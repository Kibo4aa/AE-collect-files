"""Bahasa: terjemahan lengkap, format sama, dan mode English tidak berisi kata Indonesia."""

import ast
import re
import sys
from pathlib import Path

import pytest

from collect_files_plus import i18n
from collect_files_plus.en import EN
from helpers import env_for, files_under, make_fx_project, make_plugin_tree, make_project, make_ttf

SRC = Path(__file__).resolve().parent.parent / "src" / "collect_files_plus"

# kata yang jelas bahasa Indonesia (bukan kata English)
INDO = re.compile(r"\b(yang|tidak|dengan|untuk|dari|sudah|belum|dipakai|ketemu|dicopy|hilang|gagal|pilih|tujuan|"
                  r"laporan|efek|semua|bawaan|catatan|perkiraan|centang|lewat|komputer|kalau|lalu|buka|pakai|"
                  r"ikut|hanya|bisa|dulu|selesai|tanggal|hasil|asal|dibaca|terbaca|pemakaian|jenis|dimatikan|"
                  r"sendiri|lainnya|isi|menunggu|diproses|ringkasan|dibatalkan|aktifkan|tambah|hapus|kosongkan|"
                  r"analisa|batal|lokasi|ukuran|keterangan|ditemukan|daftar|bahasa)\b", re.IGNORECASE)
DATA_NAMES = ["Template Tak Dipakai", "Proyek Saya", "rusak.aep", "Efek.aep", "Efek_", "Bahasa / Language",
              "Bahasa Indonesia"]


def _indonesian_words(text: str):
    for name in DATA_NAMES:
        text = text.replace(name, "")
    return sorted({m.group(0).lower() for m in INDO.finditer(text)})


def _keys_in_source():
    keys = {}
    for f in sorted(SRC.glob("*.py")):
        if f.name in ("i18n.py", "en.py"):
            continue
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("_", "N_")
                    and node.args and isinstance(node.args[0], ast.Constant)):
                keys.setdefault(node.args[0].value, f.name)
    return keys


def test_every_text_has_english():
    keys = _keys_in_source()
    assert len(keys) > 250
    missing = {k: f for k, f in keys.items() if k not in EN}
    assert not missing, missing
    unused = [k for k in EN if k not in keys]
    assert not unused, unused


def test_format_placeholders_match():
    spec = re.compile(r"%[-0-9.]*[sdf]")
    for k, v in EN.items():
        assert spec.findall(k) == spec.findall(v), (k, v)
        assert k.count("\n") == v.count("\n"), (k, v)
        assert k.startswith(" ") == v.startswith(" ") and k.endswith(" ") == v.endswith(" "), (k, v)


def test_language_choice(monkeypatch):
    monkeypatch.setenv(i18n.ENV_VAR, "en")
    assert i18n.system_language() == "en"
    monkeypatch.setenv(i18n.ENV_VAR, "id")
    assert i18n.system_language() == "id"
    assert i18n.set_language("xx") == "id"
    i18n.set_language("en")
    assert i18n._("Batal") == "Cancel" and i18n._("teks tanpa terjemahan") == "teks tanpa terjemahan"


def test_english_report_csv_and_batch(tmp_path: Path):
    from collect_files_plus.batch import collect_many
    from collect_files_plus.collector import Options
    from collect_files_plus.plugins import PluginRoot

    i18n.set_language("en")
    p1 = make_project(tmp_path / "A")
    mc = make_plugin_tree(tmp_path)
    fx = make_fx_project(tmp_path)
    fonts = tmp_path / "fonts"
    make_ttf(fonts / "Myriad.ttf", "Myriad Pro", "Regular", "MyriadPro-Regular")
    bad = tmp_path / "C" / "rusak.aep"
    bad.parent.mkdir()
    bad.write_bytes(b"not a project")
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)], font_dirs=[fonts])
    run = collect_many([p1, fx, bad], Options(dest_dir=tmp_path / "out", reduce_project=True), env=env)

    assert run.headline() == "0 OK, 2 with notes, 1 failed (of 3 projects)"
    assert run.items[0].status_text == "OK, 1 missing footage"
    assert run.items[1].status_text == "OK, 1 font(s) not found"
    assert run.items[1].scope == "active comp: Comp 01"
    summary = run.summary.read_text(encoding="utf-8")
    assert "batch summary" in summary and "[FAILED]" in summary
    assert _indonesian_words(summary) == []

    proj_dir = tmp_path / "out" / "Proyek Saya_Collected"
    report = (proj_dir / "Proyek Saya_report.txt").read_text(encoding="utf-8")
    assert "=== HOW TO USE ON ANOTHER COMPUTER ===" in report and "Comps read   :" in report
    assert _indonesian_words(report) == []
    fx_dir = tmp_path / "out" / "Efek_Collected"
    fx_report = (fx_dir / "Efek_report.txt").read_text(encoding="utf-8")
    assert "[OK] BCC Directional Blur  [match name: BCC Directional Blr]" in fx_report
    assert "this file also contains 1 other unused effect(s)" in fx_report
    assert _indonesian_words(fx_report) == []
    csv = (fx_dir / "Efek_effect_list.csv").read_bytes()[2:].decode("utf-16-le")
    assert csv.startswith('"Comp"\t"Layer"\t"Effect name on layer"')
    assert _indonesian_words(csv) == []
    assert "(Plugins)/MediaCore/BorisFX/Continuum/BCC_Blur.aex" in files_under(fx_dir)


def test_english_cli(tmp_path: Path, capsys, monkeypatch):
    from collect_files_plus import cli, collector

    env = env_for(tmp_path)
    monkeypatch.setattr(collector, "Environment", lambda: env)
    proj = make_project(tmp_path)
    assert cli.main(["list-comps", str(proj), "--lang", "en"]) == 0
    assert "precomp in 1 comp(s)" in capsys.readouterr().out
    assert cli.main(["--lang=en", "analyze", str(proj)]) == 0
    out = capsys.readouterr().out
    assert "Comps read   :" in out and _indonesian_words(out) == []
    assert cli.main(["collect", str(proj), str(tmp_path / "proj"), "-o", str(tmp_path / "o"), "--lang", "en"]) == 0
    out = capsys.readouterr().out
    assert "Collecting 1 project(s)" in out and "Summary:" in out and _indonesian_words(out) == []
    with pytest.raises(SystemExit):
        cli.main(["--lang", "en", "--help"])
    assert "output language" in capsys.readouterr().out
    assert cli.main(["--lang", "xx", "analyze", str(proj)]) == 2
