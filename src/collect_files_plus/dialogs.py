"""Kotak pesan bertema (ikut terang/gelap).

Messagebox bawaan Windows selalu putih, jadi di tema gelap aplikasi memakai jendela ini:
ikon bulat berwarna, teks, dan tombol OK atau Ya/Tidak, dengan title bar gelap/terang.
"""

from __future__ import annotations

from . import theme
from .i18n import _

# jenis -> (huruf di ikon, warna status)
ICONS = {
    "showinfo": ("i", "run"),
    "showwarning": ("!", "warn"),
    "showerror": ("×", "error"),
    "askyesno": ("?", "run"),
}

current = None      # dialog yang sedang terbuka (tk.Toplevel; dipakai test & screenshot)


def show(root, title: str, message: str, kind: str = "showinfo", dark: bool = False, scale: float = 1.0) -> bool:
    """Tampilkan pesan dan tunggu sampai ditutup. askyesno -> True kalau "Ya"; lainnya -> True."""
    import tkinter as tk                     # di sini, bukan di atas: lihat catatan di menus.py
    from tkinter import ttk

    global current

    def px(n: float) -> int:
        return int(round(n * scale))

    style = ttk.Style(root)
    bg = style.lookup("TFrame", "background") or ("#1c1c1c" if dark else "#fafafa")
    letter, status = ICONS.get(kind, ICONS["showinfo"])
    color = theme.STATUS_COLORS["dark" if dark else "light"][status]

    win = tk.Toplevel(root)
    win.withdraw()
    win.title(title)
    win.resizable(False, False)
    try:
        if root.winfo_viewable():
            win.transient(root)
    except tk.TclError:
        pass
    win.configure(background=bg)

    body = ttk.Frame(win, padding=(px(20), px(18), px(22), px(14)))
    body.pack(fill="both", expand=True)
    size = px(34)
    icon = tk.Canvas(body, width=size, height=size, highlightthickness=0, borderwidth=0, background=bg)
    icon.create_oval(1, 1, size - 1, size - 1, fill=color, outline=color)
    icon.create_text(size / 2, size / 2, text=letter, fill="#1c1c1c" if dark else "#ffffff",
                     font=("Segoe UI", -px(20), "bold"))
    icon.grid(row=0, column=0, sticky="n", padx=(0, px(14)))
    ttk.Label(body, text=message, justify="left", wraplength=px(440)).grid(row=0, column=1, sticky="w")

    buttons = ttk.Frame(body)
    buttons.grid(row=1, column=0, columnspan=2, sticky="e", pady=(px(18), 0))
    result = {"value": kind != "askyesno"}

    def close(value: bool) -> None:
        result["value"] = value
        try:
            win.grab_release()
        except tk.TclError:
            pass
        win.destroy()

    accent = "Accent.TButton" if _has_style(style) else "TButton"
    if kind == "askyesno":
        first = ttk.Button(buttons, text=_("Ya"), style=accent, command=lambda: close(True))
        first.pack(side="left", padx=(0, px(8)))
        ttk.Button(buttons, text=_("Tidak"), command=lambda: close(False)).pack(side="left")
        cancel_value = False
    else:
        first = ttk.Button(buttons, text="OK", style=accent, command=lambda: close(True))
        first.pack(side="left")
        cancel_value = True
    win.answer = close                     # untuk test & screenshot: dialogs.current.answer(True)
    win.bind("<Return>", lambda _e: close(True))
    win.bind("<Escape>", lambda _e: close(cancel_value))
    win.protocol("WM_DELETE_WINDOW", lambda: close(cancel_value))

    # di tengah jendela utama (atau layar kalau jendela utama belum tampil)
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    try:
        if root.winfo_viewable():
            x = root.winfo_rootx() + (root.winfo_width() - w) // 2
            y = root.winfo_rooty() + (root.winfo_height() - h) // 3
        else:
            raise tk.TclError("belum tampil")
    except tk.TclError:
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 3
    win.geometry("+%d+%d" % (max(0, x), max(0, y)))
    win.deiconify()
    win.update_idletasks()
    theme.titlebar(win, dark)
    try:
        win.grab_set()
    except tk.TclError:
        pass
    first.focus_set()
    current = win
    try:
        root.wait_window(win)
    finally:
        current = None
    return result["value"]


def _has_style(style) -> bool:
    try:
        return bool(style.layout("Accent.TButton"))
    except Exception:  # noqa: BLE001
        return False
