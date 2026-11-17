"""Titik masuk build PyInstaller (CollectFilesPlus.exe dan collect-files-plus.exe)."""

import os
import sys

# Exe tanpa jendela console (windowed) tidak punya stdout/stderr di Windows.
if sys.stdout is None or sys.stderr is None:
    _null = open(os.devnull, "w", encoding="utf-8")
    sys.stdout = sys.stdout or _null
    sys.stderr = sys.stderr or _null

from collect_files_plus.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
