from pathlib import Path

from collect_files_plus import cli
from helpers import make_project


def test_cli_list_analyze_collect(tmp_path: Path, capsys, monkeypatch):
    from collect_files_plus import collector
    from helpers import env_for

    proj = make_project(tmp_path)
    env = env_for(tmp_path)
    monkeypatch.setattr(collector, "Environment", lambda: env)

    assert cli.main(["list-comps", str(proj)]) == 0
    out = capsys.readouterr().out
    assert "Precomp Logo" in out and "precomp di 1 comp" in out

    assert cli.main(["analyze", str(proj), "--comp", "Main"]) == 0
    out = capsys.readouterr().out
    assert "Comp dibaca  : Main" in out and "=== FOOTAGE ===" in out

    dest = tmp_path / "hasil"
    assert cli.main(["collect", str(proj), "-o", str(dest), "--comp", "Main", "--reduce"]) == 0
    assert (dest / "Proyek Saya_Collected" / "Proyek Saya.aep").is_file()


def test_cli_unknown_comp(tmp_path: Path):
    import pytest
    proj = make_project(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(["analyze", str(proj), "--comp", "Tidak Ada"])


def test_cli_collect_many(tmp_path: Path, capsys, monkeypatch):
    from collect_files_plus import collector
    from helpers import env_for

    env = env_for(tmp_path)
    monkeypatch.setattr(collector, "Environment", lambda: env)
    p1 = make_project(tmp_path / "A")
    make_project(tmp_path / "B")
    bad = tmp_path / "C" / "rusak.aep"
    bad.parent.mkdir()
    bad.write_bytes(b"bukan project")
    dest = tmp_path / "hasil"
    # file + folder + file rusak sekaligus
    rc = cli.main(["collect", str(p1), str(tmp_path / "B"), str(bad), "-o", str(dest), "--all"])
    assert rc == 1                                # ada yang gagal
    out = capsys.readouterr().out
    assert "Collect 3 project" in out and "GAGAL" in out and "Ringkasan:" in out
    assert "0 OK, 2 ada catatan, 1 gagal (dari 3 project)" in out
    dirs = sorted(d.name for d in dest.iterdir() if d.is_dir())
    assert dirs == ["Proyek Saya_Collected", "Proyek Saya_Collected (2)"]

    rc = cli.main(["collect", str(tmp_path / "A"), "-o", str(tmp_path / "hasil2")])
    assert rc == 0                                # folder saja, semua berhasil
