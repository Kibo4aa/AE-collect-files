import json
from pathlib import Path

import pytest

from collect_files_plus.collector import Options, analyze, collect
from collect_files_plus.plugins import PluginRoot
from collect_files_plus.project import AepProject
from helpers import DATA, env_for, files_under, make_fx_project, make_plugin_tree, make_project, make_ttf


def _comp_ids(aep, *names):
    return [c.id for c in aep.comps if c.name in names]


def test_footage_fonts_relink_reduce(tmp_path: Path):
    proj = make_project(tmp_path)
    fonts = tmp_path / "fonts"
    make_ttf(fonts / "Myriad.ttf", "Myriad Pro", "Regular", "MyriadPro-Regular")
    aep = AepProject(proj)
    opt = Options(dest_dir=tmp_path / "out", comp_ids=_comp_ids(aep, "Main"), reduce_project=True)
    an = analyze(aep, opt, env_for(tmp_path, font_dirs=[fonts]))
    res = collect(an)

    assert res.saved_ok, res.validation_error
    assert res.dest_root == tmp_path / "out" / "Proyek Saya_Collected"
    assert res.reduced == 2           # comp template + music.wav
    files = files_under(res.dest_root)
    for f in ["(Backup)/Proyek Saya.aep", "(Fonts)/Myriad.ttf", "(Footage)/Logos/logo.png",
              "(Footage)/Other/logo.png", "(Footage)/Render/shot_0001.png", "(Footage)/Render/shot_0005.png",
              "Proyek Saya.aep", "Proyek Saya_report.txt"]:
        assert f in files, f
    assert not any("music.wav" in f for f in files)

    out = AepProject(res.project_out)
    assert {c.name for c in out.comps} == {"Main", "Precomp Logo"}
    paths = {Path(r.path).name: r.path for r in out.footage()}
    assert paths["logo.png"].startswith(str(res.dest_root))
    assert paths["shot_0001.png"] == str(res.dest_root / "(Footage)" / "Render" / "shot_0001.png")
    assert paths["missing.png"] == str(tmp_path / "src" / "Gone" / "missing.png")  # hilang: tidak diubah

    # hitungan path relatif terisi untuk lokasi project baru
    from py_aep.binary.utils import find_by_list_type, find_by_type
    for ref in out.footage():
        als2 = find_by_list_type(chunks=ref.source._pin.chunks, list_type="Als2")
        data = json.loads(find_by_type(chunks=als2.chunks, chunk_type="alas").value)
        assert data["ascendcount_base"] >= 0 and data["ascendcount_target"] >= 0

    report = res.report.read_text(encoding="utf-8")
    assert "[HILANG]" in report and "missing.png" in report
    assert "Reduce Project: 2 item" in report
    assert "[OK]      MyriadPro-Regular" in report
    # project asli tidak berubah
    orig = AepProject(proj)
    assert len(orig.comps) == 3
    assert all(not r.path.startswith(str(tmp_path / "out")) for r in orig.footage())


def test_all_comps_collects_everything(tmp_path: Path):
    aep = AepProject(make_project(tmp_path))
    an = analyze(aep, Options(dest_dir=tmp_path / "out"), env_for(tmp_path))
    res = collect(an)
    assert res.saved_ok
    assert "(Footage)/Audio/music.wav" in files_under(res.dest_root)
    assert len(AepProject(res.project_out).comps) == 3


def test_second_run_uses_new_folder(tmp_path: Path):
    proj = make_project(tmp_path)
    for expected in ("Proyek Saya_Collected", "Proyek Saya_Collected (2)"):
        an = analyze(AepProject(proj), Options(dest_dir=tmp_path / "out"), env_for(tmp_path))
        assert collect(an).dest_root.name == expected


def test_plugins_only_used_files(tmp_path: Path):
    mc = make_plugin_tree(tmp_path)
    aep = AepProject(make_fx_project(tmp_path))
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)])
    an = analyze(aep, Options(dest_dir=tmp_path / "out"), env)
    labels = sorted(cd.label for cd in an.candidates)
    assert labels == ["MediaCore/BorisFX/Continuum/BCC_Blur.aex", "MediaCore/Deep Glow.aex",
                      "MediaCore/VendorA/Kaca.aex"]
    blur = [cd for cd in an.candidates if cd.label.endswith("BCC_Blur.aex")][0]
    assert blur.others == 1 and blur.selected
    res = collect(an)
    plugins = [f for f in files_under(res.dest_root) if f.startswith("(Plugins)/")]
    assert plugins == ["(Plugins)/MediaCore/BorisFX/Continuum/BCC_Blur.aex",
                       "(Plugins)/MediaCore/Deep Glow.aex",
                       "(Plugins)/MediaCore/VendorA/Kaca.aex"]
    # tidak ada footage yang berubah -> .aep asli dicopy apa adanya, tanpa cadangan
    assert res.backup is None
    assert res.project_out.read_bytes() == aep.path.read_bytes()
    report = res.report.read_text(encoding="utf-8")
    assert "[OK] BCC Directional Blur  [match name: BCC Directional Blr]" in report
    assert "nama di layer : Slider Control" in report
    assert "[OK, CEK MANUAL] A_kaca Effect" in report or "[OK, CEK MANUAL]" in report
    assert "file ini juga berisi 1 efek lain" in report
    assert res.csv.read_bytes()[:2] == b"\xff\xfe"


def test_support_files_and_unchecked(tmp_path: Path):
    mc = make_plugin_tree(tmp_path)
    aep = AepProject(make_fx_project(tmp_path))
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)])
    an = analyze(aep, Options(dest_dir=tmp_path / "out", support_files=True), env)
    for cd in an.candidates:
        if cd.label.endswith("Kaca.aex"):
            cd.selected = False
    res = collect(an)
    files = files_under(res.dest_root)
    assert "(Plugins)/MediaCore/BorisFX/Continuum/bcc_core.dll" in files
    assert "(Plugins)/MediaCore/Deep Glow/presets.dat" in files
    for bad in ["BCC_Lens.aex", "huge.dat", "random_other_vendor.dll", "Unused.aex", "Kaca.aex"]:
        assert not any(f.endswith(bad) for f in files), bad
    assert "[TIDAK DICOPY]" in res.report.read_text(encoding="utf-8")


def test_disabled_effects_skipped(tmp_path: Path):
    import py_aep
    app = py_aep.parse(str(DATA / "Layer-01.aep"))
    fill = None
    for comp in app.project.compositions:
        for layer in comp.layers:
            for e in layer.effects:
                if e.match_name == "ADBE Fill":
                    fill = e
    assert fill is not None
    fill.enabled = False
    src = tmp_path / "off.aep"
    app.project.save(str(src))
    aep = AepProject(src)
    an = analyze(aep, Options(dest_dir=tmp_path / "o1"), env_for(tmp_path))
    assert [e.match_name for e in an.disabled_only] == ["ADBE Fill"]
    assert all(e.match_name != "ADBE Fill" for e in an.effects)
    an2 = analyze(AepProject(src), Options(dest_dir=tmp_path / "o2", skip_disabled=False), env_for(tmp_path))
    assert any(e.match_name == "ADBE Fill" for e in an2.effects)


@pytest.mark.parametrize("name", ["Item-01.aep", "Layer-01.aep", "Property-01.aep"])
def test_real_files_end_to_end(tmp_path: Path, name):
    an = analyze(AepProject(DATA / name), Options(dest_dir=tmp_path), env_for(tmp_path))
    res = collect(an)
    assert res.saved_ok and res.report.is_file()
