"""Mencari file font dari PostScript name (yang tersimpan di .aep)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

FONT_EXT = {".ttf", ".otf", ".ttc", ".otc"}
CACHE_VERSION = 1


@dataclass(frozen=True)
class FontFace:
    path: Path
    index: int
    post_script_name: str
    family: str
    style: str


def default_font_dirs() -> List[Path]:
    dirs: List[Path] = []
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot") or r"C:\Windows"
        dirs.append(Path(windir, "Fonts"))
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(Path(local, "Microsoft", "Windows", "Fonts"))
    elif sys.platform == "darwin":
        dirs += [Path.home() / "Library/Fonts", Path("/Library/Fonts"),
                 Path("/System/Library/Fonts"), Path("/System/Library/Fonts/Supplemental")]
    else:
        dirs += [Path.home() / ".fonts", Path.home() / ".local/share/fonts",
                 Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]
    return [d for d in dirs if d.is_dir()]


def adobe_fonts_dirs() -> List[Path]:
    """Folder tempat Creative Cloud menyimpan Adobe Fonts (tidak boleh dicopy)."""
    out: List[Path] = []
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            out.append(Path(appdata, "Adobe", "CoreSync", "plugins", "livetype"))
    elif sys.platform == "darwin":
        out.append(Path.home() / "Library/Application Support/Adobe/CoreSync/plugins/livetype")
    return out


def default_cache_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "CollectFilesPlus" / "font-index.json"


def _read_faces(path: Path) -> List[List]:
    """[[index, postscript, family, style], ...] untuk satu file font."""
    from fontTools.ttLib import TTCollection, TTFont

    faces: List[List] = []

    def names(font) -> List:
        name = font["name"]
        ps = name.getDebugName(6) or ""
        family = name.getDebugName(16) or name.getDebugName(1) or ""
        style = name.getDebugName(17) or name.getDebugName(2) or ""
        return [ps, family, style]

    if path.suffix.lower() in (".ttc", ".otc"):
        coll = TTCollection(str(path), lazy=True)
        try:
            for i, font in enumerate(coll.fonts):
                faces.append([i] + names(font))
        finally:
            coll.close()
    else:
        font = TTFont(str(path), lazy=True, fontNumber=0)
        try:
            faces.append([0] + names(font))
        finally:
            font.close()
    return faces


class FontIndex:
    """Indeks PostScript name -> file font, dengan cache di disk."""

    def __init__(self, dirs: Optional[Sequence[Path]] = None, cache_path: Optional[Path] = None,
                 use_cache: bool = True):
        self.dirs = list(dirs) if dirs is not None else default_font_dirs()
        self.cache_path = cache_path if cache_path is not None else default_cache_path()
        self.use_cache = use_cache
        self.by_ps: Dict[str, List[FontFace]] = {}
        self.files_scanned = 0

    def build(self, progress: Optional[Callable[[str], None]] = None) -> "FontIndex":
        cache = self._load_cache()
        new_cache: Dict[str, dict] = {}
        files: List[Path] = []
        for d in self.dirs:
            for dirpath, _dirs, names in os.walk(d):
                for n in names:
                    if Path(n).suffix.lower() in FONT_EXT:
                        files.append(Path(dirpath, n))
        for i, f in enumerate(files):
            try:
                st = f.stat()
            except OSError:
                continue
            key = str(f)
            stamp = [st.st_size, int(st.st_mtime)]
            rec = cache.get(key)
            if not rec or rec.get("stamp") != stamp:
                if progress and i % 25 == 0:
                    progress("Membaca font %d/%d: %s" % (i + 1, len(files), f.name))
                try:
                    faces = _read_faces(f)
                except Exception:  # file font rusak / format aneh
                    faces = []
                rec = {"stamp": stamp, "faces": faces}
                self.files_scanned += 1
            new_cache[key] = rec
            for idx, ps, family, style in rec["faces"]:
                if ps:
                    self.by_ps.setdefault(ps.lower(), []).append(FontFace(f, idx, ps, family, style))
        self._save_cache(new_cache)
        return self

    def lookup(self, post_script_name: str) -> Optional[FontFace]:
        faces = self.by_ps.get((post_script_name or "").lower())
        return faces[0] if faces else None

    def _load_cache(self) -> Dict[str, dict]:
        if not self.use_cache:
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if data.get("version") == CACHE_VERSION:
                return data.get("files", {})
        except (OSError, ValueError, AttributeError):
            pass
        return {}

    def _save_cache(self, files: Dict[str, dict]) -> None:
        if not self.use_cache:
            return
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps({"version": CACHE_VERSION, "files": files}),
                                       encoding="utf-8")
        except OSError:
            pass
