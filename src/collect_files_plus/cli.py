"""Command line.

Contoh:
    collect-files-plus list-comps project.aep
    collect-files-plus analyze project.aep --rq
    collect-files-plus collect project.aep -o D:/Hasil --comp "Main" --reduce
    collect-files-plus collect a.aep b.aep "D:/Folder Project" -o D:/Hasil     (banyak project)
    collect-files-plus --lang en analyze project.aep                            (output English)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from . import __version__
from .i18n import LANGS, _, set_language, system_language


def _scope_mode(args) -> Tuple[str, Sequence[str]]:
    if args.all:
        return "all", ()
    if args.comp:
        return "names", args.comp
    if args.rq:
        return "rq", ()
    return "auto", ()


def _scope(aep, args) -> Tuple[Optional[List[int]], str]:
    from .batch import resolve_scope
    mode, names = _scope_mode(args)
    try:
        comp_ids, _label = resolve_scope(aep, mode, names)
    except ValueError as exc:
        raise SystemExit(str(exc))
    return comp_ids, ""


def _add_common(p: argparse.ArgumentParser, multi: bool = False) -> None:
    if multi:
        p.add_argument("projects", type=Path, nargs="+", metavar="project",
                       help=_("file .aep, boleh lebih dari satu; folder = semua .aep di dalamnya"))
    else:
        p.add_argument("project", type=Path, help=_("file .aep"))
    g = p.add_mutually_exclusive_group()
    g.add_argument("--comp", action="append", metavar=_("NAMA"),
                   help=_("comp utama (boleh diulang). Precomp di dalamnya ikut dibaca."))
    g.add_argument("--rq", action="store_true", help=_("comp yang ada di Render Queue"))
    g.add_argument("--all", action="store_true", help=_("semua comp di project"))
    p.add_argument("--no-footage", action="store_true", help=_("jangan collect footage"))
    p.add_argument("--no-fonts", action="store_true", help=_("jangan collect font"))
    p.add_argument("--no-plugins", action="store_true", help=_("jangan collect plugin"))
    p.add_argument("--include-disabled", action="store_true", help=_("ikutkan efek yang ikon fx-nya mati"))
    p.add_argument("--support-files", action="store_true",
                   help=_("ikut copy file pendukung plugin (DLL/data di folder yang sama, tanpa plugin lain)"))
    p.add_argument("--reduce", action="store_true",
                   help=_("buang comp & footage yang tidak dipakai dari project hasil (Reduce Project)"))
    p.add_argument("--presets", action="store_true",
                   help=_("ikut copy animation preset (.ffx) yang namanya sama dengan efek yang di-rename"))
    p.add_argument("--include-guesses", action="store_true",
                   help=_("ikut copy plugin yang hanya ditemukan lewat perkiraan"))


def _options(args, dest: Path, comp_ids):
    from .collector import Options
    return Options(
        dest_dir=dest,
        comp_ids=comp_ids,
        collect_footage=not args.no_footage,
        reduce_project=args.reduce,
        collect_fonts=not args.no_fonts,
        collect_plugins=not args.no_plugins,
        skip_disabled=not args.include_disabled,
        support_files=args.support_files,
        presets=args.presets,
    )


def _progress(msg: str) -> None:
    if sys.stderr.isatty():
        sys.stderr.write("\r" + msg[:110].ljust(110))
        sys.stderr.flush()


def _safe_streams() -> None:
    # Output yang di-redirect ke file di Windows memakai code page lama (cp1252 dsb.):
    # nama comp/file berhuruf Jepang tidak boleh membuat program berhenti.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def _take_lang(argv: List[str]) -> Tuple[List[str], Optional[str]]:
    """Ambil --lang dari mana pun posisinya (sebelum parser dibuat, supaya --help ikut bahasanya)."""
    out: List[str] = []
    lang = None
    it = iter(argv)
    for a in it:
        if a == "--lang":
            lang = next(it, None)
        elif a.startswith("--lang="):
            lang = a.split("=", 1)[1]
        else:
            out.append(a)
    return out, lang


def main(argv: Optional[Sequence[str]] = None) -> int:
    _safe_streams()
    argv, lang = _take_lang(list(sys.argv[1:] if argv is None else argv))
    if lang is not None and lang not in LANGS:
        print("--lang: id / en", file=sys.stderr)
        return 2
    set_language(lang or system_language())

    parser = argparse.ArgumentParser(
        prog="collect-files-plus",
        description=_("Kumpulkan footage, font, dan plugin dari project After Effects tanpa membuka AE."))
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    parser.add_argument("--lang", choices=sorted(LANGS), help=_("bahasa output: id (Indonesia) atau en (English)"))
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list-comps", help=_("daftar comp di project"))
    p_list.add_argument("project", type=Path)

    p_an = sub.add_parser("analyze", help=_("analisa saja, tidak menyalin apa pun"))
    _add_common(p_an)

    p_col = sub.add_parser("collect", help=_("collect ke folder tujuan (bisa banyak project sekaligus)"))
    _add_common(p_col, multi=True)
    p_col.add_argument("-o", "--output", type=Path, required=True, help=_("folder tujuan"))

    sub.add_parser("gui", help=_("buka jendela aplikasi"))
    sub.add_parser("update", help=_("cek versi terbaru di GitHub"))

    args = parser.parse_args(argv)
    if args.cmd in (None, "gui"):
        from .gui import main as gui_main
        return gui_main()
    if args.cmd == "update":
        return _check_update()

    from .collector import Cancelled, analyze, collect
    from .project import AepProject
    from .report import build_report

    if args.cmd == "collect":
        if len(args.projects) > 1 or args.projects[0].is_dir():
            return _collect_batch(args)
        args.project = args.projects[0]

    if not args.project.is_file():
        print(_("File tidak ditemukan: %s") % args.project, file=sys.stderr)
        return 2
    aep = AepProject(args.project)

    if args.cmd == "list-comps":
        rq = {c.id for c in aep.rq_comps()}
        act = aep.active_comp()
        users = aep.precomp_users()
        for c in aep.comps:
            tags = []
            if c.id in rq:
                tags.append("Render Queue")
            if act is not None and c.id == act.id:
                tags.append(_("aktif"))
            if users.get(c.id):
                tags.append(_("precomp di %d comp") % users[c.id])
            print("%-40s %s" % (c.name, ", ".join(tags)))
        return 0

    comp_ids, _label = _scope(aep, args)
    dest = getattr(args, "output", None) or Path(".")
    opt = _options(args, dest, comp_ids)
    try:
        an = analyze(aep, opt, progress=_progress)
        if args.include_guesses:
            for cd in an.candidates:
                cd.selected = True
        if args.cmd == "analyze":
            if sys.stderr.isatty():
                sys.stderr.write("\n")
            print("\n".join(build_report(an)))
            return 0
        res = collect(an, progress=_progress)
    except Cancelled:
        return 130
    if sys.stderr.isatty():
        sys.stderr.write("\n")
    print(_("Selesai: %s") % res.dest_root)
    if res.report:
        print(_("Laporan: %s") % res.report)
    if not res.saved_ok:
        print(_("PERHATIAN: %s") % res.validation_error, file=sys.stderr)
        return 1
    return 0


def _check_update() -> int:
    from . import updater
    try:
        info = updater.check_latest()
    except Exception as exc:  # noqa: BLE001
        print(_("Tidak bisa mengecek update:\n%s") % exc, file=sys.stderr)
        return 1
    print(_("Versi ini     : %s") % __version__)
    if info is None:
        print(_("Belum ada rilis di GitHub."))
        return 0
    print(_("Versi terbaru : %s") % info.version)
    if info.newer:
        print(_("Download      : %s") % info.page)
        print(_("Di aplikasi (jendela), klik \"Update sekarang\" untuk memasang otomatis."))
    else:
        print(_("Kamu sudah memakai versi terbaru (%s).") % __version__)
    return 0


def _collect_batch(args) -> int:
    from .batch import collect_many, find_projects

    missing = [p for p in args.projects if not p.exists()]
    for p in missing:
        print(_("Tidak ditemukan: %s") % p, file=sys.stderr)
    files = find_projects(args.projects)
    if not files:
        print(_("Tidak ada file .aep yang ditemukan."), file=sys.stderr)
        return 2
    mode, names = _scope_mode(args)
    print(_("Collect %d project ke %s") % (len(files), args.output))
    tag = {"ok": "OK", "catatan": _("CATATAN"), "gagal": _("GAGAL"), "dibatalkan": _("DIBATALKAN")}

    def on_item(i, it) -> None:
        if it.status not in tag:
            return
        if sys.stderr.isatty():
            sys.stderr.write("\r" + " " * 110 + "\r")
        line = "[%d/%d] %-10s %s" % (i + 1, len(files), tag[it.status], it.path)
        if it.result is not None:
            line += "  ->  %s" % it.result.dest_root.name
        if it.notes:
            line += "  (%s)" % "; ".join(it.notes)
        if it.error:
            line += "\n        %s" % it.error
        print(line)

    run = collect_many(files, _options(args, args.output, None), mode, names, progress=_progress,
                       on_item=on_item, include_guesses=args.include_guesses)
    print(run.headline())
    if run.summary is not None:
        print(_("Ringkasan: %s") % run.summary)
    return 0 if run.ok and not missing else 1


if __name__ == "__main__":
    sys.exit(main())
