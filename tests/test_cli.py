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
