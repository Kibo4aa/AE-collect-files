"""Menu drop-down bertema untuk Windows & Linux.

Menu bawaan Windows (tk.Menu) digambar oleh sistem dengan bingkai dan garis pemisah putih,
jadi di tema gelap terlihat belang. FlyoutMenu menggambar menunya sendiri dengan widget Tk
biasa: warnanya ikut tema, dan cara pakainya sama seperti tk.Menu (add_command, add_cascade,
add_radiobutton, add_checkbutton, add_separator, tk_popup).

Mouse: arahkan untuk menyorot / membuka submenu, klik untuk memilih, klik di luar untuk menutup.
Keyboard: panah atas/bawah/kanan/kiri, Enter atau spasi, Escape.

tkinter di-import di dalam fungsi (bukan di atas) supaya test dengan tkinter tiruan tidak
meninggalkan modul yang terikat ke tiruan itu.
"""

from __future__ import annotations

from typing import Callable, List, Optional

CHECK = "✓"
BULLET = "•"
ARROW = "›"


def is_dark(color: str) -> bool:
    try:
        c = str(color).lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return 0.299 * r + 0.587 * g + 0.114 * b < 128
    except (ValueError, IndexError):
        return False


class FlyoutMenu:
    """Pengganti tk.Menu yang digambar sendiri (warna ikut tema, tanpa bingkai putih)."""

    def __init__(self, root, scale: float = 1.0,
                 on_outside: Optional[Callable[["FlyoutMenu", int, int], bool]] = None):
        self.root = root
        self.scale = scale
        self.on_outside = on_outside
        self.entries: List[dict] = []
        self.kw = {"background": "#f9f9f9", "foreground": "#1a1a1a", "activebackground": "#e1e1e1",
                   "activeforeground": "#1a1a1a", "disabledforeground": "#a0a0a0"}
        self.win = None
        self.parent: Optional["FlyoutMenu"] = None
        self.child: Optional["FlyoutMenu"] = None
        self.rows: List[tuple] = []
        self.active = -1
        self.popped = None
        self.destroyed = False

    # ------------------------------------------------------------- seperti tk.Menu

    def configure(self, cnf=None, **kw) -> None:
        self.kw.update(cnf or {}, **kw)

    config = configure

    def cget(self, key):
        return self.kw.get(key)

    def add_command(self, label: str = "", command=None, accelerator: str = "", state: str = "normal", **_kw) -> None:
        self.entries.append({"kind": "command", "label": label, "command": command, "accelerator": accelerator,
                             "state": state})

    def add_cascade(self, label: str = "", menu=None, **_kw) -> None:
        self.entries.append({"kind": "cascade", "label": label, "menu": menu, "state": "normal"})

    def add_radiobutton(self, label: str = "", value=None, variable=None, command=None, **_kw) -> None:
        self.entries.append({"kind": "radiobutton", "label": label, "value": value, "variable": variable,
                             "command": command, "state": "normal"})

    def add_checkbutton(self, label: str = "", variable=None, command=None, **_kw) -> None:
        self.entries.append({"kind": "checkbutton", "label": label, "variable": variable, "command": command,
                             "state": "normal"})

    def add_separator(self, **_kw) -> None:
        self.entries.append({"kind": "separator"})

    def delete(self, first=0, last=None) -> None:
        self.unpost()
        self.entries = []

    def labels(self) -> List[str]:
        return [e.get("label") for e in self.entries if e["kind"] != "separator"]

    def entry(self, label: str) -> dict:
        for e in self.entries:
            if e.get("label") == label:
                return e
        raise KeyError(label)

    def invoke(self, label: str):
        """Seperti pengguna memilih item ini."""
        return self._run(self.entry(label))

    def tk_popup(self, x: int, y: int, entry: str = "") -> None:
        self.popped = (x, y)
        self.post(x, y)

    def grab_release(self) -> None:
        pass                                     # grab diatur sendiri saat menu dibuka/ditutup

    def destroy(self) -> None:
        self.destroyed = True
        self.unpost()
        for e in self.entries:
            if e["kind"] == "cascade" and e.get("menu") is not None:
                e["menu"].destroy()

    @property
    def is_open(self) -> bool:
        return self.win is not None

    # ------------------------------------------------------------- tampil / tutup

    def px(self, n: float) -> int:
        return int(round(n * self.scale))

    def _font(self):
        try:
            from tkinter import font as tkfont
            names = tkfont.names(self.root)
            return next((n for n in ("SunValleyBodyFont", "TkMenuFont") if n in names), None)
        except Exception:  # noqa: BLE001
            return None

    def post(self, x: int, y: int, parent: Optional["FlyoutMenu"] = None) -> None:
        import tkinter as tk

        self.unpost()
        self.parent = parent
        bg, fg, muted = self.kw["background"], self.kw["foreground"], self.kw["disabledforeground"]
        border = "#4a4a4a" if is_dark(bg) else "#cdcdcd"
        master = parent.win if parent is not None and parent.win is not None else self.root
        win = tk.Toplevel(master)
        win.withdraw()
        win.overrideredirect(True)
        try:
            win.attributes("-topmost", True)
        except Exception:  # noqa: BLE001
            pass
        outer = tk.Frame(win, background=border, padx=1, pady=1, borderwidth=0, highlightthickness=0)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, background=bg, padx=self.px(4), pady=self.px(4), borderwidth=0,
                         highlightthickness=0)
        inner.pack(fill="both", expand=True)
        font = self._font()
        self.rows = []
        for e in self.entries:
            r = len(self.rows)
            if e["kind"] == "separator":
                tk.Frame(inner, background=border, height=1, borderwidth=0, highlightthickness=0).grid(
                    row=r, column=0, columnspan=4, sticky="ew", padx=self.px(8), pady=self.px(4))
                self.rows.append((e, []))
                continue
            enabled = e.get("state", "normal") != "disabled"
            mark = ""
            if e["kind"] == "checkbutton" and e["variable"] is not None and e["variable"].get():
                mark = CHECK
            elif e["kind"] == "radiobutton" and e["variable"] is not None and e["variable"].get() == e["value"]:
                mark = BULLET
            texts = (mark, e["label"], e.get("accelerator") or "", ARROW if e["kind"] == "cascade" else "")
            cells = []
            for col, text in enumerate(texts):
                cell = tk.Label(inner, text=text, background=bg, foreground=fg if enabled and col != 2 else muted,
                                font=font, anchor="w" if col == 1 else ("e" if col == 2 else "center"),
                                padx=self.px(10 if col in (1, 2) else 6), pady=self.px(4),
                                borderwidth=0, highlightthickness=0)
                cell.grid(row=r, column=col, sticky="nsew")
                cell.bind("<Enter>", lambda _e, i=r: self._hover(i))
                cell.bind("<ButtonRelease-1>", lambda _e, i=r: self._click(i))
                cells.append(cell)
            self.rows.append((e, cells))
        inner.columnconfigure(1, weight=1)
        self.win = win
        self.active = -1

        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        if x + w > sw:                                    # tidak keluar layar
            x = parent.win.winfo_rootx() - w if parent is not None and parent.win is not None else sw - w
        if y + h > sh:
            y = sh - h
        win.geometry("+%d+%d" % (max(0, x), max(0, y)))
        win.deiconify()
        win.lift()
        if parent is None:                                # menu paling atas: pegang mouse & keyboard
            win.bind("<ButtonPress>", self._press, add="+")
            for key in ("<Up>", "<Down>", "<Left>", "<Right>", "<Return>", "<KP_Enter>", "<space>", "<Escape>"):
                win.bind(key, lambda _e, k=key: self._key(k))
            win.bind("<FocusOut>", lambda _e: self.root.after(200, self._check_focus), add="+")
            win.update_idletasks()
            self._grab(win, 5)

    def _grab(self, win, tries: int) -> None:
        if self.win is not win:
            return
        try:
            win.grab_set()
            win.focus_force()
        except Exception:  # noqa: BLE001 - jendela belum tampil: coba sebentar lagi
            if tries > 0:
                self.root.after(30, lambda: self._grab(win, tries - 1))

    def unpost(self) -> None:
        self._close_child()
        if self.win is not None:
            try:
                self.win.grab_release()
            except Exception:  # noqa: BLE001
                pass
            try:
                self.win.destroy()
            except Exception:  # noqa: BLE001
                pass
        self.win = None
        self.rows = []
        self.active = -1
        if self.parent is not None and self.parent.child is self:
            self.parent.child = None
        self.parent = None

    def _top(self) -> "FlyoutMenu":
        menu = self
        while menu.parent is not None:
            menu = menu.parent
        return menu

    def _close_child(self) -> None:
        if self.child is not None:
            child, self.child = self.child, None
            child.unpost()

    def _open_child(self, i: int, keyboard: bool = False) -> None:
        e, cells = self.rows[i]
        sub = e.get("menu")
        if sub is None or self.win is None:
            return
        if self.child is not sub or sub.win is None:
            self._close_child()
            sub.scale = self.scale
            x = self.win.winfo_rootx() + self.win.winfo_width() - self.px(2)
            y = (cells[1].winfo_rooty() if cells else self.win.winfo_rooty()) - self.px(5)
            sub.post(x, y, parent=self)
            self.child = sub
        if keyboard:
            sub._set_active(sub._step(-1, 1))

    # ------------------------------------------------------------- sorot & pilih

    def _set_active(self, i: int) -> None:
        if self.active == i:
            return
        if 0 <= self.active < len(self.rows):
            self._paint(self.active, False)
        self.active = i
        if 0 <= i < len(self.rows):
            self._paint(i, True)

    def _paint(self, i: int, on: bool) -> None:
        e, cells = self.rows[i]
        if not cells:
            return
        enabled = e.get("state", "normal") != "disabled"
        bg = self.kw["activebackground"] if on and enabled else self.kw["background"]
        fg = self.kw["activeforeground"] if on and enabled else self.kw["foreground"]
        for col, cell in enumerate(cells):
            try:
                cell.configure(background=bg,
                               foreground=fg if enabled and col != 2 else self.kw["disabledforeground"])
            except Exception:  # noqa: BLE001
                pass

    def _hover(self, i: int) -> None:
        self._set_active(i)
        e = self.rows[i][0]
        if e["kind"] == "cascade":
            self._open_child(i)
        else:
            self._close_child()

    def _click(self, i: int):
        e = self.rows[i][0]
        if e["kind"] == "cascade":
            self._open_child(i, keyboard=True)
            return None
        return self._run(e)

    def _run(self, e: dict):
        if e["kind"] in ("separator", "cascade") or e.get("state") == "disabled":
            return None
        self._top().unpost()
        if e["kind"] == "radiobutton":
            e["variable"].set(e["value"])
        elif e["kind"] == "checkbutton":
            e["variable"].set(not e["variable"].get())
        if e.get("command"):
            return e["command"]()
        return None

    def _step(self, start: int, step: int) -> int:
        n = len(self.rows)
        i = start
        for _n in range(n):
            i = (i + step) % n
            e = self.rows[i][0]
            if e["kind"] != "separator" and e.get("state", "normal") != "disabled":
                return i
        return -1

    def _key(self, key: str) -> str:
        menu = self
        while menu.child is not None and menu.child.win is not None and menu.child.active >= 0:
            menu = menu.child
        if key == "<Escape>":
            if menu is self:
                self.unpost()
            else:
                menu.unpost()
        elif key in ("<Up>", "<Down>"):
            start = menu.active if menu.active >= 0 else (0 if key == "<Up>" else -1)
            menu._set_active(menu._step(start, -1 if key == "<Up>" else 1))
        elif key == "<Right>":
            if menu.active >= 0 and menu.rows[menu.active][0]["kind"] == "cascade":
                menu._open_child(menu.active, keyboard=True)
        elif key == "<Left>":
            if menu is not self:
                menu.unpost()
        elif menu.active >= 0:                            # Enter / spasi
            menu._click(menu.active)
        return "break"

    # ------------------------------------------------------------- klik di luar

    def _inside(self, x: int, y: int) -> bool:
        if self.win is None:
            return False
        try:
            wx, wy = self.win.winfo_rootx(), self.win.winfo_rooty()
            return wx <= x < wx + self.win.winfo_width() and wy <= y < wy + self.win.winfo_height()
        except Exception:  # noqa: BLE001
            return False

    def _press(self, event) -> None:
        x, y = event.x_root, event.y_root
        menu = self
        while menu is not None:
            if menu._inside(x, y):
                return
            menu = menu.child
        self.unpost()
        if self.on_outside is not None:
            self.on_outside(self, x, y)

    def _check_focus(self) -> None:
        """Pengguna pindah ke aplikasi lain: tutup menu."""
        if self.win is None:
            return
        try:
            focus = self.root.focus_get()
        except Exception:  # noqa: BLE001
            focus = None
        if focus is None:
            self.unpost()
