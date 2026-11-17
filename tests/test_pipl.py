from pathlib import Path

from collect_files_plus.pipl import PiPLEntry, parse_pipl, pe_resource_range, read_plugin_pipl, scan_needles
from helpers import effect_pipl, make_mac_plugin, make_pe


def test_parse_windows_and_mac():
    for win in (True, False):
        data = b"xx" + effect_pipl("A_kaca", "Vendor A", "VNDA A_kaca", win) + \
            effect_pipl("a_paya", "Vendor A", "a_paya", win) + b"yy"
        assert parse_pipl(data) == [
            PiPLEntry("VNDA A_kaca", "A_kaca", "Vendor A"),
            PiPLEntry("a_paya", "a_paya", "Vendor A"),
        ]


def test_pe_resource_range_pe32_and_pe32plus(tmp_path: Path):
    for plus in (False, True):
        f = tmp_path / ("p%s.aex" % plus)
        f.write_bytes(make_pe(b"dir" + effect_pipl("Deep Glow", "PE", "PEDG"),
                              text=b"code" + effect_pipl("Fake", "X", "FAKE in text"), plus=plus))
        start, size = pe_resource_range(f)
        assert size > 0
        assert [e.match_name for e in read_plugin_pipl(f)] == ["PEDG"]


def test_not_pe_reads_whole_file(tmp_path: Path):
    f = tmp_path / "x.aex"
    f.write_bytes(b"hello" + effect_pipl("N", "C", "NOTPE Fx"))
    assert pe_resource_range(f) is None
    assert [e.match_name for e in read_plugin_pipl(f)] == ["NOTPE Fx"]


def test_mac_bundle(tmp_path: Path):
    b = make_mac_plugin(tmp_path / "Glow.plugin", [("M Glow", "Vendor M", "VNDM Glow")])
    rsrc = list((b / "Contents" / "Resources").glob("*.rsrc"))
    assert [e.match_name for e in read_plugin_pipl(b, rsrc)] == ["VNDM Glow"]


def test_scan_needles_strength(tmp_path: Path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"zz\x0dPKD Packed FXzz" + b"PLAIN Only" + "WIDE Name".encode("utf-16-le"))
    hits = scan_needles(f, ["PKD Packed FX", "PLAIN Only", "WIDE Name", "None Here"])
    assert hits == {"PKD Packed FX": 2, "PLAIN Only": 1, "WIDE Name": 1}


def test_needle_across_chunk_boundary(tmp_path: Path, monkeypatch):
    import collect_files_plus.pipl as pipl
    monkeypatch.setattr(pipl, "SCAN_CHUNK", 64)
    for off in range(40, 80):
        f = tmp_path / ("b%d.bin" % off)
        f.write_bytes(b"\0" * off + b"\x0dPKD Packed FX" + b"\0" * 10)
        assert scan_needles(f, ["PKD Packed FX"]) == {"PKD Packed FX": 2}, off
