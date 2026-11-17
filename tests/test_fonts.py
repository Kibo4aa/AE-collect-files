from pathlib import Path

from collect_files_plus.fonts import FontIndex
from helpers import make_ttf


def test_lookup_by_postscript_name_and_cache(tmp_path: Path):
    fonts = tmp_path / "fonts"
    make_ttf(fonts / "Judul-Bold.ttf", "Judul", "Bold", "Judul-Bold")
    make_ttf(fonts / "sub" / "Isi.ttf", "Isi", "Regular", "Isi-Regular")
    cache = tmp_path / "cache.json"
    idx = FontIndex([fonts], cache).build()
    assert idx.lookup("judul-bold").path.name == "Judul-Bold.ttf"
    assert idx.lookup("Isi-Regular").family == "Isi"
    assert idx.lookup("Tidak-Ada") is None
    assert idx.files_scanned == 2
    again = FontIndex([fonts], cache).build()
    assert again.files_scanned == 0          # dari cache
    assert again.lookup("Judul-Bold") is not None


def test_broken_font_is_ignored(tmp_path: Path):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    (fonts / "rusak.ttf").write_bytes(b"bukan font")
    idx = FontIndex([fonts], use_cache=False).build()
    assert idx.by_ps == {}
