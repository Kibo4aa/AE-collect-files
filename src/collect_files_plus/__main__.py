"""`python -m collect_files_plus` -> GUI (tanpa argumen) atau CLI."""

import os
import sys
from typing import List, Optional


def _gui_paths(args: List[str]) -> Optional[List[str]]:
    """Semua argumen file .aep / folder -> dibuka di GUI.

    Terjadi saat file di-drag ke ikon aplikasi atau dikirim lewat menu "Send to".
    """
    if not args:
        return None
    for a in args:
        if not ((a.lower().endswith(".aep") and os.path.isfile(a)) or os.path.isdir(a)):
            return None
    return args


def main() -> int:
    args = sys.argv[1:]
    paths = _gui_paths(args)
    if paths is not None:
        from .gui import main as gui_main
        if len(paths) == 1 and os.path.isfile(paths[0]):
            return gui_main(paths[0])          # satu project -> mode biasa
        return gui_main(batch=paths)           # banyak project / folder -> tab Batch
    if args:
        from .cli import main as cli_main
        return cli_main(args)
    from .gui import main as gui_main
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
