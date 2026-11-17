"""Uji update lewat installer .msi di CI (Windows), persis seperti tombol "Update sekarang":
skrip pemasang dari updater menunggu aplikasi tertutup, menjalankan msiexec untuk versi baru,
lalu mencatat hasilnya.

    python packaging/msi_upgrade_test.py <installer-versi-baru.msi> <folder aplikasi terpasang> <versi>
"""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from collect_files_plus import updater  # noqa: E402


def _read(path: Path) -> str:
    data = path.read_bytes() if path.is_file() else b""
    return data.decode("utf-16", "replace") if data[:2] == b"\xff\xfe" else data.decode("latin-1")


def main() -> int:
    msi, app, version = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), sys.argv[3]
    tmp = Path(tempfile.mkdtemp(prefix="cfp-msi-"))
    done = subprocess.Popen([sys.executable, "-c", "pass"])   # "aplikasi" yang sudah tertutup
    done.wait()
    args, env = updater.msi_command(msi, tmp, version, app=app, pid=done.pid, restart=False)
    subprocess.run(args, env=env, check=True, timeout=900)
    log = _read(tmp / "update-log.txt")
    print(log)
    if "msiexec selesai: 0" not in log and "msiexec selesai: 3010" not in log:
        print(_read(tmp / "msi-log.txt")[-6000:])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
