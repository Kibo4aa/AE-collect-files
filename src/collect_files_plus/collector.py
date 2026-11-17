"""Analisa project lalu collect: copy footage/font/plugin, relink, simpan .aep baru."""

from __future__ import annotations

import os
import re
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from py_aep.models.items.composition import CompItem

from .firstparty import BUILTIN_EFFECTS
from .fonts import FontFace, FontIndex, adobe_fonts_dirs
from .i18n import N_, _
from .plugins import (
    Match,
    PluginFile,
    PluginRoot,
    build_plugin_list,
    find_ae_installs,
    guess_by_file_name,
    match_effects,
    norm_key,
    path_size,
    support_items,
)
from .project import AepProject, EffectGroup, FootageRef, sequence_frames

ProgressFn = Callable[[str], None]

MODEL_EXT = {".gltf", ".obj"}
MODEL_SIDE_EXT = {".bin", ".mtl", ".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff", ".bmp",
                  ".webp", ".ktx2", ".exr", ".hdr"}
MODEL_TEX_DIR = re.compile(r"^(tex|texture|textures|map|maps|image|images|material|materials)$", re.I)


class Cancelled(Exception):
    """Dihentikan oleh pengguna."""


@dataclass
class Options:
    dest_dir: Path
    comp_ids: Optional[List[int]] = None   # None = semua comp di project
    scope_label: str = ""
    collect_footage: bool = True
    reduce_project: bool = False
    collect_fonts: bool = True
    collect_plugins: bool = True
    skip_disabled: bool = True
    support_files: bool = False
    presets: bool = False


@dataclass
class Environment:
    """Lokasi di komputer ini. None = dicari otomatis (bisa diganti untuk test)."""

    plugin_roots: Optional[List[PluginRoot]] = None
    plugin_logs: Optional[List[Path]] = None
    ae_installs: Optional[List[Path]] = None
    font_dirs: Optional[List[Path]] = None
    font_cache: Optional[Path] = None
    adobe_font_dirs: Optional[List[Path]] = None
    preset_dirs: Optional[List[Path]] = None
    preset_effects_xml: Optional[List[Path]] = None
    # hasil yang mahal (indeks font) disimpan di sini supaya batch tidak mengulang
    cache: Dict[str, object] = field(default_factory=dict, repr=False, compare=False)

    def installs(self) -> List[Path]:
        if self.ae_installs is None:
            self.ae_installs = find_ae_installs()
        return self.ae_installs


@dataclass
class EffectInfo:
    group: EffectGroup
    kind: str                      # plugin / builtin / pseudo / presetxml
    display: str = ""
    category: str = ""
    match: Optional[Match] = None
    candidate: Optional["PluginCandidate"] = None
    xml_block: Optional[str] = None

    @property
    def match_name(self) -> str:
        return self.group.match_name

    @property
    def names(self) -> List[str]:
        return self.group.names

    @property
    def count(self) -> int:
        return self.group.count

    @property
    def title(self) -> str:
        return self.display or (self.names[0] if self.names else "") or self.match_name


@dataclass
class PluginCandidate:
    plugin: PluginFile
    effects: List[EffectInfo] = field(default_factory=list)
    strict: bool = False
    support: List[Path] = field(default_factory=list)
    size: int = 0
    others: int = 0
    selected: bool = False
    ok: Optional[bool] = None
    dest_rel: str = ""

    @property
    def label(self) -> str:
        return self.plugin.label


@dataclass
class FontEntry:
    post_script_name: str
    face: Optional[FontFace]
    status: str                    # "ada" / "adobe" / "tidak-ketemu"
    copied: Optional[bool] = None


@dataclass
class FootageEntry:
    src: Path                      # file, atau frame pertama image sequence
    is_sequence: bool
    files: List[Path]
    refs: List[FootageRef]
    exists: bool
    size: int
    extras: List[Path] = field(default_factory=list)
    dest: Optional[Path] = None
    copied: Optional[bool] = None
    error: str = ""

    @property
    def names(self) -> List[str]:
        out: List[str] = []
        for r in self.refs:
            n = r.item.name + (" (proxy)" if r.role == "proxy" else "")
            if n not in out:
                out.append(n)
        return out


@dataclass
class Analysis:
    aep: AepProject
    options: Options
    env: Environment
    roots: List[CompItem]
    comps: List[CompItem]
    effects: List[EffectInfo] = field(default_factory=list)
    disabled_only: List[EffectInfo] = field(default_factory=list)
    disabled_all: List[EffectInfo] = field(default_factory=list)
    disabled_uses: int = 0
    candidates: List[PluginCandidate] = field(default_factory=list)
    fonts: List[FontEntry] = field(default_factory=list)
    footage: List[FootageEntry] = field(default_factory=list)
    presets: List[Tuple[Path, str]] = field(default_factory=list)
    xml_source: Optional[Path] = None
    notes: List[str] = field(default_factory=list)

    @property
    def plugin_effects(self) -> List[EffectInfo]:
        return [e for e in self.effects if e.kind == "plugin"]


@dataclass
class Result:
    dest_root: Path
    project_out: Optional[Path] = None
    backup: Optional[Path] = None
    report: Optional[Path] = None
    csv: Optional[Path] = None
    reduced: int = -1
    saved_ok: bool = True
    validation_error: str = ""
    errors: List[str] = field(default_factory=list)


# ------------------------------------------------------------- helper

def _tick(progress: Optional[ProgressFn], msg: str, cancel: Optional[threading.Event] = None) -> None:
    if cancel is not None and cancel.is_set():
        raise Cancelled()
    if progress:
        progress(msg)


def copy_file(src: Path, dest_dir: Path, rename_if_different: bool = False) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / src.name
    size = src.stat().st_size
    if target.exists() and target.stat().st_size == size:
        return target
    if target.exists() and rename_if_different:
        n = 2
        while True:
            cand = dest_dir / (src.stem + " (%d)" % n + src.suffix)
            if not cand.exists() or cand.stat().st_size == size:
                target = cand
                break
            n += 1
        if target.exists():
            return target
    shutil.copy2(src, target)
    return target


def copy_tree(src: Path, dest_parent: Path) -> Path:
    target = dest_parent / src.name
    shutil.copytree(src, target, symlinks=True, dirs_exist_ok=True)
    return target


def unique_dir(base: Path) -> Path:
    if not base.exists() or not any(base.iterdir()):
        return base
    n = 2
    while True:
        cand = base.with_name(base.name + " (%d)" % n)
        if not cand.exists() or not any(cand.iterdir()):
            return cand
        n += 1


def _preset_effects_candidates(env: Environment) -> List[Path]:
    if env.preset_effects_xml is not None:
        return env.preset_effects_xml
    out = []
    for inst in env.installs():
        out.append(inst / "PresetEffects.xml")
        out.extend(inst.glob("*.app/Contents/Resources/PresetEffects.xml"))
    return out


def find_preset_effect_block(xml_text: str, match_name: str) -> Optional[str]:
    escaped = (match_name.replace("&", "&amp;").replace("<", "&lt;")
               .replace(">", "&gt;").replace('"', "&quot;"))
    for v in (match_name, escaped):
        for q in ('"', "'"):
            idx = xml_text.find("matchname=" + q + v + q)
            if idx == -1:
                continue
            s = xml_text.rfind("<Effect", 0, idx)
            e = xml_text.find("</Effect>", idx)
            if s != -1 and e != -1:
                return xml_text[s:e + 9]
    return None


def _documents_dirs() -> List[Path]:
    home = Path.home()
    return [d for d in (home / "Documents", home / "OneDrive" / "Documents") if d.is_dir()]


def _preset_dirs(env: Environment) -> List[Path]:
    if env.preset_dirs is not None:
        return env.preset_dirs
    dirs = [inst / "Presets" for inst in env.installs()[:1]]
    for docs in _documents_dirs():
        adobe = docs / "Adobe"
        if adobe.is_dir():
            dirs += [d for d in adobe.iterdir() if d.is_dir() and d.name.lower().startswith("after effects")]
    return [d for d in dirs if d.is_dir()]


def _is_renamed(instance: str, original: str) -> bool:
    if not instance or not original:
        return False
    return norm_key(re.sub(r"\s+\d+$", "", instance)) != norm_key(original)


# ------------------------------------------------------------- analisa

def analyze(aep: AepProject, options: Options, env: Optional[Environment] = None,
            progress: Optional[ProgressFn] = None,
            cancel: Optional[threading.Event] = None) -> Analysis:
    env = env or Environment()
    if options.comp_ids is None:
        roots = aep.comps
        comps = roots
    else:
        by_id = {c.id: c for c in aep.comps}
        roots = [by_id[i] for i in options.comp_ids if i in by_id]
        comps = aep.expand(roots)
    an = Analysis(aep, options, env, roots, comps)

    # --- efek
    _tick(progress, _("Membaca efek..."), cancel)
    used, off = aep.effects(comps, options.skip_disabled)
    xml_text = ""
    for cand in _preset_effects_candidates(env):
        if cand.is_file():
            try:
                xml_text = cand.read_text(encoding="utf-8", errors="replace")
                an.xml_source = cand
                break
            except OSError:
                pass

    def classify(g: EffectGroup) -> EffectInfo:
        mn = g.match_name
        if mn.startswith("Pseudo/"):
            info = EffectInfo(g, "pseudo")
        elif mn in BUILTIN_EFFECTS:
            info = EffectInfo(g, "builtin", display=BUILTIN_EFFECTS[mn])
        else:
            info = EffectInfo(g, "plugin")
        if info.kind != "builtin" and xml_text:
            info.xml_block = find_preset_effect_block(xml_text, mn)
            if info.xml_block and info.kind == "plugin":
                info.kind = "presetxml"
        return info

    an.effects = [classify(g) for g in used]
    used_set = {e.match_name for e in an.effects}
    for g in off:
        an.disabled_uses += g.count
        info = classify(g)
        an.disabled_all.append(info)
        if g.match_name not in used_set:
            an.disabled_only.append(info)

    # --- plugin
    wanted = an.plugin_effects
    if options.collect_plugins and wanted:
        hints = [(e.match_name, e.display, e.names) for e in wanted]
        plugins = build_plugin_list(hints, roots=env.plugin_roots, log_files=env.plugin_logs,
                                    ae_installs=env.ae_installs,
                                    progress=lambda m: _tick(progress, m, cancel))
        found = match_effects(plugins, [e.match_name for e in wanted],
                              progress=lambda m: _tick(progress, m, cancel))
        cand_map: Dict[str, PluginCandidate] = {}
        for e in wanted:
            m = found.get(e.match_name)
            if m is None:
                m = guess_by_file_name(plugins, [e.display, e.match_name] + e.names)
            e.match = m
            if m is None:
                continue
            if m.effect_name and not e.display:
                e.display = m.effect_name
            if m.category:
                e.category = m.category
            key = os.path.normcase(str(m.plugin.target))
            cd = cand_map.get(key)
            if cd is None:
                cd = PluginCandidate(m.plugin)
                cand_map[key] = cd
                an.candidates.append(cd)
            cd.effects.append(e)
            e.candidate = cd
            if m.strict:
                cd.strict = True
        for cd in an.candidates:
            cd.support = support_items(cd.plugin) if options.support_files else []
            cd.size = path_size(cd.plugin.target) + sum(path_size(p) for p in cd.support)
            others = {en.match_name for en in (cd.plugin.entries or [])} - used_set
            cd.others = len(others)
            cd.selected = cd.strict  # perkiraan tidak dicentang otomatis
    elif wanted:
        an.notes.append(N_("Pencarian plugin dimatikan."))

    # --- font
    if options.collect_fonts:
        _tick(progress, _("Membaca daftar font..."), cancel)
        names = aep.fonts(comps if options.comp_ids is not None else None)
        if names:
            index = env.cache.get("font_index")
            if index is None:
                index = FontIndex(env.font_dirs, env.font_cache).build(lambda m: _tick(progress, m, cancel))
                env.cache["font_index"] = index
            adobe_index = env.cache.get("adobe_index")
            for ps in names:
                face = index.lookup(ps)
                status = "ada" if face else "tidak-ketemu"
                if face is None:
                    if adobe_index is None:
                        dirs = env.adobe_font_dirs if env.adobe_font_dirs is not None else adobe_fonts_dirs()
                        dirs = [d for d in dirs if d.is_dir()]
                        adobe_index = FontIndex(dirs, use_cache=False).build() if dirs else FontIndex([], use_cache=False)
                        env.cache["adobe_index"] = adobe_index
                    if adobe_index.lookup(ps):
                        status = "adobe"
                an.fonts.append(FontEntry(ps, face, status))

    # --- footage
    if options.collect_footage:
        _tick(progress, _("Membaca footage..."), cancel)
        only = comps if (options.reduce_project and options.comp_ids is not None) else None
        groups: Dict[str, FootageEntry] = {}
        for ref in aep.footage(only_used_by=only):
            src = Path(ref.path)
            key = os.path.normcase(str(src.parent if ref.is_sequence else src))
            fe = groups.get(key)
            if fe is None:
                if ref.is_sequence:
                    if ref.frames:
                        files = [src.parent / n for n in ref.frames]
                    else:
                        files = sequence_frames(src)
                else:
                    files = [src]
                exists = src.exists()
                files = [f for f in files if f.exists()] if exists else files
                fe = FootageEntry(src, ref.is_sequence, files, [], exists,
                                  sum(f.stat().st_size for f in files) if exists else 0)
                if exists and src.suffix.lower() in MODEL_EXT:
                    fe.extras = _model_extras(src)
                    fe.size += sum(path_size(p) for p in fe.extras)
                groups[key] = fe
            fe.refs.append(ref)
        an.footage = list(groups.values())

    # --- animation preset (.ffx) yang namanya sama dengan efek yang di-rename
    if options.presets:
        _tick(progress, _("Mencari animation preset (.ffx)..."), cancel)
        keys: Dict[str, str] = {}
        for e in an.effects:
            for inst in e.names:
                if e.kind == "pseudo" or not e.display or _is_renamed(inst, e.display):
                    k = norm_key(inst)
                    if len(k) >= 3:
                        keys[k] = inst
        if keys:
            seen = set()
            for d in _preset_dirs(env):
                for f in d.rglob("*.ffx"):
                    k = norm_key(f.stem)
                    if k in keys and os.path.normcase(str(f)) not in seen:
                        seen.add(os.path.normcase(str(f)))
                        an.presets.append((f, keys[k]))
    return an


def _model_extras(src: Path) -> List[Path]:
    out = []
    for en in src.parent.iterdir():
        if en == src:
            continue
        if en.is_file() and en.suffix.lower() in MODEL_SIDE_EXT:
            out.append(en)
        elif en.is_dir() and MODEL_TEX_DIR.match(en.name):
            out.append(en)
    return out


# ------------------------------------------------------------- collect

def collect(an: Analysis, progress: Optional[ProgressFn] = None,
            cancel: Optional[threading.Event] = None) -> Result:
    from .report import build_report, effect_rows, write_csv

    opt = an.options
    aep = an.aep
    stem = aep.path.stem
    dest_root = unique_dir(Path(opt.dest_dir) / (stem + "_Collected"))
    dest_root.mkdir(parents=True, exist_ok=True)
    res = Result(dest_root)

    # 1. reduce project (di memori; file asli tidak berubah)
    if opt.reduce_project and opt.comp_ids is not None and an.roots:
        _tick(progress, "Reduce Project...", cancel)
        try:
            res.reduced = aep.reduce(an.roots)
        except Exception as exc:  # noqa: BLE001
            res.errors.append(_("Reduce Project gagal: %s") % exc)

    # 2. footage + relink
    expected: Dict[Tuple[int, str], str] = {}
    if opt.collect_footage and an.footage:
        foot_root = dest_root / "(Footage)"
        folder_map: Dict[str, Path] = {}
        used_names: set = set()

        def dest_for(folder: Path) -> Path:
            key = os.path.normcase(str(folder))
            if key in folder_map:
                return folder_map[key]
            base = re.sub(r'[<>:"/\\|?*]', "", folder.name) or "root"
            name, n = base, 2
            while name.lower() in used_names:
                name = "%s_%d" % (base, n)
                n += 1
            used_names.add(name.lower())
            folder_map[key] = foot_root / name
            return folder_map[key]

        for i, fe in enumerate(an.footage):
            _tick(progress, "Footage %d/%d: %s" % (i + 1, len(an.footage), fe.src.name), cancel)
            if not fe.exists:
                fe.copied = False
                fe.error = _("file tidak ada")
                continue
            try:
                dest = dest_for(fe.src.parent)
                for j, f in enumerate(fe.files):
                    if fe.is_sequence and j % 50 == 0:
                        _tick(progress, "Footage %d/%d: %s (frame %d/%d)" % (
                            i + 1, len(an.footage), fe.src.name, j + 1, len(fe.files)), cancel)
                    copy_file(f, dest)
                for ex in fe.extras:
                    if ex.is_dir():
                        copy_tree(ex, dest)
                    else:
                        copy_file(ex, dest)
                fe.dest = dest / fe.src.name
                for ref in fe.refs:
                    aep.relink(ref, str(fe.dest))
                    expected[(ref.item.id, ref.role)] = str(fe.dest)
                fe.copied = True
            except Cancelled:
                raise
            except Exception as exc:  # noqa: BLE001
                fe.copied = False
                fe.error = str(exc)

    # 3. font
    if opt.collect_fonts:
        for fe in an.fonts:
            if fe.face is None:
                continue
            _tick(progress, "Font: " + fe.post_script_name, cancel)
            try:
                copy_file(fe.face.path, dest_root / "(Fonts)", rename_if_different=True)
                fe.copied = True
            except Exception as exc:  # noqa: BLE001
                fe.copied = False
                res.errors.append("Font %s: %s" % (fe.post_script_name, exc))

    # 4. plugin (hanya file plugin yang dicentang)
    if opt.collect_plugins:
        copied_keys: set = set()
        for cd in an.candidates:
            if not cd.selected:
                continue
            _tick(progress, "Plugin: " + cd.label, cancel)
            dirs = cd.plugin.parts[:-1]
            cd.dest_rel = "/".join((cd.plugin.root.label,) + tuple(dirs))
            dest = dest_root / "(Plugins)"
            for part in cd.dest_rel.split("/"):
                dest = dest / part
            try:
                key = os.path.normcase(str(cd.plugin.target))
                if key not in copied_keys:
                    copied_keys.add(key)
                    if cd.plugin.target.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                        copy_tree(cd.plugin.target, dest)
                    else:
                        copy_file(cd.plugin.target, dest)
                for s in cd.support:
                    sk = os.path.normcase(str(s))
                    if sk in copied_keys:
                        continue
                    copied_keys.add(sk)
                    if s.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                        copy_tree(s, dest)
                    else:
                        copy_file(s, dest)
                cd.ok = True
            except Exception as exc:  # noqa: BLE001
                cd.ok = False
                res.errors.append("Plugin %s: %s" % (cd.label, exc))

    # 5. PresetEffects.xml & animation preset
    blocks = [e.xml_block for e in an.effects if e.xml_block]
    if blocks:
        xdir = dest_root / "(PresetEffects)"
        xdir.mkdir(parents=True, exist_ok=True)
        (xdir / _("PresetEffects_dari_project.xml")).write_text("\n".join([
            '<?xml version="1.0" encoding="UTF-8"?>',
            _("<!-- Collect Files Plus: definisi efek dari PresetEffects.xml yang dipakai project ini."),
            _("     Asal: %s") % an.xml_source,
            _('     Efek dengan match name berawalan "Pseudo/" sudah tersimpan di dalam project,'),
            _("     jadi biasanya tidak perlu dipasang. Efek lainnya: salin blok <Effect> di bawah"),
            _("     ke PresetEffects.xml di komputer tujuan (sebelum tag </Effects> terakhir),"),
            _("     lalu restart After Effects. -->"),
            "<Effects>",
            "\n\n".join(blocks),
            "</Effects>",
            "",
        ]), encoding="utf-8")
    for f, _inst in an.presets:
        try:
            copy_file(f, dest_root / "(Presets)", rename_if_different=True)
        except Exception as exc:  # noqa: BLE001
            res.errors.append("Preset %s: %s" % (f.name, exc))

    # 6. simpan project hasil collect. Kalau tidak ada yang berubah, .aep asli
    #    cukup dicopy (penyimpanan py_aep masih eksperimental).
    out_path = dest_root / aep.path.name
    if expected or res.reduced > 0:
        _tick(progress, _("Menyimpan project hasil collect..."), cancel)
        res.backup = copy_file(aep.path, dest_root / "(Backup)")
        try:
            aep.save(out_path)
            res.project_out = out_path
            res.validation_error = _validate(out_path, expected)
            res.saved_ok = not res.validation_error
        except Exception as exc:  # noqa: BLE001
            res.saved_ok = False
            res.validation_error = _("Gagal menyimpan project: %s") % exc
    else:
        res.project_out = copy_file(aep.path, dest_root)

    # 7. laporan + CSV
    _tick(progress, _("Menulis laporan..."), None)
    res.report = dest_root / (stem + "_report.txt")
    res.report.write_text("\n".join(build_report(an, res)), encoding="utf-8")
    rows = effect_rows(an)
    if len(rows) > 1:
        res.csv = dest_root / (stem + "_" + _("daftar_efek") + ".csv")
        write_csv(res.csv, rows)
    return res


def _validate(saved: Path, expected: Dict[Tuple[int, str], str]) -> str:
    """Buka lagi project hasil simpan dan pastikan path footage-nya benar."""
    try:
        check = AepProject(saved)
    except Exception as exc:  # noqa: BLE001
        return _("Project hasil tidak bisa dibaca ulang: %s") % exc
    got = {(r.item.id, r.role): r.path for r in check.footage()}
    wrong = []
    for key, path in expected.items():
        if os.path.normcase(os.path.normpath(got.get(key, ""))) != os.path.normcase(os.path.normpath(path)):
            wrong.append(path)
    if wrong:
        return _("%d footage tidak menunjuk ke file hasil copy (contoh: %s)") % (len(wrong), wrong[0])
    return ""


def scope_choices(aep: AepProject) -> Tuple[str, List[CompItem]]:
    return aep.default_roots()


def comps_by_ids(aep: AepProject, ids: Sequence[int]) -> List[CompItem]:
    by_id = {c.id: c for c in aep.comps}
    return [by_id[i] for i in ids if i in by_id]
