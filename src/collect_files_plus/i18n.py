"""Bahasa tampilan: Indonesia (teks asli di kode), English, atau 日本語.

Teks di kode ditulis dalam bahasa Indonesia dan dibungkus ``_()``. Terjemahannya ada di
``EN`` (modul en.py) dan ``JA`` (modul ja.py). ``N_()`` menandai teks yang diterjemahkan
nanti saat dipakai (misalnya nilai dict tingkat modul).
"""

from __future__ import annotations

import locale
import os
import sys
from typing import Dict, Optional

LANGS = {"id": "Bahasa Indonesia", "en": "English", "ja": "日本語"}
ENV_VAR = "COLLECT_FILES_PLUS_LANG"

_lang = "id"
_table: Optional[Dict[str, str]] = None


def set_language(code: str) -> str:
    global _lang, _table
    _lang = code if code in LANGS else "id"
    _table = None
    return _lang


def get_language() -> str:
    return _lang


def _load(lang: str) -> Dict[str, str]:
    from .en import EN
    if lang == "ja":
        from .ja import JA
        return {**EN, **JA}           # teks yang belum diterjemahkan ke Jepang tampil dalam English
    return EN


def _(text: str) -> str:
    global _table
    if _lang == "id":
        return text
    if _table is None:
        _table = _load(_lang)
    return _table.get(text, text)


def N_(text: str) -> str:
    return text


def _from_code(code: str) -> str:
    code = code.lower()
    if code.startswith(("id", "in_", "indonesian")):
        return "id"
    if code.startswith(("ja", "japanese")):
        return "ja"
    return "en"


def system_language() -> str:
    """Bahasa sistem: 'id' (Indonesia), 'ja' (Jepang), selain itu 'en'. Bisa dipaksa lewat
    variabel lingkungan COLLECT_FILES_PLUS_LANG=id/en/ja."""
    forced = (os.environ.get(ENV_VAR) or "").strip().lower()
    if forced in LANGS:
        return forced
    if sys.platform == "win32":
        try:
            import ctypes
            primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
            return {0x21: "id", 0x11: "ja"}.get(primary, "en")   # LANG_INDONESIAN, LANG_JAPANESE
        except Exception:  # noqa: BLE001
            pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = (os.environ.get(var) or "").lower()
        if val and val not in ("c", "posix", "c.utf-8"):
            return _from_code(val)
    try:
        loc = (locale.getlocale()[0] or "").lower()
    except Exception:  # noqa: BLE001
        loc = ""
    return _from_code(loc) if loc else "en"
