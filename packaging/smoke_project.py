"""Membuat project .aep contoh (footage asli + sequence + teks) untuk uji build di CI.

    python packaging/smoke_project.py FOLDER   -> mencetak path file .aep
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from helpers import make_project  # noqa: E402

if __name__ == "__main__":
    print(make_project(Path(sys.argv[1])))
