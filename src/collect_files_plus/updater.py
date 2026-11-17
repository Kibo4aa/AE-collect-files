"""Cek dan pasang update dari GitHub Releases.

Build exe Windows bisa mengganti dirinya sendiri: zip rilis diunduh, dicek SHA-256-nya,
diextract ke folder sementara, lalu skrip PowerShell kecil menunggu aplikasi ditutup,
menyalin file baru ke folder aplikasi (versi lama dicadangkan dan dikembalikan kalau
gagal), dan membuka aplikasi lagi. Di macOS / dari source: cukup diberi tahu dan
halaman rilis dibuka.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from . import __version__
from .i18n import _

REPO = "Kibo4aa/AE-collect-files"
API_LATEST = "https://api.github.com/repos/%s/releases/latest" % REPO
RELEASES_PAGE = "https://github.com/%s/releases/latest" % REPO
APP_EXE = "CollectFilesPlus.exe"
RESULT_ENV = "COLLECT_FILES_PLUS_UPDATE_RESULT"     # diisi skrip update untuk aplikasi yang dibuka ulang
NO_CHECK_ENV = "COLLECT_FILES_PLUS_NO_UPDATE_CHECK"


class UpdateCancelled(Exception):
    pass


def parse_version(text: str) -> Tuple[int, ...]:
    m = re.match(r"^\s*v?(\d+(?:\.\d+)*)", text or "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def is_newer(latest: str, current: str = __version__) -> bool:
    a, b = parse_version(latest), parse_version(current)
    if not a:
        return False
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def platform_suffix() -> Optional[str]:
    if sys.platform == "win32":
        return "-windows-x64.zip"
    if sys.platform == "darwin":
        return "-macos-arm64.zip"
    return None


@dataclass
class UpdateInfo:
    version: str
    tag: str
    page: str
    notes: str = ""
    asset_name: str = ""
    asset_url: str = ""
    asset_size: int = 0
    sha256: str = ""

    @property
    def newer(self) -> bool:
        return is_newer(self.version)


def _ssl_context() -> ssl.SSLContext:
    if sys.platform == "darwin":  # app beku di macOS tidak membawa sertifikat sistem untuk OpenSSL
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except Exception:  # noqa: BLE001
            pass
    return ssl.create_default_context()


def _open(url: str, timeout: float):
    req = urllib.request.Request(url, headers={"User-Agent": "CollectFilesPlus/" + __version__,
                                               "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout, context=_ssl_context())


def check_latest(timeout: float = 10.0) -> Optional[UpdateInfo]:
    """Rilis terbaru di GitHub, atau None kalau belum ada rilis. Error jaringan dilempar."""
    try:
        with _open(API_LATEST, timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    tag = data.get("tag_name") or ""
    info = UpdateInfo(version=tag.lstrip("vV"), tag=tag, page=data.get("html_url") or RELEASES_PAGE,
                      notes=data.get("body") or "")
    suffix = platform_suffix()
    for asset in data.get("assets") or []:
        name = asset.get("name") or ""
        if suffix and name.endswith(suffix):
            info.asset_name = name
            info.asset_url = asset.get("browser_download_url") or ""
            info.asset_size = int(asset.get("size") or 0)
            digest = asset.get("digest") or ""
            if digest.startswith("sha256:"):
                info.sha256 = digest[7:].lower()
            break
    return info


def app_dir() -> Path:
    return Path(sys.executable).resolve().parent


def _writable(folder: Path) -> bool:
    probe = folder / (".cfp-write-test-%d" % os.getpid())
    try:
        probe.write_bytes(b"")
        probe.unlink()
        return True
    except OSError:
        return False


def can_self_update() -> bool:
    """Hanya build exe Windows di folder yang bisa ditulisi yang bisa mengganti dirinya sendiri."""
    return (sys.platform == "win32" and bool(getattr(sys, "frozen", False))
            and (app_dir() / APP_EXE).is_file() and _writable(app_dir()))


def download(info: UpdateInfo, dest_dir: Path, progress: Optional[Callable[[int, int], None]] = None,
             cancel: Optional[threading.Event] = None) -> Path:
    if not info.asset_url:
        raise OSError(_("Rilis ini tidak punya file untuk sistem ini."))
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / (info.asset_name or "update.zip")
    digest = hashlib.sha256()
    with _open(info.asset_url, 60) as resp, open(path, "wb") as out:
        total = int(resp.headers.get("Content-Length") or info.asset_size or 0)
        done = 0
        while True:
            if cancel is not None and cancel.is_set():
                raise UpdateCancelled()
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            out.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if progress is not None:
                progress(done, total)
    if info.sha256 and digest.hexdigest() != info.sha256:
        path.unlink()
        raise OSError(_("File update rusak (checksum tidak cocok). Coba lagi."))
    return path


def extract_app(zip_path: Path, dest_dir: Path) -> Path:
    """Extract zip rilis, kembalikan folder yang berisi CollectFilesPlus.exe."""
    dest_dir = Path(dest_dir).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            target = (dest_dir / name).resolve()
            if target != dest_dir and dest_dir not in target.parents:
                raise OSError(_("Isi file update tidak valid."))
        z.extractall(dest_dir)
    for exe in sorted(dest_dir.rglob(APP_EXE), key=lambda p: len(p.parts)):
        return exe.parent
    raise OSError(_("Isi update tidak lengkap (CollectFilesPlus.exe tidak ada)."))


# Dijalankan setelah aplikasi ditutup. Path lewat variabel lingkungan supaya aman dari spasi dsb.
APPLY_PS1 = r"""
$ErrorActionPreference = 'Continue'
$log = $env:CFP_LOG
function Log($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format s) + '  ' + $m) }
function Copy-Dir($from, $to, $opts) {
    $rcArgs = @($from, $to) + $opts + @('/R:5', '/W:1', '/NP', '/NFL', '/NDL', '/NJH', '/NJS')
    & robocopy @rcArgs | Out-Null
    return ($LASTEXITCODE -lt 8)
}
$app = $env:CFP_APP; $new = $env:CFP_NEW; $bak = Join-Path $env:CFP_TMP 'backup'
$appInt = Join-Path $app '_internal'; $newInt = Join-Path $new '_internal'; $bakInt = Join-Path $bak '_internal'
Log "menunggu aplikasi ditutup (pid $env:CFP_PID)"
try { Wait-Process -Id ([int]$env:CFP_PID) -Timeout 120 -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Milliseconds 800
# cadangan: hanya file program (folder _internal + file di folder utama)
$ok = (Copy-Dir $appInt $bakInt @('/E')) -and (Copy-Dir $app $bak @('/LEV:1'))
if (-not $ok) { Log 'gagal membuat cadangan, update dibatalkan' }
if ($ok) {
    $ok = (Copy-Dir $newInt $appInt @('/MIR')) -and (Copy-Dir $new $app @('/E', '/XD', $newInt))
    if (-not $ok) {
        Log 'gagal menyalin versi baru, mengembalikan versi lama'
        Copy-Dir $bakInt $appInt @('/MIR') | Out-Null
        Copy-Dir $bak $app @('/LEV:1') | Out-Null
    }
}
if ($ok) { Log 'selesai'; $env:COLLECT_FILES_PLUS_UPDATE_RESULT = 'ok:' + $env:CFP_VERSION }
else { $env:COLLECT_FILES_PLUS_UPDATE_RESULT = 'failed:' + $log }
if (-not $env:CFP_NO_RESTART) { Start-Process -FilePath (Join-Path $app 'CollectFilesPlus.exe') -WorkingDirectory $app }
if ($ok) {
    Remove-Item -LiteralPath $new -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $bak -Recurse -Force -ErrorAction SilentlyContinue
}
"""


def apply_command(new_dir: Path, tmp_dir: Path, version: str, app: Optional[Path] = None,
                  pid: Optional[int] = None, restart: bool = True) -> Tuple[List[str], dict]:
    """Perintah + environment untuk skrip PowerShell yang memasang update."""
    tmp_dir = Path(tmp_dir)
    script = tmp_dir / "pasang-update.ps1"
    script.write_text(APPLY_PS1, encoding="utf-8-sig")
    env = dict(os.environ, CFP_APP=str(app or app_dir()), CFP_NEW=str(new_dir), CFP_TMP=str(tmp_dir),
               CFP_LOG=str(tmp_dir / "update-log.txt"), CFP_PID=str(pid if pid is not None else os.getpid()),
               CFP_VERSION=version)
    env.pop(RESULT_ENV, None)
    if not restart:
        env["CFP_NO_RESTART"] = "1"
    args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-WindowStyle", "Hidden", "-File", str(script)]
    return args, env


def launch_apply(new_dir: Path, tmp_dir: Path, version: str) -> None:
    """Jalankan skrip pemasang di latar belakang; setelah ini aplikasi harus ditutup."""
    args, env = apply_command(new_dir, tmp_dir, version)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(args, env=env, creationflags=flags, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def take_update_result() -> Optional[Tuple[bool, str]]:
    """Hasil update sebelumnya (dari skrip pemasang), sekali baca: (berhasil, versi atau path log)."""
    raw = os.environ.pop(RESULT_ENV, "")
    if not raw:
        return None
    status, _sep, detail = raw.partition(":")
    return status == "ok", detail
