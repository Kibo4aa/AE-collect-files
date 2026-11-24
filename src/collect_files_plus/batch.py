"""Analisa atau collect banyak project .aep sekaligus.

Collect: setiap project tetap mendapat folder hasil sendiri (``<nama>_Collected``) di
dalam folder tujuan, jadi relink footage tiap project tidak saling bentrok. Analisa:
setiap project hanya dibaca (tidak ada yang dicopy), hasilnya ringkasan per project.
Satu project yang gagal tidak menghentikan project lain.
"""

from __future__ import annotations

import dataclasses
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from . import __version__
from . import collector as _collector
from .i18n import N_, _
from .collector import Analysis, Cancelled, Environment, Options, Result, analyze, collect
from .plugins import default_roots, plugin_log_files
from .project import AepProject

ProgressFn = Callable[[str], None]

SCOPE_LABEL = {
    "auto": N_("otomatis (Render Queue, kalau kosong comp aktif, kalau tidak ada semua comp)"),
    "rq": N_("comp di Render Queue"),
    "active": N_("comp aktif saat project disimpan"),
    "all": N_("semua comp"),
    "names": N_("comp dengan nama tertentu"),
}

STATUS_LABEL = {
    "menunggu": N_("menunggu"),
    "jalan": N_("sedang diproses..."),
    "ok": "OK",
    "catatan": N_("OK, ada catatan"),
    "gagal": N_("GAGAL"),
    "dibatalkan": N_("dibatalkan"),
    "dilewati": N_("dilewati: tidak ada comp yang dicentang"),
}

# catatan per project disimpan sebagai angka, teksnya dibuat saat ditampilkan (ikut bahasa)
NOTE_TEXT = {
    "missing": N_("%d footage hilang"),
    "fonts": N_("%d font tidak ketemu"),
    "adobe": N_("%d Adobe Fonts (aktifkan di CC)"),
    "fx": N_("%d efek plugin tidak ketemu"),
    "guess": N_("%d plugin perkiraan tidak dicopy"),
    "guess_an": N_("%d plugin perkiraan perlu dicek"),
    "errors": N_("%d error saat copy"),
}

# folder yang tidak ikut discan saat menambah folder: auto-save AE dan hasil collect sebelumnya
_SKIP_DIRS = {"adobe after effects auto-save", "(backup)", "(footage)", "(fonts)", "(plugins)",
              "(presets)", "(preseteffects)"}
_COLLECTED_RE = re.compile(r"_collected( \(\d+\))?$", re.IGNORECASE)


def _skip_dir(name: str) -> bool:
    return name.lower() in _SKIP_DIRS or bool(_COLLECTED_RE.search(name))


def find_projects(paths: Iterable) -> List[Path]:
    """File .aep dari daftar file dan/atau folder (folder discan sampai ke subfolder)."""
    out: List[Path] = []
    seen = set()

    def add(p: Path) -> None:
        key = os.path.normcase(os.path.abspath(str(p)))
        if key not in seen:
            seen.add(key)
            out.append(p)

    for raw in paths:
        p = Path(raw)
        if p.is_file() and p.suffix.lower() == ".aep":
            add(p)
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = sorted((d for d in dirs if not _skip_dir(d)), key=str.lower)
                for f in sorted(files, key=str.lower):
                    if f.lower().endswith(".aep"):
                        add(Path(root) / f)
    return out


def scope_parts(aep: AepProject, mode: str = "auto",
                names: Sequence[str] = ()) -> Tuple[Optional[List[int]], str, List[str], int]:
    """(comp_ids atau None = semua, jenis: all/names/rq/active, nama comp, jumlah comp project)."""
    n = len(aep.comps)
    if mode == "all":
        return None, "all", [], n
    if mode == "names":
        wanted = list(dict.fromkeys(names))
        roots = [c for c in aep.comps if c.name in set(wanted)]
        missing = set(wanted) - {c.name for c in roots}
        if missing:
            raise ValueError(_("Comp tidak ditemukan: %s") % ", ".join(sorted(missing)))
        return [c.id for c in roots], "names", [c.name for c in roots], n
    if mode == "rq":
        roots = aep.rq_comps()
        if not roots:
            raise ValueError(_("Render Queue kosong."))
        return [c.id for c in roots], "rq", [c.name for c in roots], n
    if mode == "active":
        act = aep.active_comp()
        if act is None:
            raise ValueError(_("Tidak ada comp aktif yang tersimpan di project ini."))
        return [act.id], "active", [act.name], n
    kind, roots = aep.default_roots()
    if kind == "all":
        return None, "all", [], n
    return [c.id for c in roots], kind, [c.name for c in roots], n


def ids_parts(aep: AepProject, ids: Iterable[int]) -> Tuple[Optional[List[int]], str, List[str], int]:
    """Seperti scope_parts, untuk comp yang dicentang sendiri (id comp). Semua comp -> None."""
    wanted = set(ids)
    roots = [c for c in aep.comps if c.id in wanted]
    n = len(aep.comps)
    if not roots:
        raise ValueError(_("Comp yang dicentang tidak ada lagi di project ini."))
    if len(roots) == n:
        return None, "all", [], n
    return [c.id for c in roots], "names", [c.name for c in roots], n


def scope_label(kind: str, names: Sequence[str], n_comps: int) -> str:
    if not kind:
        return ""
    if kind == "all":
        return _("semua comp (%d)") % n_comps
    prefix = {"names": _("comp"), "rq": _("Render Queue"), "active": _("comp aktif")}[kind]
    return prefix + ": " + ", ".join(names)


def resolve_scope(aep: AepProject, mode: str = "auto",
                  names: Sequence[str] = ()) -> Tuple[Optional[List[int]], str]:
    """Comp utama yang dibaca. Mengembalikan (comp_ids atau None = semua, keterangan).

    mode: auto | rq | active | all | names. ValueError kalau comp yang diminta tidak ada.
    """
    ids, kind, roots, n = scope_parts(aep, mode, names)
    return ids, scope_label(kind, roots, n)


@dataclass
class BatchItem:
    path: Path
    status: str = "menunggu"            # menunggu / jalan / ok / catatan / gagal / dibatalkan / dilewati
    scope_kind: str = ""
    scope_names: List[str] = field(default_factory=list)
    n_comps: int = 0
    result: Optional[Result] = None
    error: str = ""
    counts: Dict[str, int] = field(default_factory=dict)
    info: Dict[str, int] = field(default_factory=dict)   # hasil analisa: jumlah footage/font/plugin + ukuran

    @property
    def scope(self) -> str:
        return scope_label(self.scope_kind, self.scope_names, self.n_comps)

    @property
    def notes(self) -> List[str]:
        return [_(NOTE_TEXT[k]) % n for k, n in self.counts.items() if n]

    @property
    def status_text(self) -> str:
        text = _(STATUS_LABEL.get(self.status, self.status))
        if self.status == "catatan" and self.notes:
            return "OK, " + "; ".join(self.notes)
        if self.status == "gagal" and self.error:
            return _("GAGAL: %s") % self.error
        return text

    @property
    def result_name(self) -> str:
        if self.result is not None:
            return self.result.dest_root.name
        if self.info:
            from .report import fmt_bytes
            return _("%d footage, %d font, %d plugin (%s)") % (
                self.info.get("footage", 0), self.info.get("fonts", 0), self.info.get("plugins", 0),
                fmt_bytes(self.info.get("bytes", 0)))
        return ""


@dataclass
class BatchRun:
    items: List[BatchItem]
    dest: Path
    scope: str
    summary: Optional[Path] = None
    kind: str = "collect"               # collect / analyze

    def count(self, *statuses: str) -> int:
        return sum(1 for it in self.items if it.status in statuses)

    @property
    def ok(self) -> bool:
        return self.count("gagal", "dibatalkan") == 0

    def headline(self) -> str:
        parts = ["%d OK" % self.count("ok")]
        if self.count("catatan"):
            parts.append(_("%d ada catatan") % self.count("catatan"))
        if self.count("gagal"):
            parts.append(_("%d gagal") % self.count("gagal"))
        if self.count("dibatalkan", "menunggu"):
            parts.append(_("%d tidak diproses") % self.count("dibatalkan", "menunggu"))
        if self.count("dilewati"):
            parts.append(_("%d dilewati") % self.count("dilewati"))
        return _("%s (dari %d project)") % (", ".join(parts), len(self.items))


def note_counts(an: Analysis, res: Optional[Result] = None) -> Dict[str, int]:
    """Hal yang perlu dicek. Tanpa `res` (hanya analisa): plugin perkiraan = perlu dicek."""
    counts = {
        "missing": sum(1 for fe in an.footage if not fe.exists),
        "fonts": sum(1 for f in an.fonts if f.status == "tidak-ketemu"),
        "adobe": sum(1 for f in an.fonts if f.status == "adobe"),
    }
    if an.options.collect_plugins:
        counts["fx"] = sum(1 for e in an.plugin_effects if e.candidate is None)
        counts["guess" if res is not None else "guess_an"] = sum(1 for cd in an.candidates if not cd.selected)
    if res is not None:
        counts["errors"] = len(res.errors)
    return {k: n for k, n in counts.items() if n}


def analysis_info(an: Analysis) -> Dict[str, int]:
    """Jumlah footage, font, file plugin yang akan dicopy, dan perkiraan total ukurannya."""
    plugins = [cd for cd in an.candidates if cd.selected]
    size = sum(fe.size for fe in an.footage if fe.exists) + sum(cd.size for cd in plugins)
    for f in an.fonts:
        if f.face is not None:
            try:
                size += f.face.path.stat().st_size
            except OSError:
                pass
    return {"footage": len(an.footage), "fonts": len(an.fonts), "plugins": len(plugins), "bytes": size}


def _short_error(exc: BaseException) -> str:
    msg = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
    text = "%s: %s" % (type(exc).__name__, msg) if msg else type(exc).__name__
    return text[:300]


def prepare_env(env: Optional[Environment] = None) -> Environment:
    """Cari lokasi plugin sekali saja untuk semua project."""
    env = env or _collector.Environment()
    if env.plugin_roots is None:
        env.plugin_roots = default_roots(env.installs())
    if env.plugin_logs is None:
        env.plugin_logs = plugin_log_files()
    return env


#: Pilihan comp untuk satu project: mode (auto/rq/active/all) atau daftar id comp (kosong = dilewati).
Scope = Union[str, Sequence[int]]


def _run_many(paths: Sequence, options: Options, scope: str, comp_names: Sequence[str],
              env: Optional[Environment], progress: Optional[ProgressFn], cancel: Optional[threading.Event],
              on_item: Optional[Callable[[int, BatchItem], None]], include_guesses: bool,
              do_collect: bool, scopes: Optional[Sequence[Scope]] = None) -> BatchRun:
    env = prepare_env(env)
    run = BatchRun([BatchItem(Path(p)) for p in paths], Path(options.dest_dir), scope,
                   kind="collect" if do_collect else "analyze")
    total = len(run.items)

    def emit(i: int) -> None:
        if on_item is not None:
            on_item(i, run.items[i])

    for i, it in enumerate(run.items):
        if cancel is not None and cancel.is_set():
            break
        spec: Scope = scopes[i] if scopes is not None and i < len(scopes) else scope
        if not isinstance(spec, str) and not list(spec):
            it.status = "dilewati"          # tidak ada comp yang dicentang di project ini
            emit(i)
            continue
        it.status = "jalan"
        emit(i)
        prefix = "[%d/%d] %s: " % (i + 1, total, it.path.name)
        sub = (lambda m, _p=prefix: progress(_p + m)) if progress is not None else None
        try:
            if sub is not None:
                sub(_("Membaca project..."))
            aep = AepProject(it.path)
            if isinstance(spec, str):
                comp_ids, it.scope_kind, it.scope_names, it.n_comps = scope_parts(aep, spec, comp_names)
            else:
                comp_ids, it.scope_kind, it.scope_names, it.n_comps = ids_parts(aep, spec)
            opt = dataclasses.replace(options, comp_ids=comp_ids, scope_label="")
            an = analyze(aep, opt, env, progress=sub, cancel=cancel)
            if include_guesses:
                for cd in an.candidates:
                    cd.selected = True
            if not do_collect:
                it.counts = note_counts(an)
                it.info = analysis_info(an)
                it.status = "catatan" if it.counts else "ok"
            else:
                res = collect(an, progress=sub, cancel=cancel)
                it.result = res
                it.counts = note_counts(an, res)
                if not res.saved_ok:
                    it.status = "gagal"
                    it.error = (_("project hasil gagal dicek (%s); file sudah dicopy, pakai .aep di (Backup)")
                                % (res.validation_error or _("tidak diketahui")))
                else:
                    it.status = "catatan" if it.counts else "ok"
        except Cancelled:
            it.status = "dibatalkan"
            emit(i)
            break
        except Exception as exc:  # noqa: BLE001 - satu project gagal, lanjut ke berikutnya
            it.status = "gagal"
            it.error = _short_error(exc)
        emit(i)

    for i, it in enumerate(run.items):
        if it.status == "menunggu":
            it.status = "dibatalkan"
            emit(i)
    return run


def collect_many(paths: Sequence, options: Options, scope: str = "auto", comp_names: Sequence[str] = (),
                 env: Optional[Environment] = None, progress: Optional[ProgressFn] = None,
                 cancel: Optional[threading.Event] = None,
                 on_item: Optional[Callable[[int, BatchItem], None]] = None,
                 include_guesses: bool = False, write_summary: bool = True,
                 scopes: Optional[Sequence[Scope]] = None) -> BatchRun:
    """Collect setiap project ke ``options.dest_dir``. ``options.comp_ids`` diabaikan:
    comp tiap project dipilih dengan ``scope`` (lihat resolve_scope), atau per project lewat
    ``scopes`` (mode atau daftar id comp; daftar kosong = project dilewati)."""
    run = _run_many(paths, options, scope, comp_names, env, progress, cancel, on_item, include_guesses, True,
                    scopes)
    if write_summary and any(it.status not in ("dibatalkan", "dilewati") for it in run.items):
        try:
            run.summary = write_batch_summary(run)
        except OSError:
            run.summary = None
    return run


def analyze_many(paths: Sequence, options: Options, scope: str = "auto", comp_names: Sequence[str] = (),
                 env: Optional[Environment] = None, progress: Optional[ProgressFn] = None,
                 cancel: Optional[threading.Event] = None,
                 on_item: Optional[Callable[[int, BatchItem], None]] = None,
                 include_guesses: bool = False, scopes: Optional[Sequence[Scope]] = None) -> BatchRun:
    """Analisa setiap project tanpa menyalin apa pun: yang perlu dicek (footage hilang, font,
    plugin yang tidak ketemu) dan perkiraan ukuran hasil collect-nya."""
    return _run_many(paths, options, scope, comp_names, env, progress, cancel, on_item, include_guesses, False,
                     scopes)


def write_batch_summary(run: BatchRun) -> Path:
    run.dest.mkdir(parents=True, exist_ok=True)
    path = run.dest / ("CollectFilesPlus_batch_%s.txt" % time.strftime("%Y%m%d-%H%M%S"))
    n = 2
    while path.exists():
        path = run.dest / ("CollectFilesPlus_batch_%s (%d).txt" % (time.strftime("%Y%m%d-%H%M%S"), n))
        n += 1
    tag = {"ok": "[OK]", "catatan": _("[CATATAN]"), "gagal": _("[GAGAL]"), "dibatalkan": _("[DIBATALKAN]"),
           "menunggu": _("[DIBATALKAN]"), "jalan": "[?]", "dilewati": _("[DILEWATI]")}
    lines = [
        _("Collect Files Plus %s - ringkasan batch") % __version__,
        _("Tanggal : %s") % time.strftime("%Y-%m-%d %H:%M"),
        _("Folder  : %s") % run.dest,
        _("Comp    : %s") % _(SCOPE_LABEL.get(run.scope, run.scope)),
        _("Hasil   : %s") % run.headline(),
        "",
    ]
    attention = [it for it in run.items if it.status != "ok"]
    lines.append(_("=== PERLU DICEK ==="))
    if not attention:
        lines.append(_("Semua project berhasil di-collect tanpa catatan."))
    for it in attention:
        reason = it.error.splitlines()[0] if it.error else "; ".join(it.notes)
        lines.append("%-12s %s%s" % (tag.get(it.status, it.status), it.path.name, (": " + reason) if reason else ""))
    lines.append("")
    lines.append(_("=== SEMUA PROJECT ==="))
    for it in run.items:
        lines.append("%-12s %s" % (tag.get(it.status, it.status), it.path.name))
        lines.append(_("             asal    : %s") % it.path)
        if it.scope:
            lines.append(_("             comp    : %s") % it.scope)
        if it.result is not None:
            lines.append(_("             hasil   : %s") % it.result.dest_root)
        if it.notes:
            lines.append(_("             catatan : %s") % "; ".join(it.notes))
        if it.error:
            lines.append("             error   : %s" % it.error)
        lines.append("")
    lines.append(_("Detail tiap project ada di file _report.txt di folder hasilnya masing-masing."))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
