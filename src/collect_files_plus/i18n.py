"""Bahasa tampilan: Indonesia (teks asli di kode) atau English.

Teks di kode ditulis dalam bahasa Indonesia dan dibungkus ``_()``. Terjemahan
English ada di ``EN`` (modul en.py). ``N_()`` menandai teks yang diterjemahkan
nanti saat dipakai (misalnya nilai dict tingkat modul).
"""

from __future__ import annotations

import locale
import os
import sys

LANGS = {"id": "Bahasa Indonesia", "en": "English"}
ENV_VAR = "COLLECT_FILES_PLUS_LANG"

_lang = "id"


def set_language(code: str) -> str:
    global _lang
    _lang = code if code in LANGS else "id"
    return _lang


def get_language() -> str:
    return _lang


def _(text: str) -> str:
    if _lang == "en":
        from .en import EN
        return EN.get(text, text)
    return text


def N_(text: str) -> str:
    return text


def system_language() -> str:
    """'id' kalau bahasa sistem Indonesia, selain itu 'en'. Bisa dipaksa lewat
    variabel lingkungan COLLECT_FILES_PLUS_LANG=id/en."""
    forced = (os.environ.get(ENV_VAR) or "").strip().lower()
    if forced in LANGS:
        return forced
    if sys.platform == "win32":
        try:
            import ctypes
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "id" if (langid & 0x3FF) == 0x21 else "en"   # 0x21 = LANG_INDONESIAN
        except Exception:  # noqa: BLE001
            pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = (os.environ.get(var) or "").lower()
        if val and val not in ("c", "posix", "c.utf-8"):
            return "id" if val.startswith(("id", "in_")) else "en"
    try:
        loc = (locale.getlocale()[0] or "").lower()
    except Exception:  # noqa: BLE001
        loc = ""
    return "id" if loc.startswith(("id", "indonesian")) else "en"
