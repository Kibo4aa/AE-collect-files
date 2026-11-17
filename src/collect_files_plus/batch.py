"""Collect banyak project .aep sekaligus ke satu folder tujuan.

Setiap project tetap mendapat folder hasil sendiri (``<nama>_Collected``) di dalam
folder tujuan, jadi relink footage tiap project tidak saling bentrok. Satu project
yang gagal tidak menghentikan project lain.
"""

from __future__ import annotations

import dataclasses
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

from . import __version__
from . import collector as _collector
from .collector import Analysis, Cancelled, Environment, Options, Result, analyze, collect
from .plugins import default_roots, plugin_log_files
from .project import AepProject

ProgressFn = Callable[[str], None]

SCOPE_LABEL = {
    "auto": "otomatis (Render Queue, kalau kosong comp aktif, kalau tidak ada semua comp)",
    "rq": "comp di Render Queue",
    "active": "comp aktif saat project disimpan",
    "all": "semua comp",
    "names": "comp dengan nama tertentu",
}

STATUS_LABEL = {
    "menunggu": "menunggu",
    "jalan": "sedang diproses...",
    "ok": "OK",
    "catatan": "OK, ada catatan",
    "gagal": "GAGAL",
    "dibatalkan": "dibatalkan",
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


def resolve_scope(aep: AepProject, mode: str = "auto",
                  names: Sequence[str] = ()) -> Tuple[Optional[List[int]], str]:
    """Comp utama yang dibaca. Mengembalikan (comp_ids atau None = semua, keterangan).

    mode: auto | rq | active | all | names. ValueError kalau comp yang diminta tidak ada.
    """
    if mode == "all":
        return None, "semua comp (%d)" % len(aep.comps)
    if mode == "names":
        wanted = list(dict.fromkeys(names))
        roots = [c for c in aep.comps if c.name in set(wanted)]
        missing = set(wanted) - {c.name for c in roots}
        if missing:
            raise ValueError("Comp tidak ditemukan: " + ", ".join(sorted(missing)))
        return [c.id for c in roots], "comp: " + ", ".join(c.name for c in roots)
    if mode == "rq":
        roots = aep.rq_comps()
        if not roots:
            raise ValueError("Render Queue kosong.")
        return [c.id for c in roots], "Render Queue: " + ", ".join(c.name for c in roots)
    if mode == "active":
        act = aep.active_comp()
        if act is None:
            raise ValueError("Tidak ada comp aktif yang tersimpan di project ini.")
        return [act.id], "comp aktif: " + act.name
    kind, roots = aep.default_roots()
    if kind == "all":
        return None, "semua comp (%d)" % len(aep.comps)
    label = "Render Queue" if kind == "rq" else "comp aktif"
    return [c.id for c in roots], label + ": " + ", ".join(c.name for c in roots)


@dataclass
class BatchItem:
    path: Path
    status: str = "menunggu"            # menunggu / jalan / ok / catatan / gagal / dibatalkan
    scope: str = ""
    result: Optional[Result] = None
    error: str = ""
    notes: List[str] = field(default_factory=list)

    @property
    def status_text(self) -> str:
        text = STATUS_LABEL.get(self.status, self.status)
        if self.status == "catatan" and self.notes:
            return "OK, " + "; ".join(self.notes)
        if self.status == "gagal" and self.error:
            return "GAGAL: " + self.error
        return text

    @property
    def result_name(self) -> str:
        return self.result.dest_root.name if self.result is not None else ""


@dataclass
class BatchRun:
    items: List[BatchItem]
    dest: Path
    scope: str
    summary: Optional[Path] = None

    def count(self, *statuses: str) -> int:
        return sum(1 for it in self.items if it.status in statuses)

    @property
    def ok(self) -> bool:
        return self.count("gagal", "dibatalkan") == 0

    def headline(self) -> str:
        parts = ["%d OK" % self.count("ok")]
        if self.count("catatan"):
            parts.append("%d ada catatan" % self.count("catatan"))
        if self.count("gagal"):
            parts.append("%d gagal" % self.count("gagal"))
        if self.count("dibatalkan", "menunggu"):
            parts.append("%d tidak diproses" % self.count("dibatalkan", "menunggu"))
        return "%s (dari %d project)" % (", ".join(parts), len(self.items))


def notes_for(an: Analysis, res: Result) -> List[str]:
    notes: List[str] = []
    missing = sum(1 for fe in an.footage if not fe.exists)
    if missing:
        notes.append("%d footage hilang" % missing)
    nf = sum(1 for f in an.fonts if f.status == "tidak-ketemu")
    if nf:
        notes.append("%d font tidak ketemu" % nf)
    na = sum(1 for f in an.fonts if f.status == "adobe")
    if na:
        notes.append("%d Adobe Fonts (aktifkan di CC)" % na)
    if an.options.collect_plugins:
        nx = sum(1 for e in an.plugin_effects if e.candidate is None)
        if nx:
            notes.append("%d efek plugin tidak ketemu" % nx)
        ng = sum(1 for cd in an.candidates if not cd.selected)
        if ng:
            notes.append("%d plugin perkiraan tidak dicopy" % ng)
    if res.errors:
        notes.append("%d error saat copy" % len(res.errors))
    return notes


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


def collect_many(paths: Sequence, options: Options, scope: str = "auto", comp_names: Sequence[str] = (),
                 env: Optional[Environment] = None, progress: Optional[ProgressFn] = None,
                 cancel: Optional[threading.Event] = None,
                 on_item: Optional[Callable[[int, BatchItem], None]] = None,
                 include_guesses: bool = False, write_summary: bool = True) -> BatchRun:
    """Collect setiap project ke ``options.dest_dir``. ``options.comp_ids`` diabaikan:
    comp tiap project dipilih dengan ``scope`` (lihat resolve_scope)."""
    env = prepare_env(env)
    run = BatchRun([BatchItem(Path(p)) for p in paths], Path(options.dest_dir), scope)
    total = len(run.items)

    def emit(i: int) -> None:
        if on_item is not None:
            on_item(i, run.items[i])

    for i, it in enumerate(run.items):
        if cancel is not None and cancel.is_set():
            break
        it.status = "jalan"
        emit(i)
        prefix = "[%d/%d] %s: " % (i + 1, total, it.path.name)
        sub = (lambda m, _p=prefix: progress(_p + m)) if progress is not None else None
        try:
            if sub is not None:
                sub("Membaca project...")
            aep = AepProject(it.path)
            comp_ids, it.scope = resolve_scope(aep, scope, comp_names)
            opt = dataclasses.replace(options, comp_ids=comp_ids, scope_label="")
            an = analyze(aep, opt, env, progress=sub, cancel=cancel)
            if include_guesses:
                for cd in an.candidates:
                    cd.selected = True
            res = collect(an, progress=sub, cancel=cancel)
            it.result = res
            it.notes = notes_for(an, res)
            if not res.saved_ok:
                it.status = "gagal"
                it.error = ("project hasil gagal dicek (%s); file sudah dicopy, pakai .aep di (Backup)"
                            % (res.validation_error or "tidak diketahui"))
            else:
                it.status = "catatan" if it.notes else "ok"
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
    if write_summary and any(it.status != "dibatalkan" for it in run.items):
        try:
            run.summary = write_batch_summary(run)
        except OSError:
            run.summary = None
    return run


def write_batch_summary(run: BatchRun) -> Path:
    run.dest.mkdir(parents=True, exist_ok=True)
    path = run.dest / ("CollectFilesPlus_batch_%s.txt" % time.strftime("%Y%m%d-%H%M%S"))
    n = 2
    while path.exists():
        path = run.dest / ("CollectFilesPlus_batch_%s (%d).txt" % (time.strftime("%Y%m%d-%H%M%S"), n))
        n += 1
    tag = {"ok": "[OK]", "catatan": "[CATATAN]", "gagal": "[GAGAL]", "dibatalkan": "[DIBATALKAN]",
           "menunggu": "[DIBATALKAN]", "jalan": "[?]"}
    lines = [
        "Collect Files Plus %s - ringkasan batch" % __version__,
        "Tanggal : %s" % time.strftime("%Y-%m-%d %H:%M"),
        "Folder  : %s" % run.dest,
        "Comp    : %s" % SCOPE_LABEL.get(run.scope, run.scope),
        "Hasil   : %s" % run.headline(),
        "",
    ]
    for it in run.items:
        lines.append("%-12s %s" % (tag.get(it.status, it.status), it.path.name))
        lines.append("             asal    : %s" % it.path)
        if it.scope:
            lines.append("             comp    : %s" % it.scope)
        if it.result is not None:
            lines.append("             hasil   : %s" % it.result.dest_root)
        if it.notes:
            lines.append("             catatan : %s" % "; ".join(it.notes))
        if it.error:
            lines.append("             error   : %s" % it.error)
        lines.append("")
    lines.append("Detail tiap project ada di file _report.txt di folder hasilnya masing-masing.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
