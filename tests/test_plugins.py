from pathlib import Path

from collect_files_plus.plugins import (
    PluginRoot,
    build_plugin_list,
    guess_by_file_name,
    match_effects,
    parse_plugin_logs,
    support_items,
)
from helpers import make_aex, make_plugin_tree


def _plugins(tmp_path: Path, logs=()):
    mc = make_plugin_tree(tmp_path)
    return mc, build_plugin_list([], roots=[PluginRoot(mc, "MediaCore", 1)], log_files=list(logs), ae_installs=[])


def test_skips_parenthesized_folders(tmp_path: Path):
    _mc, plugins = _plugins(tmp_path)
    labels = [p.label for p in plugins]
    assert "MediaCore/(Disabled)/Kaca.aex" not in labels
    assert "MediaCore/BorisFX/Continuum/BCC_Blur.aex" in labels


def test_match_exact_two_effects_in_one_file(tmp_path: Path):
    _mc, plugins = _plugins(tmp_path)
    found = match_effects(plugins, ["BCC Directional Blr", "PEDG Deep Glow Ctl"])
    assert found["BCC Directional Blr"].plugin.label == "MediaCore/BorisFX/Continuum/BCC_Blur.aex"
    assert found["BCC Directional Blr"].how == "pipl"
    assert found["BCC Directional Blr"].effect_name == "BCC Directional Blur"
    assert found["PEDG Deep Glow Ctl"].plugin.label == "MediaCore/Deep Glow.aex"


def test_packed_plugin_found_by_content(tmp_path: Path):
    _mc, plugins = _plugins(tmp_path)
    found = match_effects(plugins, ["VNDA A_kaca Effect"])
    m = found["VNDA A_kaca Effect"]
    assert m.plugin.label == "MediaCore/VendorA/Kaca.aex"
    assert m.how == "isi-file" and m.strict


def test_not_installed_effect_not_found(tmp_path: Path):
    _mc, plugins = _plugins(tmp_path)
    assert "XYZ Missing" not in match_effects(plugins, ["XYZ Missing"])


def test_guess_is_not_strict_and_not_too_loose(tmp_path: Path):
    _mc, plugins = _plugins(tmp_path)
    assert guess_by_file_name(plugins, ["Glow", "XX Glow"]) is None
    g = guess_by_file_name(plugins, ["Deep Glow"])
    assert g is not None and g.how == "nama-file" and not g.strict


def test_support_items_never_include_other_plugins(tmp_path: Path):
    _mc, plugins = _plugins(tmp_path)
    by_label = {p.label: p for p in plugins}
    blur = [p.name for p in support_items(by_label["MediaCore/BorisFX/Continuum/BCC_Blur.aex"])]
    assert blur == ["bcc_core.dll"]
    glow = [p.name for p in support_items(by_label["MediaCore/Deep Glow.aex"])]
    assert glow == ["Deep Glow"]   # folder bernama sama; DLL vendor lain di root tidak ikut


def test_plugin_loading_log(tmp_path: Path):
    log = tmp_path / "Plugin Loading.log"
    other = tmp_path / "Kustom" / "Saber"
    make_aex(other / "Saber.aex", [("Saber", "Video Copilot", "VIDEOCOPILOT Saber")])
    loose = make_aex(tmp_path / "Lain" / "Twitch.aex", [("Twitch", "Video Copilot", "VIDEOCOPILOT Twitch")])
    log.write_text("Loading from root path: %s\r\nLoading %s\r\nLoading %s (cached)\r\nLoading C:\\x\\Player.prm\r\n"
                   % (tmp_path / "Kustom", other / "Saber.aex", loose), encoding="utf-8")
    roots, files = parse_plugin_logs([log])
    assert roots == [str(tmp_path / "Kustom")]
    assert files == [str(other / "Saber.aex"), str(loose)]
    _mc, plugins = _plugins(tmp_path, logs=[log])
    found = match_effects(plugins, ["VIDEOCOPILOT Saber", "VIDEOCOPILOT Twitch"])
    assert found["VIDEOCOPILOT Saber"].plugin.label == "Lainnya/Kustom/Saber/Saber.aex"
    assert found["VIDEOCOPILOT Twitch"].plugin.label == "Lainnya/Lain/Twitch.aex"
