"""Pembuat data uji: gambar, audio, font, file plugin palsu (PiPL asli), project .aep."""

from __future__ import annotations

import math
import struct
import wave
import zlib
from pathlib import Path
from typing import List, Sequence, Tuple

DATA = Path(__file__).parent / "data"


def make_png(path: Path, color=(255, 0, 0), w: int = 8, h: int = 6) -> Path:
    raw = b"".join(b"\x00" + bytes(color) * w for _ in range(h))

    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return path


def make_wav(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(b"\x00\x00" * 4800)
    return path


def make_ttf(path: Path, family: str, style: str, ps_name: str) -> Path:
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", "A"])
    fb.setupCharacterMap({0x41: "A"})
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((0, 500))
    pen.lineTo((500, 500))
    pen.closePath()
    glyph = pen.glyph()
    fb.setupGlyf({".notdef": glyph, "A": glyph})
    fb.setupHorizontalMetrics({".notdef": (500, 0), "A": (500, 0)})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": family, "styleName": style, "psName": ps_name})
    fb.setupOS2()
    fb.setupPost()
    path.parent.mkdir(parents=True, exist_ok=True)
    fb.save(str(path))
    return path


# ------------------------------------------------------------- PiPL / PE

def _u32(v: int, win: bool) -> bytes:
    return struct.pack("<I" if win else ">I", v)


def pipl(props: Sequence[Tuple[str, object]], win: bool = True) -> bytes:
    """Port dari pipl::build_pipl (crate Rust after-effects): byte PiPL asli."""
    cc = (lambda s: s[::-1]) if win else (lambda s: s)
    out = b"\x01\x00" if win else b""
    out += _u32(0, win) + _u32(len(props), win)
    for key, val in props:
        out += cc(b"8BIM") + cc(key.encode()) + _u32(0, win)
        if isinstance(val, str):
            data = bytes([len(val)]) + val.encode()
            if win:
                data += b"\0" * ((4 - len(data) % 4) % 4)
        else:
            data = val  # type: ignore[assignment]
        out += _u32(len(data), win) + data
        if not win:
            out += b"\0" * ((4 - len(data) % 4) % 4)
    return out


def effect_pipl(name: str, category: str, match_name: str, win: bool = True) -> bytes:
    return pipl([("kind", b"TKFe" if win else b"eFKT"), ("name", name), ("catg", category),
                 ("eVER", _u32(0x80001, win)), ("eMNA", match_name)], win)


def make_pe(rsrc: bytes, text: bytes = b"code", plus: bool = True) -> bytes:
    def align(x: int) -> int:
        return int(math.ceil(max(x, 1) / 0x200) * 0x200)

    h = b"MZ" + b"\0" * 0x3A + struct.pack("<I", 0x80) + b"\0" * 0x40 + b"PE\0\0"
    opt_size = 0xF0 if plus else 0xE0
    h += struct.pack("<HHIIIHH", 0x8664 if plus else 0x14C, 2, 0, 0, 0, opt_size, 0x2022)
    dd = 112 if plus else 96
    opt = struct.pack("<H", 0x20B if plus else 0x10B)
    opt += b"\0" * (dd - 4 - len(opt)) + struct.pack("<I", 16)
    for i in range(16):
        opt += struct.pack("<II", 0x3000, len(rsrc)) if i == 2 else b"\0" * 8
    assert len(opt) == opt_size
    h += opt
    text_raw, text_size = 0x400, align(len(text))
    rsrc_raw, rsrc_size = text_raw + text_size, align(len(rsrc))

    def sect(name: bytes, vsize: int, va: int, size: int, ptr: int) -> bytes:
        return (name + b"\0" * 8)[:8] + struct.pack("<IIII", vsize, va, size, ptr) + b"\0" * 16

    h += sect(b".text", len(text), 0x1000, text_size, text_raw)
    h += sect(b".rsrc", len(rsrc), 0x3000, rsrc_size, rsrc_raw)
    h += b"\0" * (text_raw - len(h))
    h += text + b"\0" * (text_size - len(text))
    h += rsrc + b"\0" * (rsrc_size - len(rsrc))
    return h


def make_aex(path: Path, effects: Sequence[Tuple[str, str, str]], packed_text: bytes = b"") -> Path:
    """File .aex palsu. effects: (nama, kategori, match name)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if packed_text:
        path.write_bytes(make_pe(b"\0\0junk-no-pipl", packed_text))
    else:
        path.write_bytes(make_pe(b"\0\0rsrc-dir" + b"".join(effect_pipl(n, c, m) for n, c, m in effects)))
    return path


def make_mac_plugin(path: Path, effects: Sequence[Tuple[str, str, str]]) -> Path:
    res = path / "Contents" / "Resources"
    res.mkdir(parents=True, exist_ok=True)
    (res / (path.stem + ".rsrc")).write_bytes(
        b"rsrcHDR" + b"".join(effect_pipl(n, c, m, win=False) for n, c, m in effects))
    mac = path / "Contents" / "MacOS"
    mac.mkdir(parents=True, exist_ok=True)
    (mac / path.stem).write_bytes(b"\xcf\xfa\xed\xfe binary")
    return path


# ------------------------------------------------------------- project

def make_project(root: Path) -> Path:
    """Project .aep buatan py_aep: Main (logo, logo lain, sequence, teks) dan
    comp Template yang tidak dipakai (musik + teks)."""
    import py_aep
    from py_aep import ImportOptions

    src = root / "src"
    make_png(src / "Logos" / "logo.png")
    make_png(src / "Other" / "logo.png", (0, 0, 255))
    make_wav(src / "Audio" / "music.wav")
    for i in range(1, 6):
        make_png(src / "Render" / ("shot_%04d.png" % i), (0, 40 * i, 0))
    make_png(src / "Gone" / "missing.png")

    app = py_aep.new("25.0x50")
    p = app.project
    folder = p.root_folder
    main = folder.add_comp("Main", 1920, 1080, 1.0, 5.0, 25.0)
    pre = folder.add_comp("Precomp Logo", 1920, 1080, 1.0, 5.0, 25.0)
    template = folder.add_comp("Template Tak Dipakai", 1920, 1080, 1.0, 5.0, 25.0)
    logo = p.import_file(ImportOptions(str(src / "Logos" / "logo.png")))
    logo2 = p.import_file(ImportOptions(str(src / "Other" / "logo.png")))
    music = p.import_file(ImportOptions(str(src / "Audio" / "music.wav")))
    seq_opt = ImportOptions(str(src / "Render" / "shot_0001.png"))
    seq_opt.sequence = True
    seq = p.import_file(seq_opt)
    gone = p.import_file(ImportOptions(str(src / "Gone" / "missing.png")))
    pre.add(logo)
    main.add(pre)
    main.add(logo2)
    main.add(seq)
    main.add(gone)
    main.add_text("Judul")
    template.add(music)
    out = root / "proj" / "Proyek Saya.aep"
    out.parent.mkdir(parents=True, exist_ok=True)
    p.save(str(out))
    (src / "Gone" / "missing.png").unlink()   # footage hilang
    return out


#: (match name asli, pengganti dengan panjang sama) -> efek "pihak ketiga"
FX_SWAPS = [
    (b"ADBE Color Control", b"PEDG Deep Glow Ctl"),
    (b"ADBE Slider Control", b"BCC Directional Blr"),
    (b"ADBE Point Control", b"VNDA A_kaca Effect"),
]


def make_fx_project(root: Path, swaps: Sequence[Tuple[bytes, bytes]] = FX_SWAPS) -> Path:
    """Sample .aep asli (After Effects) yang beberapa efeknya diganti jadi
    efek pihak ketiga dengan mengganti match name-nya."""
    data = (DATA / "Property-01.aep").read_bytes()
    for old, new in swaps:
        assert len(old) == len(new)
        data = data.replace(old, new)
    out = root / "fx" / "Efek.aep"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return out


def make_plugin_tree(root: Path) -> Path:
    """Folder MediaCore palsu ala Boris: banyak file efek dalam satu folder."""
    mc = root / "MediaCore"
    make_aex(mc / "Deep Glow.aex", [("Deep Glow", "Plugin Everything", "PEDG Deep Glow Ctl")])
    (mc / "Deep Glow").mkdir(parents=True, exist_ok=True)
    (mc / "Deep Glow" / "presets.dat").write_bytes(b"P")
    (mc / "random_other_vendor.dll").write_bytes(b"X")
    make_aex(mc / "BorisFX" / "Continuum" / "BCC_Blur.aex",
             [("BCC Gaussian Blur", "BCC Blur", "BCC Gaussian Blur"),
              ("BCC Directional Blur", "BCC Blur", "BCC Directional Blr")])
    make_aex(mc / "BorisFX" / "Continuum" / "BCC_Lens.aex", [("BCC Lens Flare", "BCC Light", "BCC Lens Flare")])
    (mc / "BorisFX" / "Continuum" / "bcc_core.dll").write_bytes(b"DLL")
    (mc / "BorisFX" / "Continuum" / "Resources").mkdir(parents=True, exist_ok=True)
    (mc / "BorisFX" / "Continuum" / "Resources" / "huge.dat").write_bytes(b"H" * 4000)
    make_aex(mc / "(Disabled)" / "Kaca.aex", [("A_kaca", "Vendor A", "VNDA A_kaca Effect")])
    make_aex(mc / "VendorA" / "Kaca.aex", [], packed_text=b"stub\x12VNDA A_kaca Effectstub")
    make_aex(mc / "VendorA" / "Unused.aex", [("Tidak Dipakai", "Vendor A", "VNDA Unused")])
    return mc


def env_for(root: Path, plugin_roots=None, font_dirs: Sequence[Path] = ()):
    from collect_files_plus.collector import Environment
    return Environment(plugin_roots=list(plugin_roots or []), plugin_logs=[], ae_installs=[],
                       font_dirs=list(font_dirs), font_cache=root / "font-cache.json",
                       adobe_font_dirs=[], preset_dirs=[], preset_effects_xml=[])


def files_under(folder: Path) -> List[str]:
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())
