"""Membaca data PiPL di dalam file plugin After Effects.

Setiap plugin efek After Effects menyimpan "PiPL" (Plug-in Property List):
nama efek, kategori, dan *match name* (nama unik yang juga tersimpan di
.aep). Dengan membaca PiPL kita tahu efek apa saja yang ada di sebuah file
plugin tanpa perlu membuka After Effects.

- Windows (.aex): PiPL ada di resource section file PE, kode 4 huruf disimpan
  terbalik (little-endian), contoh `MIB8ANMe` untuk `8BIM` + `eMNA`.
- macOS (.plugin): PiPL ada di `Contents/Resources/*.rsrc`, big-endian
  (`8BIMeMNA`).

Isi properti teks berupa Pascal string: 1 byte panjang lalu teksnya.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

#: Batas baca resource section / file non-PE.
RSRC_MAX = 256 * 1024 * 1024
#: Ukuran potongan baca untuk pencarian isi file penuh.
SCAN_CHUNK = 8 * 1024 * 1024
SCAN_OVERLAP = 600

# (penanda, kunci, little_endian)
_MARKERS: Tuple[Tuple[bytes, str, bool], ...] = (
    (b"MIB8ANMe", "mn", True),
    (b"8BIMeMNA", "mn", False),
    (b"MIB8eman", "name", True),
    (b"8BIMname", "name", False),
    (b"MIB8gtac", "cat", True),
    (b"8BIMcatg", "cat", False),
)


@dataclass(frozen=True)
class PiPLEntry:
    """Satu efek di dalam file plugin."""

    match_name: str
    name: str
    category: str


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def parse_pipl(data: bytes) -> List[PiPLEntry]:
    """Ambil semua efek (match name + nama + kategori) dari sebuah blok byte."""
    hits: List[Tuple[int, str, bool]] = []
    for marker, key, little in _MARKERS:
        start = 0
        while True:
            k = data.find(marker, start)
            if k == -1:
                break
            hits.append((k, key, little))
            start = k + 1
    hits.sort(key=lambda h: h[0])

    entries: List[PiPLEntry] = []
    cur_name = ""
    cur_cat = ""
    for k, key, little in hits:
        if k + 17 > len(data):
            continue
        length = struct.unpack_from("<I" if little else ">I", data, k + 12)[0]
        plen = data[k + 16]
        if plen < 1 or length < plen + 1 or length > 1024 or k + 17 + plen > len(data):
            continue
        raw = data[k + 17:k + 17 + plen]
        if any(c < 32 or c == 127 for c in raw):
            continue
        text = _decode(raw)
        if key == "name":
            cur_name, cur_cat = text, ""
        elif key == "cat":
            cur_cat = text
        else:
            entries.append(PiPLEntry(text, cur_name, cur_cat))
    return entries


def pe_resource_range(path: Path) -> Optional[Tuple[int, int]]:
    """Posisi & ukuran resource section sebuah file PE (.aex).

    Mengembalikan None kalau bukan file PE, atau (0, 0) kalau file PE itu
    tidak punya resource yang bisa dibaca dari disk (misalnya dikompres).
    """
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
            if len(head) < 64 or head[:2] != b"MZ":
                return None
            pe = struct.unpack_from("<I", head, 60)[0]
            if pe < 64 or pe > 1024 * 1024:
                return None
            if pe + 264 > len(head):
                f.seek(0)
                head = f.read(pe + 4096)
            if len(head) < pe + 24 or head[pe:pe + 4] != b"PE\x00\x00":
                return None
            nsec, = struct.unpack_from("<H", head, pe + 6)
            opt_size, = struct.unpack_from("<H", head, pe + 20)
            opt = pe + 24
            magic, = struct.unpack_from("<H", head, opt)
            dd = opt + (112 if magic == 0x20B else 96)
            if dd + 24 > opt + opt_size:
                return (0, 0)
            if struct.unpack_from("<I", head, dd - 4)[0] < 3:
                return (0, 0)
            rva, = struct.unpack_from("<I", head, dd + 16)
            if not rva:
                return (0, 0)
            sec = opt + opt_size
            if sec + nsec * 40 > len(head):
                f.seek(0)
                head = f.read(sec + nsec * 40 + 64)
            for i in range(nsec):
                s = sec + i * 40
                if s + 40 > len(head):
                    break
                vsize, va, raw_size, raw_ptr = struct.unpack_from("<IIII", head, s + 8)
                if va <= rva < va + max(vsize, raw_size):
                    avail = raw_size - (rva - va)
                    if avail <= 0:
                        return (0, 0)
                    return (raw_ptr + (rva - va), avail)
            return (0, 0)
    except (OSError, struct.error):
        return None


def _read_range(path: Path, start: int, size: int) -> bytes:
    try:
        with open(path, "rb") as f:
            f.seek(start)
            return f.read(min(size, RSRC_MAX))
    except OSError:
        return b""


def read_plugin_pipl(target: Path, rsrc_files: Iterable[Path] = ()) -> List[PiPLEntry]:
    """Daftar efek di dalam satu plugin (.aex atau bundle .plugin)."""
    rsrc_files = list(rsrc_files)
    if rsrc_files:
        entries: List[PiPLEntry] = []
        for r in rsrc_files:
            entries.extend(parse_pipl(_read_range(r, 0, RSRC_MAX)))
        return entries
    if target.is_dir():
        return []
    rng = pe_resource_range(target)
    if rng is None:
        return parse_pipl(_read_range(target, 0, RSRC_MAX))
    start, size = rng
    if size <= 0:
        return []
    return parse_pipl(_read_range(target, start, size))


def scan_needles(path: Path, needles: List[str]) -> Dict[str, int]:
    """Cari match name di seluruh isi file.

    2 = cocok kuat (Pascal string, seperti di PiPL), 1 = cocok lemah (teks
    biasa / UTF-16). Dipakai untuk plugin yang PiPL-nya tidak terbaca.
    """
    hits: Dict[str, int] = {}
    if not needles:
        return hits
    pas = [bytes([min(len(n.encode("utf-8")), 255)]) + n.encode("utf-8") for n in needles]
    plain = [n.encode("utf-8") for n in needles]
    wide = [n.encode("utf-16-le") for n in needles]
    left = len(needles)
    tail = b""
    try:
        with open(path, "rb") as f:
            while left > 0:
                buf = f.read(SCAN_CHUNK)
                if not buf:
                    break
                data = tail + buf
                for i, n in enumerate(needles):
                    if hits.get(n) == 2:
                        continue
                    if pas[i] in data:
                        hits[n] = 2
                        left -= 1
                    elif n not in hits and (plain[i] in data or wide[i] in data):
                        hits[n] = 1
                tail = data[-SCAN_OVERLAP:]
    except OSError:
        pass
    return hits
