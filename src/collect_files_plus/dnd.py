"""Drag & drop file dari Windows Explorer ke jendela Tk.

Tk tidak bisa menerima file dari Explorer sendiri. Di Windows, jendela didaftarkan
dengan DragAcceptFiles lalu pesan WM_DROPFILES ditangkap dengan mengganti window
procedure (subclass) lewat ctypes. Tanpa library tambahan. Di macOS/Linux modul ini
tidak melakukan apa-apa (macOS: drop ke ikon aplikasi lewat ::tk::mac::OpenDocument).
"""

from __future__ import annotations

import sys
from typing import Callable, List, Optional

WM_DROPFILES = 0x0233
_WM_COPYDATA = 0x004A
_WM_COPYGLOBALDATA = 0x0049
_MSGFLT_ALLOW = 1
_GWLP_WNDPROC = -4

_hooks: list = []  # referensi callback harus hidup selama jendela ada


def available() -> bool:
    return sys.platform == "win32"


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _LRESULT = ctypes.c_ssize_t
    _WNDPROC = ctypes.WINFUNCTYPE(_LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _shell32 = ctypes.WinDLL("shell32", use_last_error=True)

    _SetWindowLongPtr = getattr(_user32, "SetWindowLongPtrW", None) or _user32.SetWindowLongW
    _SetWindowLongPtr.restype = ctypes.c_void_p
    _SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    _user32.CallWindowProcW.restype = _LRESULT
    _user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                        wintypes.WPARAM, wintypes.LPARAM]
    _user32.IsWindow.restype = wintypes.BOOL
    _user32.IsWindow.argtypes = [wintypes.HWND]
    _shell32.DragAcceptFiles.restype = None
    _shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    _shell32.DragQueryFileW.restype = wintypes.UINT
    _shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    _shell32.DragFinish.restype = None
    _shell32.DragFinish.argtypes = [ctypes.c_void_p]

    def dropped_files(hdrop: int) -> List[str]:
        count = _shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
        out = []
        for i in range(count):
            length = _shell32.DragQueryFileW(hdrop, i, None, 0)
            buf = ctypes.create_unicode_buffer(length + 1)
            _shell32.DragQueryFileW(hdrop, i, buf, length + 1)
            out.append(buf.value)
        return out

    class _Hook:
        def __init__(self, hwnd: int, callback: Callable[[List[str]], None]):
            self.hwnd = hwnd
            self.callback = callback
            self.proc = _WNDPROC(self._wndproc)
            _shell32.DragAcceptFiles(hwnd, True)
            filt = getattr(_user32, "ChangeWindowMessageFilterEx", None)
            if filt is not None:  # supaya tetap bisa di-drop walau aplikasi jalan sebagai admin
                for msg in (WM_DROPFILES, _WM_COPYDATA, _WM_COPYGLOBALDATA):
                    try:
                        filt(wintypes.HWND(hwnd), wintypes.UINT(msg), wintypes.DWORD(_MSGFLT_ALLOW), None)
                    except Exception:  # noqa: BLE001
                        pass
            ctypes.set_last_error(0)
            self.old = _SetWindowLongPtr(hwnd, _GWLP_WNDPROC, ctypes.cast(self.proc, ctypes.c_void_p))
            if not self.old:
                _shell32.DragAcceptFiles(hwnd, False)
                raise OSError("SetWindowLongPtrW gagal (error %d)" % ctypes.get_last_error())

        def _wndproc(self, hwnd, msg, wparam, lparam):
            if msg == WM_DROPFILES:
                try:
                    files = dropped_files(wparam)
                finally:
                    _shell32.DragFinish(wparam)
                try:
                    self.callback(files)
                except Exception:  # noqa: BLE001 - jangan sampai jendela macet karena error di handler
                    pass
                return 0
            return _user32.CallWindowProcW(self.old, hwnd, msg, wparam, lparam)


def enable(widget, callback: Callable[[List[str]], None]) -> Optional[int]:
    """Aktifkan drop file ke `widget` (biasanya jendela utama). Mengembalikan HWND, atau
    None kalau tidak didukung.

    PENTING: callback dipanggil langsung dari window procedure, di tengah event loop Tk.
    Callback TIDAK BOLEH memanggil fungsi Tk/tkinter apa pun (termasuk after/after_idle):
    _tkinter tidak tahan dipanggil ulang dari situ dan Python bisa berhenti mendadak.
    Cukup simpan daftar path (mis. queue.Queue.put) lalu proses dari loop Tk biasa.
    """
    if sys.platform != "win32":
        return None
    widget.update_idletasks()
    hwnd = int(widget.winfo_id())
    if not hwnd or not _user32.IsWindow(hwnd):
        return None
    _hooks.append(_Hook(hwnd, callback))
    return hwnd
