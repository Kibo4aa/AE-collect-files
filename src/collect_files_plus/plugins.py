"""Mencari file plugin (.aex / .plugin) yang berisi efek yang dipakai project."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .pipl import PiPLEntry, read_plugin_pipl, scan_needles
from .i18n import N_, _

ProgressFn = Callable[[str], None]

#: Folder "struktural" (bukan milik satu plugin).
STRUCTURAL_DIRS = {
    "effects", "effect", "format", "formats", "keyframe", "extensions", "aegp",
    "standard", "plug-ins", "plugins", "plugin", "mediacore", "common",
}
#: Ekstensi file plugin: tidak pernah ikut sebagai "file pendukung".
PLUGIN_BIN_EXT = {".aex", ".plugin", ".prm", ".8bf", ".8bi", ".8li", ".aip", ".bundle"}
#: Cara ketemu yang cukup pasti untuk langsung dicentang.
STRICT_HOW = {"pipl", "pipl-nama", "isi-file"}
#: Cara ketemu yang 100% pasti (laporan menandai [OK]).
CERTAIN_HOW = {"pipl", "pipl-nama"}
HOW_LABEL = {
    "pipl": N_("data PiPL"),
    "pipl-nama": N_("data PiPL (nama efek sama dengan match name)"),
    "pipl-mirip": N_("data PiPL (nama efek mirip, bukan persis)"),
    "isi-file": N_("isi file (data PiPL tidak terbaca, plugin mungkin dikompres)"),
    "isi-file-lemah": N_("teks di isi file (cocok lemah)"),
    "nama-file": N_("nama file sama dengan nama efek"),
    "nama-file-mirip": N_("nama file mirip nama efek"),
}
FALLBACK_BUDGET = 2 * 1024 * 1024 * 1024
MAX_DEPTH = 10
_GENERIC_TOKENS = {"adbe", "effect", "effects", "plugin", "plugins", "the", "and", "pseudo"}



def how_label(how: str) -> str:
    """Keterangan cara plugin ditemukan, dalam bahasa tampilan."""
    return _(HOW_LABEL.get(how, how))

@dataclass
class PluginRoot:
    folder: Path
    label: str
    priority: int
    is_app: bool = False


@dataclass
class PluginFile:
    target: Path
    is_bundle: bool
    root: PluginRoot
    parts: Tuple[str, ...]
    rsrc: List[Path] = field(default_factory=list)
    bins: List[Path] = field(default_factory=list)
    size: int = 0
    score: int = 0
    entries: Optional[List[PiPLEntry]] = None

    @property
    def label(self) -> str:
        return self.root.label + "/" + "/".join(self.parts)

    def read_entries(self) -> List[PiPLEntry]:
        if self.entries is None:
            key = _entry_key(self)
            cached = _ENTRY_CACHE.get(key) if key is not None else None
            if cached is not None:
                self.entries = cached
            else:
                self.entries = read_plugin_pipl(self.target, self.rsrc)
                if key is not None:
                    _ENTRY_CACHE[key] = self.entries
        return self.entries


# Isi PiPL per file plugin (path + ukuran + waktu ubah). Analisa berikutnya
# (batch banyak project, atau analisa ulang di GUI) tidak membaca file yang sama lagi.
_ENTRY_CACHE: Dict[tuple, List[PiPLEntry]] = {}


def _entry_key(pf: "PluginFile") -> Optional[tuple]:
    try:
        files = pf.rsrc if pf.rsrc else [pf.target]
        return tuple((os.path.normcase(str(f)), st.st_size, st.st_mtime_ns)
                     for f in files for st in (f.stat(),))
    except OSError:
        return None


@dataclass
class Match:
    plugin: PluginFile
    how: str
    effect_name: str = ""
    category: str = ""

    @property
    def strict(self) -> bool:
        return self.how in STRICT_HOW


def norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def is_structural(name: str) -> bool:
    return (name or "").lower() in STRUCTURAL_DIRS


# --------------------------------------------------------------- lokasi

def _win_registry_paths() -> List[Tuple[str, str]]:
    """(nilai, versi) dari HKLM\\SOFTWARE\\Adobe\\After Effects\\<versi>."""
    out: List[Tuple[str, str]] = []
    if sys.platform != "win32":
        return out
    try:
        import winreg  # type: ignore
    except ImportError:
        return out
    try:
        base = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Adobe\After Effects")
    except OSError:
        return out
    i = 0
    while True:
        try:
            ver = winreg.EnumKey(base, i)
        except OSError:
            break
        i += 1
        try:
            key = winreg.OpenKey(base, ver)
        except OSError:
            continue
        for name in ("CommonPluginInstallPath", "PluginInstallPath", "InstallPath"):
            try:
                val, _kind = winreg.QueryValueEx(key, name)
                if val:
                    out.append((name + "|" + str(val), ver))
            except OSError:
                pass
    return out


def _version_key(text: str) -> Tuple[int, ...]:
    nums = re.findall(r"\d+", text)
    return tuple(int(n) for n in nums) if nums else (0,)


def find_ae_installs() -> List[Path]:
    """Folder aplikasi After Effects yang terinstall, terbaru dulu.

    Windows: folder `Support Files`. macOS: folder `Adobe After Effects <versi>`.
    """
    found: Dict[str, Path] = {}
    if sys.platform == "win32":
        for raw, _ver in _win_registry_paths():
            name, val = raw.split("|", 1)
            if name == "InstallPath":
                p = Path(val)
                if p.is_dir():
                    found[str(p).lower()] = p
        for env in ("ProgramW6432", "ProgramFiles"):
            pf = os.environ.get(env)
            if not pf:
                continue
            for p in Path(pf, "Adobe").glob("Adobe After Effects*/Support Files"):
                if p.is_dir():
                    found[str(p).lower()] = p
    elif sys.platform == "darwin":
        for p in Path("/Applications").glob("Adobe After Effects*"):
            if p.is_dir() and not p.name.endswith(".app"):
                found[str(p)] = p
    return sorted(found.values(), key=lambda p: _version_key(str(p)), reverse=True)


def default_roots(ae_installs: Optional[Sequence[Path]] = None) -> List[PluginRoot]:
    roots: List[PluginRoot] = []
    seen = set()

    def add(folder: Path, label: str, priority: int, is_app: bool = False) -> None:
        try:
            key = str(folder.resolve()).lower() if sys.platform == "win32" else str(folder.resolve())
        except OSError:
            return
        if key in seen or not folder.is_dir():
            return
        seen.add(key)
        roots.append(PluginRoot(folder, label, priority, is_app))

    if sys.platform == "win32":
        for raw, _ver in _win_registry_paths():
            name, val = raw.split("|", 1)
            if name == "CommonPluginInstallPath":
                add(Path(val), "MediaCore", 1)
        for env in ("ProgramW6432", "ProgramFiles"):
            pf = os.environ.get(env)
            if pf:
                add(Path(pf, "Adobe", "Common", "Plug-ins", "7.0", "MediaCore"), "MediaCore", 1)
    elif sys.platform == "darwin":
        add(Path("/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore"), "MediaCore", 1)
        add(Path.home() / "Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore",
            "MediaCore (user)", 1)

    installs = list(ae_installs) if ae_installs is not None else find_ae_installs()
    for i, inst in enumerate(installs):
        # Windows: ...\Adobe After Effects 2025\Support Files  -> nama versi di parent
        version_name = inst.parent.name if inst.name.lower() == "support files" else inst.name
        label = "AE Plug-ins" if i == 0 else "AE Plug-ins (" + version_name + ")"
        add(inst / "Plug-ins", label, 2, True)
    return roots


def plugin_log_files() -> List[Path]:
    """Semua "Plugin Loading.log" milik After Effects, terbaru dulu."""
    bases: List[Path] = []
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            bases.append(Path(appdata, "Adobe", "After Effects"))
    elif sys.platform == "darwin":
        bases.append(Path.home() / "Library/Preferences/Adobe/After Effects")
        bases.append(Path.home() / "Library/Application Support/Adobe/After Effects")
    logs: List[Path] = []
    for base in bases:
        if not base.is_dir():
            continue
        for ver in base.iterdir():
            for cand in (ver / "logs" / "Plugin Loading.log", ver / "Plugin Loading.log"):
                if cand.is_file():
                    logs.append(cand)
    logs.sort(key=lambda p: _version_key(p.parent.name if p.parent.name != "logs" else p.parent.parent.name),
              reverse=True)
    return logs


_LOG_ROOT = re.compile(r"Loading from root path:\s*\"?(.+?)\"?\s*$", re.I)
_LOG_FILE = re.compile(r"Loading\s+\"?(.+?\.(?:aex|plugin))(?=[\"\s/\\]|$)", re.I)


def parse_plugin_logs(files: Iterable[Path]) -> Tuple[List[str], List[str]]:
    roots: List[str] = []
    plugin_files: List[str] = []
    seen = set()
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            m = _LOG_ROOT.search(line)
            if m:
                if ("r", m.group(1)) not in seen:
                    seen.add(("r", m.group(1)))
                    roots.append(m.group(1))
                continue
            m = _LOG_FILE.search(line)
            if m and ("f", m.group(1)) not in seen:
                seen.add(("f", m.group(1)))
                plugin_files.append(m.group(1))
    return roots, plugin_files


# --------------------------------------------------------- daftar plugin

def _rel_parts(target: Path, root: Path) -> Tuple[str, ...]:
    try:
        return tuple(target.relative_to(root).parts)
    except ValueError:
        return (target.name,)


def make_plugin(target: Path, root: PluginRoot) -> PluginFile:
    is_bundle = target.suffix.lower() == ".plugin" and target.is_dir()
    pf = PluginFile(target=target, is_bundle=is_bundle, root=root, parts=_rel_parts(target, root.folder))
    if is_bundle:
        res = target / "Contents" / "Resources"
        if res.is_dir():
            pf.rsrc = sorted(p for p in res.glob("*.rsrc") if p.is_file())
        mac = target / "Contents" / "MacOS"
        if mac.is_dir():
            pf.bins = sorted(p for p in mac.iterdir() if p.is_file())
        pf.size = sum(_safe_size(p) for p in pf.rsrc + pf.bins)
    else:
        pf.size = _safe_size(target)
    return pf


def _safe_size(p: Path) -> int:
    try:
        return p.stat().st_size
    except OSError:
        return 0


def _walk_plugins(folder: Path, root: PluginRoot, out: List[PluginFile], seen: set,
                  seen_dirs: set, depth: int) -> None:
    if depth > MAX_DEPTH:
        return
    try:
        real = str(folder.resolve())
    except OSError:
        return
    if real in seen_dirs:
        return
    seen_dirs.add(real)
    try:
        entries = sorted(folder.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return
    for en in entries:
        name = en.name
        ext = en.suffix.lower()
        try:
            is_dir = en.is_dir()
        except OSError:
            continue
        if is_dir:
            if name.startswith("(") and name.endswith(")"):
                continue  # After Effects tidak memuat folder (dalam kurung)
            if ext == ".plugin":
                _add(out, seen, en, root)
            elif ext not in (".app", ".bundle", ".framework"):
                _walk_plugins(en, root, out, seen, seen_dirs, depth + 1)
        elif ext == ".aex":
            _add(out, seen, en, root)


def _add(out: List[PluginFile], seen: set, target: Path, root: PluginRoot) -> None:
    key = os.path.normcase(str(target))
    if key in seen:
        return
    seen.add(key)
    out.append(make_plugin(target, root))


def list_plugins(roots: Sequence[PluginRoot], extra_files: Sequence[str] = (),
                 progress: Optional[ProgressFn] = None) -> List[PluginFile]:
    out: List[PluginFile] = []
    seen: set = set()
    seen_dirs: set = set()
    for root in roots:
        if progress:
            progress(_("Mendata plugin di %s") % root.folder)
        _walk_plugins(root.folder, root, out, seen, seen_dirs, 0)
    for raw in extra_files:
        p = Path(raw)
        if not p.exists():
            continue
        root = PluginRoot(p.parent, _("Lainnya") + "/" + p.parent.name, 4)
        _add(out, seen, p, root)
    return out


def build_plugin_list(effect_hints: Sequence[Tuple[str, str, Sequence[str]]],
                      roots: Optional[Sequence[PluginRoot]] = None,
                      log_files: Optional[Sequence[Path]] = None,
                      ae_installs: Optional[Sequence[Path]] = None,
                      progress: Optional[ProgressFn] = None) -> List[PluginFile]:
    """Semua file plugin di folder yang dimuat AE (+ Plugin Loading.log).

    effect_hints: (match name, nama efek, nama-nama di layer) untuk mengurutkan
    file yang namanya mirip efek supaya dicek lebih dulu.
    """
    if roots is None:
        roots = default_roots(ae_installs)
    roots = list(roots)
    if log_files is None:
        log_files = plugin_log_files()
    log_roots, log_plugins = parse_plugin_logs(log_files)
    known = {os.path.normcase(str(r.folder)) for r in roots}
    for raw in log_roots:
        p = Path(raw)
        if p.is_dir() and os.path.normcase(str(p)) not in known:
            known.add(os.path.normcase(str(p)))
            roots.append(PluginRoot(p, _("Lainnya") + "/" + p.name, 3))
    plugins = list_plugins(roots, log_plugins, progress)

    tokens = set()
    for mn, disp, names in effect_hints:
        for s in [mn, disp, *names]:
            for t in re.split(r"[^a-z0-9]+", (s or "").lower()):
                if len(t) >= 3 and t not in _GENERIC_TOKENS:
                    tokens.add(t)
    for pf in plugins:
        hay = " ".join(pf.parts).lower()
        pf.score = sum(1 for t in tokens if t in hay)
    plugins.sort(key=lambda p: (-p.score, p.root.priority, p.size))
    return plugins


# ------------------------------------------------------------ pencocokan

def match_effects(plugins: Sequence[PluginFile], needed: Sequence[str],
                  progress: Optional[ProgressFn] = None,
                  budget: int = FALLBACK_BUDGET) -> Dict[str, Match]:
    """Cari file plugin untuk setiap match name di `needed`."""
    need = set(needed)
    loose_need = {norm_key(n): n for n in needed if norm_key(n)}
    found: Dict[str, Match] = {}
    name_idx: Dict[str, Tuple[PluginFile, PiPLEntry]] = {}
    loose_idx: Dict[str, Tuple[PluginFile, PiPLEntry]] = {}

    for i, pf in enumerate(plugins):
        if len(found) >= len(need):
            break
        if progress:
            progress(_("Membaca plugin %d/%d: %s") % (i + 1, len(plugins), pf.label))
        for en in pf.read_entries():
            if en.match_name in need and en.match_name not in found:
                found[en.match_name] = Match(pf, "pipl", en.name, en.category)
                continue
            lk = norm_key(en.match_name)
            if lk and lk in loose_need and lk not in loose_idx:
                loose_idx[lk] = (pf, en)
            if en.name and en.name not in name_idx:
                name_idx[en.name] = (pf, en)

    for mn in needed:
        if mn in found:
            continue
        if mn in name_idx:
            pf, en = name_idx[mn]
            found[mn] = Match(pf, "pipl-nama", en.name, en.category)
            continue
        hit = loose_idx.get(norm_key(mn))
        if hit:
            found[mn] = Match(hit[0], "pipl-mirip", hit[1].name, hit[1].category)

    # Cadangan: baca isi penuh file yang PiPL-nya tidak terbaca (mis. dikompres).
    missing = [mn for mn in needed if mn not in found]
    if missing:
        weak: Dict[str, PluginFile] = {}
        no_pipl = [p for p in plugins if p.entries is not None and not p.entries]
        no_pipl.sort(key=lambda p: (-p.score, p.size))
        for pf in no_pipl:
            pending = [mn for mn in missing if mn not in found]
            if not pending or budget <= 0:
                break
            files = pf.rsrc + pf.bins if pf.is_bundle else [pf.target]
            for f in files:
                budget -= _safe_size(f)
                if progress:
                    progress(_("Pencarian cadangan: %s") % pf.label)
                hits = scan_needles(f, pending)
                for mn, strength in hits.items():
                    if strength == 2 and mn not in found:
                        found[mn] = Match(pf, "isi-file")
                    elif strength == 1 and mn not in weak:
                        weak[mn] = pf
        for mn, pf in weak.items():
            if mn not in found:
                found[mn] = Match(pf, "isi-file-lemah")
    return found


def guess_by_file_name(plugins: Sequence[PluginFile], keys_src: Sequence[str]) -> Optional[Match]:
    """Tebakan terakhir dari nama file (tidak dicentang otomatis)."""
    keys = []
    for s in keys_src:
        k = norm_key(re.sub(r"\s+\d+$", "", s or ""))
        if len(k) >= 4:
            keys.append(k)
    best: Optional[PluginFile] = None
    best_score = 0
    for pf in plugins:
        b = norm_key(Path(pf.parts[-1]).stem)
        if len(b) < 4:
            continue
        for k in keys:
            shorter, longer = min(len(b), len(k)), max(len(b), len(k))
            sc = 0
            if b == k:
                sc = 3
            elif shorter >= 5 and shorter / longer >= 0.5 and (k in b or b in k):
                sc = 1
            if sc > best_score:
                best, best_score = pf, sc
    if not best:
        return None
    return Match(best, "nama-file" if best_score == 3 else "nama-file-mirip")


# ------------------------------------------------------- file pendukung

def _has_plugin_binary(folder: Path, depth: int = 0) -> bool:
    if depth > 6:
        return True
    try:
        for en in folder.iterdir():
            if en.suffix.lower() in PLUGIN_BIN_EXT:
                return True
            if en.is_dir() and _has_plugin_binary(en, depth + 1):
                return True
    except OSError:
        return False
    return False


def support_items(pf: PluginFile) -> List[Path]:
    """File non-plugin di folder yang sama (DLL/data) + folder bernama sama.

    File plugin lain tidak pernah ikut, jadi efek yang tidak dipakai tidak
    ikut tercopy.
    """
    out: List[Path] = []
    parent = pf.target.parent
    dirs = pf.parts[:-1]
    vendor_dir = len(dirs) >= 1 and not is_structural(dirs[-1])
    base = pf.target.stem.lower()
    try:
        entries = sorted(parent.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return out
    for en in entries:
        if en == pf.target or en.suffix.lower() in PLUGIN_BIN_EXT:
            continue
        same_base = en.stem.lower() == base
        if en.is_file():
            if vendor_dir or same_base:
                out.append(en)
        elif en.is_dir() and same_base and not _has_plugin_binary(en):
            out.append(en)
    return out


def path_size(p: Path) -> int:
    if p.is_file():
        return _safe_size(p)
    total = 0
    for dirpath, _dirs, files in os.walk(p):
        for name in files:
            total += _safe_size(Path(dirpath, name))
    return total
