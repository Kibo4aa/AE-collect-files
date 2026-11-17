"""`python -m collect_files_plus` -> GUI (tanpa argumen) atau CLI."""

import os
import sys


def main() -> int:
    args = sys.argv[1:]
    # File .aep yang di-drag ke ikon aplikasi -> buka GUI dengan file itu.
    if len(args) == 1 and args[0].lower().endswith(".aep") and os.path.isfile(args[0]):
        from .gui import main as gui_main
        return gui_main(args[0])
    if args:
        from .cli import main as cli_main
        return cli_main(args)
    from .gui import main as gui_main
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
