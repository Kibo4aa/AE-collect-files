"""Tema tampilan (terang / gelap / ikuti Windows), warna status, dan font."""

from __future__ import annotations

import subprocess
import sys
from typing import Dict

MODES = ("system", "light", "dark")

# warna teks status di tabel, terbaca di tema terang maupun gelap
STATUS_COLORS: Dict[str, Dict[str, str]] = {
    "light": {"ok": "#0f7b0f", "warn": "#9d5d00", "error": "#c42b1c", "muted": "#707070", "run": "#005fb8"},
    "dark": {"ok": "#6ccb5f", "warn": "#f7c94b", "error": "#ff99a4", "muted": "#9a9a9a", "run": "#60cdff"},
}
TEXT_COLORS = {"light": ("#ffffff", "#1c1c1c"), "dark": ("#202020", "#e8e8e8")}  # (latar, teks) untuk tk.Text

_JA_FONTS = ("Yu Gothic UI", "Meiryo UI", "MS UI Gothic")
_FALLBACK_FONTS = ("Segoe UI",)
_original: Dict[str, str] = {}        # nama font Tk -> family semula
_base_size: Dict[str, int] = {}       # nama font Sun Valley -> ukuran semula (piksel)
_has: Dict[str, bool] = {}


def system_theme() -> str:
    """'dark' kalau Windows/macOS memakai mode gelap untuk aplikasi, selain itu 'light'."""
    if sys.platform == "win32":
        try:
            import winreg
            key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                value, _kind = winreg.QueryValueEx(k, "AppsUseLightTheme")
            return "light" if value else "dark"
        except OSError:
            return "light"
    if sys.platform == "darwin":
        try:
            out = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True,
                                 text=True, timeout=3)
            return "dark" if "Dark" in out.stdout else "light"
        except (OSError, subprocess.SubprocessError):
            return "light"
    return "light"


def resolve(mode: str) -> str:
    if mode == "system":
        return system_theme()
    return mode if mode in ("light", "dark") else "light"


def apply(root, mode: str, scale: float = 1.0) -> str:
    """Pasang tema Sun Valley. Mengembalikan 'light'/'dark', atau '' kalau tema tidak tersedia
    (aplikasi tetap jalan dengan tema bawaan Tk)."""
    name = resolve(mode)
    try:
        import sv_ttk
        sv_ttk.set_theme(name, root)
    except Exception:  # noqa: BLE001 - tanpa sv_ttk, pakai tema bawaan
        return ""
    _scale_fonts(root, scale)
    return name


def _scale_fonts(root, scale: float) -> None:
    """Font Sun Valley ditulis dalam piksel, jadi tidak ikut membesar di layar 125%/150%."""
    try:
        from tkinter import font as tkfont
        for name in tkfont.names(root):
            if not name.startswith("SunValley"):
                continue
            f = tkfont.nametofont(name, root=root)
            base = _base_size.setdefault(name, int(f.cget("size")))
            if base < 0:
                f.configure(size=int(round(base * scale)))
    except Exception:  # noqa: BLE001
        pass


def titlebar(root, dark: bool) -> None:
    """Title bar gelap/terang di Windows 10/11 (DwmSetWindowAttribute)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        user32, dwm = ctypes.WinDLL("user32"), ctypes.WinDLL("dwmapi")   # objek sendiri: argtypes tidak bentrok
        user32.GetParent.restype = wintypes.HWND
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, wintypes.UINT]
        dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        hwnd = user32.GetParent(root.winfo_id())
        if not hwnd:
            return
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (Windows 11 / Windows 10 lama)
            if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0020)  # gambar ulang frame
    except Exception:  # noqa: BLE001
        pass


def _has_family(root, family: str) -> bool:
    """Cek satu font terpasang tanpa mendaftar semua font (lambat kalau font-nya ribuan)."""
    if family not in _has:
        try:
            from tkinter import font as tkfont
            f = tkfont.Font(root=root, family=family, size=10)
            _has[family] = str(f.actual("family")).lower() == family.lower()
        except Exception:  # noqa: BLE001 - tidak disimpan: bisa jadi hanya Tk belum siap
            return False
    return _has[family]


def _family_for(root, orig: str, lang: str) -> str:
    strong = "semibold" in orig.lower() or "bold" in orig.lower()
    if lang == "ja":
        wanted = (("Yu Gothic UI Semibold",) if strong else ()) + _JA_FONTS
    elif orig.startswith("Segoe UI Variable") and not _has_family(root, orig):
        wanted = (("Segoe UI Semibold",) if strong else ()) + _FALLBACK_FONTS    # Windows 10
    else:
        return orig
    return next((f for f in wanted if _has_family(root, f)), orig)


def apply_fonts(root, lang: str) -> None:
    """Bahasa Jepang: pakai font UI Jepang (Yu Gothic UI dll.) supaya huruf rapi; bahasa lain: font semula."""
    try:
        from tkinter import font as tkfont
        for name in tkfont.names(root):
            if name == "TkFixedFont" or not (name.startswith(("Tk", "SunValley"))):
                continue
            f = tkfont.nametofont(name, root=root)
            orig = _original.setdefault(name, str(f.cget("family")))
            family = _family_for(root, orig, lang)
            if f.cget("family") != family:
                f.configure(family=family)
    except Exception:  # noqa: BLE001
        pass
