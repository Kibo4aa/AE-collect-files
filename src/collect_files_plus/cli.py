"""Command line.

Contoh:
    collect-files-plus list-comps project.aep
    collect-files-plus analyze project.aep --rq
    collect-files-plus collect project.aep -o D:/Hasil --comp "Main" --reduce
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from . import __version__


def _scope(aep, args) -> Tuple[Optional[List[int]], str]:
    if args.all:
        return None, ""
    if args.comp:
        wanted = set(args.comp)
        roots = [c for c in aep.comps if c.name in wanted]
        missing = wanted - {c.name for c in roots}
        if missing:
            raise SystemExit("Comp tidak ditemukan: " + ", ".join(sorted(missing)))
        return [c.id for c in roots], ""
    if args.rq:
        roots = aep.rq_comps()
        if not roots:
            raise SystemExit("Render Queue kosong.")
        return [c.id for c in roots], ""
    mode, roots = aep.default_roots()
    if mode == "all":
        return None, ""
    return [c.id for c in roots], ""


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("project", type=Path, help="file .aep")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--comp", action="append", metavar="NAMA",
                   help="comp utama (boleh diulang). Precomp di dalamnya ikut dibaca.")
    g.add_argument("--rq", action="store_true", help="comp yang ada di Render Queue")
    g.add_argument("--all", action="store_true", help="semua comp di project")
    p.add_argument("--no-footage", action="store_true", help="jangan collect footage")
    p.add_argument("--no-fonts", action="store_true", help="jangan collect font")
    p.add_argument("--no-plugins", action="store_true", help="jangan collect plugin")
    p.add_argument("--include-disabled", action="store_true", help="ikutkan efek yang ikon fx-nya mati")
    p.add_argument("--support-files", action="store_true",
                   help="ikut copy file pendukung plugin (DLL/data di folder yang sama, tanpa plugin lain)")
    p.add_argument("--reduce", action="store_true",
                   help="buang comp & footage yang tidak dipakai dari project hasil (Reduce Project)")
    p.add_argument("--presets", action="store_true",
                   help="ikut copy animation preset (.ffx) yang namanya sama dengan efek yang di-rename")
    p.add_argument("--include-guesses", action="store_true",
                   help="ikut copy plugin yang hanya ditemukan lewat perkiraan")


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


def main(argv: Optional[Sequence[str]] = None) -> int:
    _safe_streams()
    parser = argparse.ArgumentParser(
        prog="collect-files-plus",
        description="Kumpulkan footage, font, dan plugin dari project After Effects tanpa membuka AE.")
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list-comps", help="daftar comp di project")
    p_list.add_argument("project", type=Path)

    p_an = sub.add_parser("analyze", help="analisa saja, tidak menyalin apa pun")
    _add_common(p_an)

    p_col = sub.add_parser("collect", help="collect ke folder tujuan")
    _add_common(p_col)
    p_col.add_argument("-o", "--output", type=Path, required=True, help="folder tujuan")

    sub.add_parser("gui", help="buka jendela aplikasi")

    args = parser.parse_args(argv)
    if args.cmd in (None, "gui"):
        from .gui import main as gui_main
        return gui_main()

    from .collector import Cancelled, analyze, collect
    from .project import AepProject
    from .report import build_report

    if not args.project.is_file():
        print("File tidak ditemukan: %s" % args.project, file=sys.stderr)
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
                tags.append("aktif")
            if users.get(c.id):
                tags.append("precomp di %d comp" % users[c.id])
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
    print("Selesai: %s" % res.dest_root)
    if res.report:
        print("Laporan: %s" % res.report)
    if not res.saved_ok:
        print("PERHATIAN: %s" % res.validation_error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
