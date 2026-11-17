"""Update otomatis dari GitHub Releases."""

import hashlib
import io
import json
import subprocess
import sys
import threading
import urllib.error
import zipfile
from pathlib import Path

import pytest

from collect_files_plus import __version__, updater


class FakeResp(io.BytesIO):
    def __init__(self, data: bytes, headers=None):
        super().__init__(data)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def release_json(tag="v9.9.0", digest=None):
    asset_win = {"name": "CollectFilesPlus-%s-windows-x64.zip" % tag, "size": 123,
                 "browser_download_url": "https://example.invalid/win.zip"}
    if digest:
        asset_win["digest"] = "sha256:" + digest
    return {"tag_name": tag, "html_url": "https://github.com/%s/releases/tag/%s" % (updater.REPO, tag),
            "body": "catatan rilis",
            "assets": [{"name": "CollectFilesPlus-%s-macos-arm64.zip" % tag, "size": 1,
                        "browser_download_url": "https://example.invalid/mac.zip"}, asset_win]}


def test_versions():
    assert updater.parse_version("v1.2.10") == (1, 2, 10)
    assert updater.is_newer("1.0.1", "1.0.0") and updater.is_newer("v1.1", "1.0.9")
    assert not updater.is_newer("1.0.0", "1.0.0") and not updater.is_newer("1.0", "1.0.0")
    assert not updater.is_newer("0.9.9", "1.0.0") and not updater.is_newer("rilis-aneh", "1.0.0")
    assert updater.is_newer("1.0.10", "1.0.9")


def test_check_latest(monkeypatch):
    calls = []

    def fake_open(url, timeout):
        calls.append(url)
        return FakeResp(json.dumps(release_json(digest="ab" * 32)).encode())

    monkeypatch.setattr(updater, "_open", fake_open)
    monkeypatch.setattr(updater, "platform_suffix", lambda: "-windows-x64.zip")
    info = updater.check_latest()
    assert calls == [updater.API_LATEST]
    assert info.version == "9.9.0" and info.newer and info.notes == "catatan rilis"
    assert info.asset_url == "https://example.invalid/win.zip" and info.sha256 == "ab" * 32
    monkeypatch.setattr(updater, "platform_suffix", lambda: "-macos-arm64.zip")
    assert updater.check_latest().asset_url.endswith("mac.zip")
    monkeypatch.setattr(updater, "platform_suffix", lambda: None)
    assert updater.check_latest().asset_url == ""


def test_check_latest_no_release_and_errors(monkeypatch):
    def not_found(url, timeout):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr(updater, "_open", not_found)
    assert updater.check_latest() is None

    def limited(url, timeout):
        raise urllib.error.HTTPError(url, 403, "rate limit", {}, None)

    monkeypatch.setattr(updater, "_open", limited)
    with pytest.raises(urllib.error.HTTPError):
        updater.check_latest()


def test_download_checksum_and_cancel(tmp_path, monkeypatch):
    data = b"isi zip" * 20000
    good = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(updater, "_open", lambda url, timeout: FakeResp(data, {"Content-Length": str(len(data))}))
    info = updater.UpdateInfo("9.9.0", "v9.9.0", "page", asset_name="u.zip", asset_url="x", sha256=good)
    seen = []
    path = updater.download(info, tmp_path / "a", progress=lambda d, t: seen.append((d, t)))
    assert path.read_bytes() == data and seen[-1] == (len(data), len(data))

    info.sha256 = "00" * 32
    with pytest.raises(OSError, match="checksum"):
        updater.download(info, tmp_path / "b")
    assert not (tmp_path / "b" / "u.zip").exists()

    info.sha256 = ""
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(updater.UpdateCancelled):
        updater.download(info, tmp_path / "c", cancel=cancel)
    info.asset_url = ""
    with pytest.raises(OSError):
        updater.download(info, tmp_path / "d")


def _zip(path: Path, files: dict) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return path


def test_extract_app(tmp_path):
    z = _zip(tmp_path / "u.zip", {"CollectFilesPlus/CollectFilesPlus.exe": "exe",
                                  "CollectFilesPlus/_internal/a.dll": "dll",
                                  "CollectFilesPlus/jsx/CollectFilesPlus.jsx": "jsx"})
    folder = updater.extract_app(z, tmp_path / "out")
    assert folder == (tmp_path / "out" / "CollectFilesPlus").resolve()
    assert (folder / "_internal" / "a.dll").read_text() == "dll"

    evil = _zip(tmp_path / "evil.zip", {"../../keluar.txt": "x", "CollectFilesPlus/CollectFilesPlus.exe": "e"})
    with pytest.raises(OSError):
        updater.extract_app(evil, tmp_path / "out2")
    assert not (tmp_path / "keluar.txt").exists()
    with pytest.raises(OSError, match="CollectFilesPlus.exe"):
        updater.extract_app(_zip(tmp_path / "kosong.zip", {"x/readme.txt": "x"}), tmp_path / "out3")


def test_apply_command_and_result(tmp_path, monkeypatch):
    args, env = updater.apply_command(tmp_path / "baru", tmp_path, "9.9.0", app=tmp_path / "App", pid=1234,
                                      restart=False)
    assert args[0] == "powershell.exe" and args[-2] == "-File"
    script = Path(args[-1]).read_text(encoding="utf-8-sig")
    assert "/MIR" in script and "Wait-Process" in script and "mengembalikan versi lama" in script
    assert env["CFP_APP"] == str(tmp_path / "App") and env["CFP_PID"] == "1234" and env["CFP_NO_RESTART"] == "1"
    assert env["CFP_VERSION"] == "9.9.0" and updater.RESULT_ENV not in env

    monkeypatch.setenv(updater.RESULT_ENV, "ok:9.9.0")
    assert updater.take_update_result() == (True, "9.9.0")
    assert updater.take_update_result() is None          # hanya sekali
    monkeypatch.setenv(updater.RESULT_ENV, "failed:C:\\temp\\log.txt")
    assert updater.take_update_result() == (False, "C:\\temp\\log.txt")


def test_cannot_self_update_from_source():
    assert updater.can_self_update() is False


def _fake_install(root: Path):
    app = root / "App"
    (app / "_internal").mkdir(parents=True)
    (app / "CollectFilesPlus.exe").write_text("lama")
    (app / "_internal" / "shared.dll").write_text("lama")
    (app / "_internal" / "hanya_lama.dll").write_text("lama")
    (app / "catatan saya.txt").write_text("milik pemakai")
    return app


def _finished_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


@pytest.mark.skipif(sys.platform != "win32", reason="skrip pemasang khusus Windows")
def test_apply_script_real_windows(tmp_path):
    app = _fake_install(tmp_path)
    tmp = tmp_path / "upd tmp"
    new = tmp / "baru" / "CollectFilesPlus"
    (new / "_internal").mkdir(parents=True)
    (new / "jsx").mkdir()
    (new / "CollectFilesPlus.exe").write_text("baru")
    (new / "_internal" / "shared.dll").write_text("baru")
    (new / "_internal" / "hanya_baru.dll").write_text("baru")
    (new / "jsx" / "CollectFilesPlus.jsx").write_text("baru")
    args, env = updater.apply_command(new, tmp, "9.9.0", app=app, pid=_finished_pid(), restart=False)
    subprocess.run(args, env=env, timeout=180, check=False)
    log = (tmp / "update-log.txt").read_text(errors="replace")
    assert "selesai" in log, log
    assert (app / "CollectFilesPlus.exe").read_text() == "baru"
    assert (app / "_internal" / "shared.dll").read_text() == "baru"
    assert (app / "_internal" / "hanya_baru.dll").exists() and not (app / "_internal" / "hanya_lama.dll").exists()
    assert (app / "jsx" / "CollectFilesPlus.jsx").read_text() == "baru"
    assert (app / "catatan saya.txt").read_text() == "milik pemakai"
    assert not (tmp / "backup").exists() and not new.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="skrip pemasang khusus Windows")
def test_apply_script_restores_on_failure(tmp_path):
    app = _fake_install(tmp_path)
    tmp = tmp_path / "upd"
    new = tmp / "baru" / "CollectFilesPlus"           # rusak: tidak ada folder _internal
    new.mkdir(parents=True)
    (new / "CollectFilesPlus.exe").write_text("baru")
    args, env = updater.apply_command(new, tmp, "9.9.0", app=app, pid=_finished_pid(), restart=False)
    subprocess.run(args, env=env, timeout=180, check=False)
    log = (tmp / "update-log.txt").read_text(errors="replace")
    assert "mengembalikan versi lama" in log, log
    assert (app / "CollectFilesPlus.exe").read_text() == "lama"
    assert (app / "_internal" / "hanya_lama.dll").read_text() == "lama"
