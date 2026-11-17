from pathlib import Path

from collect_files_plus.project import AepProject
from helpers import DATA, make_fx_project, make_project


def test_real_after_effects_files_parse():
    for name in ("Item-01.aep", "Layer-01.aep", "Property-01.aep"):
        aep = AepProject(DATA / name)
        assert aep.comps


def test_effects_with_renamed_instances():
    aep = AepProject(DATA / "Property-01.aep")
    used, off = aep.effects(aep.comps, skip_disabled=True)
    by_mn = {g.match_name: g for g in used}
    assert by_mn["ADBE Angle Control"].names == ["Custom Angle Control Label"]
    assert by_mn["ADBE Angle Control"].uses[0].layer_index == 1
    assert off == []


def test_fake_third_party_effects(tmp_path: Path):
    aep = AepProject(make_fx_project(tmp_path))
    used, _off = aep.effects(aep.comps, skip_disabled=True)
    mns = {g.match_name for g in used}
    assert {"PEDG Deep Glow Ctl", "BCC Directional Blr", "VNDA A_kaca Effect"} <= mns


def test_scope_footage_and_fonts(tmp_path: Path):
    aep = AepProject(make_project(tmp_path))
    names = {c.name for c in aep.comps}
    assert names == {"Main", "Precomp Logo", "Template Tak Dipakai"}
    main = [c for c in aep.comps if c.name == "Main"][0]
    scope = aep.expand([main])
    assert {c.name for c in scope} == {"Main", "Precomp Logo"}
    assert aep.precomp_users()[[c for c in aep.comps if c.name == "Precomp Logo"][0].id] == 1
    all_refs = aep.footage()
    used_refs = aep.footage(only_used_by=scope)
    assert len(all_refs) == 5
    assert {Path(r.path).name for r in used_refs} == {"logo.png", "shot_0001.png", "missing.png"}
    seq = [r for r in all_refs if r.is_sequence][0]
    assert Path(seq.path).name == "shot_0001.png"
    assert aep.fonts(scope) == ["MyriadPro-Regular"]
    template = [c for c in aep.comps if c.name == "Template Tak Dipakai"][0]
    assert aep.fonts([template]) == []
