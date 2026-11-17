"""Shortcut "Send to" (Windows Explorer)."""

import base64
import sys
import types
from pathlib import Path

import pytest

from collect_files_plus import sendto


def test_install_builds_powershell_command(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    calls = []

    def fake_run(args, env=None, **kw):
        calls.append((args, env))
        Path(env["CFP_LNK"]).write_bytes(b"lnk")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sendto.subprocess, "run", fake_run)
    link = sendto.install()
    assert link == tmp_path / "Microsoft" / "Windows" / "SendTo" / "Collect Files Plus.lnk"
    assert sendto.installed()
    args, env = calls[0]
    assert args[0] == "powershell.exe" and args[-2] == "-EncodedCommand"
    script = base64.b64decode(args[-1]).decode("utf-16-le")
    assert "CreateShortcut($env:CFP_LNK)" in script and "$s.Save()" in script
    assert env["CFP_ARGS"] == "-m collect_files_plus"
    sendto.uninstall()
    assert not sendto.installed()


def test_frozen_uses_gui_exe(tmp_path: Path, monkeypatch):
    app = tmp_path / "CollectFilesPlus"
    app.mkdir()
    (app / "CollectFilesPlus.exe").write_bytes(b"")
    (app / "collect-files-plus.exe").write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(app / "collect-files-plus.exe"))
    target, args, icon = sendto.launch_command()
    assert target == str(app / "CollectFilesPlus.exe") and args == "" and icon.endswith(",0")


def test_install_error_is_reported(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(sendto.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(returncode=1, stdout="", stderr="Akses ditolak"))
    with pytest.raises(OSError, match="Akses ditolak"):
        sendto.install()


@pytest.mark.skipif(sys.platform != "win32", reason="khusus Windows")
def test_install_real_shortcut(tmp_path: Path, monkeypatch):
    import subprocess
    monkeypatch.setenv("APPDATA", str(tmp_path / "App Data"))
    link = sendto.install()
    assert link.is_file()
    script = "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:CFP_LNK); $s.TargetPath; $s.Arguments"
    out = subprocess.run(sendto.powershell_args(script), env=dict(__import__("os").environ, CFP_LNK=str(link)),
                         capture_output=True, text=True, timeout=60).stdout.split("\n")
    target, args, _icon = sendto.launch_command()
    assert out[0].strip().lower() == target.lower() and out[1].strip() == args
    sendto.uninstall()
    assert not link.exists()
