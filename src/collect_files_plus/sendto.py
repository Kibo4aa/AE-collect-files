"""Shortcut di menu klik kanan "Send to" Windows Explorer.

Pilih beberapa file .aep (atau folder) di Explorer -> klik kanan -> Send to ->
Collect Files Plus. Semua file terpilih dikirim sekaligus ke aplikasi (mode batch).
"""

from __future__ import annotations

import base64
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

LINK_NAME = "Collect Files Plus.lnk"

_PS_CREATE = r"""
$ErrorActionPreference = 'Stop'
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($env:CFP_LNK)
$s.TargetPath = $env:CFP_TARGET
$s.Arguments = $env:CFP_ARGS
$s.WorkingDirectory = $env:CFP_WORKDIR
if ($env:CFP_ICON) { $s.IconLocation = $env:CFP_ICON }
$s.Description = 'Collect Files Plus: collect project After Effects (bisa banyak sekaligus)'
$s.Save()
"""


def available() -> bool:
    return sys.platform == "win32"


def sendto_dir() -> Optional[Path]:
    appdata = os.environ.get("APPDATA")
    return Path(appdata) / "Microsoft" / "Windows" / "SendTo" if appdata else None


def link_path() -> Optional[Path]:
    d = sendto_dir()
    return d / LINK_NAME if d is not None else None


def installed() -> bool:
    link = link_path()
    return link is not None and link.is_file()


def launch_command() -> Tuple[str, str, str]:
    """(program, argumen, ikon) untuk membuka aplikasi ini."""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable)
        gui = exe.with_name("CollectFilesPlus.exe")  # dari exe CLI pun tetap buka versi GUI
        target = gui if gui.is_file() else exe
        return str(target), "", str(target) + ",0"
    py = Path(sys.executable)
    pyw = py.with_name("pythonw.exe")
    return str(pyw if pyw.is_file() else py), "-m collect_files_plus", ""


def powershell_args(script: str) -> list:
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", encoded]


def install() -> Path:
    """Buat shortcut di folder SendTo. Mengembalikan path shortcut."""
    link = link_path()
    if link is None:
        raise OSError("Folder SendTo tidak ditemukan (APPDATA kosong).")
    link.parent.mkdir(parents=True, exist_ok=True)
    target, args, icon = launch_command()
    env = dict(os.environ, CFP_LNK=str(link), CFP_TARGET=target, CFP_ARGS=args, CFP_ICON=icon,
               CFP_WORKDIR=str(Path(target).parent))
    proc = subprocess.run(powershell_args(_PS_CREATE), env=env, capture_output=True, text=True,
                          errors="replace", timeout=60,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if proc.returncode != 0 or not link.is_file():
        detail = (proc.stderr or proc.stdout or "").strip()
        raise OSError("Gagal membuat shortcut Send to. %s" % detail[:400])
    return link


def uninstall() -> None:
    link = link_path()
    if link is not None and link.exists():
        link.unlink()
