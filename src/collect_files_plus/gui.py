"""Jendela aplikasi (tkinter)."""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import sys
import threading
import traceback
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__, dialogs, dnd, menus, sendto, theme, updater
from .i18n import LANGS, N_, _, get_language, set_language, system_language

APP_TITLE = "Collect Files Plus"
GITHUB_URL = "https://github.com/Kibo4aa/AE-collect-files"
CHECK_ON = "☑ "
CHECK_OFF = "☐ "


def settings_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home())
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "CollectFilesPlus" / "settings.json"


def load_settings() -> dict:
    try:
        return json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(data: dict) -> None:
    try:
        p = settings_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def ui_scale(root) -> float:
    """Skala tampilan (1.0 = 96 DPI). Di Windows 150% hasilnya 1.5."""
    try:
        return max(1.0, float(root.winfo_fpixels("1i")) / 96.0)
    except Exception:  # noqa: BLE001
        return 1.0


def set_icon(root) -> None:
    try:
        png = Path(__file__).resolve().parent / "assets" / "icon.png"
        if png.is_file():
            img = tk.PhotoImage(file=str(png))
            root.iconphoto(True, img)
            root._cfp_icon = img  # simpan referensi supaya tidak dibuang garbage collector
    except Exception:  # noqa: BLE001
        pass


def open_folder(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError:
        pass


def reveal(path: Path) -> None:
    """Tampilkan file di Explorer/Finder (file-nya terpilih)."""
    path = Path(path)
    try:
        if sys.platform == "win32" and path.exists():
            subprocess.Popen(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin" and path.exists():
            subprocess.Popen(["open", "-R", str(path)])
        else:
            open_folder(path if path.is_dir() else path.parent)
    except OSError:
        pass


def docs_dir() -> Path:
    return Path(__file__).resolve().parent / "docs"


def show_tip(master, text: str, x: int, y: int, wrap: int = 900):
    """Jendela tooltip kecil di dekat (x, y) layar, digeser supaya tetap di dalam jendela aplikasi.
    Ukurannya dihitung dulu selagi tersembunyi: posisi hanya diatur sekali sebelum tampil (Windows
    mengabaikan perubahan posisi kedua sebelum jendela muncul)."""
    win = tk.Toplevel(master)
    win.withdraw()
    win.wm_overrideredirect(True)
    ttk.Label(win, text=text, padding=(8, 4), relief="solid", borderwidth=1, wraplength=wrap,
              justify="left").pack()
    nx, ny = x, y
    try:
        win.update_idletasks()
        w, h = int(win.winfo_reqwidth()), int(win.winfo_reqheight())
        top = master.winfo_toplevel()
        left, upper = int(top.winfo_rootx()), int(top.winfo_rooty())
        right, lower = left + int(top.winfo_width()), upper + int(top.winfo_height())
        nx = max(left + 4, min(x, right - w - 4))
        ny = y if y + h <= lower - 4 else max(upper + 4, y - h - 28)     # tidak muat di bawah: di atas
        if TIP_TRACE is not None:
            TIP_TRACE.append({"x": x, "y": y, "w": w, "h": h, "left": left, "right": right, "nx": nx, "ny": ny})
    except Exception as exc:  # noqa: BLE001 - posisi awal tetap dipakai
        if TIP_TRACE is not None:
            TIP_TRACE.append({"error": repr(exc)})
    win.wm_geometry("+%d+%d" % (nx, ny))
    win.deiconify()
    return win


#: Untuk uji tampilan: daftar perhitungan posisi tooltip (None = tidak dicatat).
TIP_TRACE: Optional[list] = None


class Tip:
    """Tooltip untuk satu widget: penjelasan muncul saat kursor diam di atasnya."""

    def __init__(self, widget, text: str, delay: int = 450):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.win = None
        self.job = None
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")
        widget.tooltip = self

    def _enter(self, _e=None) -> None:
        self._hide()
        try:
            self.job = self.widget.after(self.delay, self._show)
        except Exception:  # noqa: BLE001
            self.job = None

    def _show(self) -> None:
        self.job = None
        try:
            if not self.text or not self.widget.winfo_exists():
                return
            x = self.widget.winfo_rootx() + 16
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
            self.win = show_tip(self.widget, self.text, x, y, wrap=420)
        except Exception:  # noqa: BLE001 - widget sudah dibangun ulang (ganti bahasa/tema)
            self.win = None

    def _hide(self, _e=None) -> None:
        if self.job is not None:
            try:
                self.widget.after_cancel(self.job)
            except Exception:  # noqa: BLE001
                pass
            self.job = None
        if self.win is not None:
            try:
                self.win.destroy()
            except Exception:  # noqa: BLE001
                pass
            self.win = None


class TreeTip:
    """Tooltip tabel: keterangan baris (kalau ada) atau teks lengkap sel yang terpotong."""

    def __init__(self, tree, min_len: int = 28, row_tips: Optional[Dict[str, str]] = None):
        self.tree = tree
        self.min_len = min_len
        self.row_tips = row_tips if row_tips is not None else {}
        self.win = None
        self.cell = None
        self.job = None
        tree.bind("<Motion>", self._motion, add="+")
        tree.bind("<Leave>", lambda _e: self._hide(), add="+")

    def text_at(self, row: str, col: str) -> str:
        if not row:
            return ""
        if col == "#0":
            return str(self.tree.item(row, "text")).replace(CHECK_ON, "").replace(CHECK_OFF, "").strip()
        try:
            values = self.tree.item(row, "values")
            return str(values[int(col[1:]) - 1])
        except (ValueError, IndexError, TypeError):
            return ""

    def _motion(self, e) -> None:
        cell = (self.tree.identify_row(e.y), self.tree.identify_column(e.x))
        if cell == self.cell:
            return
        self._hide()
        self.cell = cell
        self.job = self.tree.after(600, lambda: self._show(e.x_root, e.y_root))

    def tip_at(self, row: str, col: str) -> str:
        """Teks tooltip untuk sel ini ('' = tidak ada)."""
        if not row:
            return ""
        if self.row_tips.get(row):
            return self.row_tips[row]
        text = self.text_at(row, col)
        return text if len(text) >= self.min_len else ""

    def _show(self, x: int, y: int) -> None:
        self.job = None
        try:
            if not self.tree.winfo_exists():
                return
            text = self.tip_at(*self.cell) if self.cell else ""
            if not text:
                return
            self.win = show_tip(self.tree, text, x + 14, y + 18)
        except Exception:  # noqa: BLE001 - tabel sudah dibangun ulang (ganti bahasa)
            self.win = None

    def _hide(self) -> None:
        if self.job is not None:
            try:
                self.tree.after_cancel(self.job)
            except Exception:  # noqa: BLE001
                pass
            self.job = None
        if self.win is not None:
            try:
                self.win.destroy()
            except Exception:  # noqa: BLE001
                pass
            self.win = None
        self.cell = None


class EmptyHint:
    """Teks petunjuk di tengah tabel yang masih kosong (hilang begitu ada isinya)."""

    def _init_empty(self) -> None:
        self.empty_text = ""
        self.empty_label = None
        self.tips: Dict[str, str] = {}

    def set_empty_text(self, text: str) -> None:
        self.empty_text = text
        if self.empty_label is not None:
            self.empty_label.configure(text=text)
        self._sync_empty()

    def _sync_empty(self) -> None:
        show = bool(self.empty_text) and not self.tree.get_children()
        if show and self.empty_label is None:
            self.empty_label = ttk.Label(self, text=self.empty_text, justify="center", anchor="center",
                                         style="Empty.TLabel")
        if self.empty_label is not None:
            if show:
                self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
            else:
                self.empty_label.place_forget()


class CheckTree(ttk.Frame, EmptyHint):
    """Treeview dengan kotak centang di kolom pertama."""

    def __init__(self, master, columns, widths, height=12):
        super().__init__(master)
        self.tree = ttk.Treeview(self, columns=[c for c in columns[1:]], height=height, selectmode="extended")
        self.tree.heading("#0", text=columns[0], anchor="w")
        self.tree.column("#0", width=widths[0], minwidth=60, anchor="w", stretch=True)
        for i, c in enumerate(columns[1:], start=1):   # semua kolom ikut melebar/menyempit bersama jendela
            self.tree.heading(c, text=c, anchor="w")
            self.tree.column(c, width=widths[i], minwidth=50, anchor="w", stretch=True)
        ys = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.checked: Dict[str, bool] = {}
        self.labels: Dict[str, str] = {}
        self.checkable: Dict[str, bool] = {}
        self.on_change = None
        self.tree.bind("<Button-1>", self._click, add="+")
        self.tree.bind("<space>", self._space, add="+")
        self._init_empty()
        self.tip = TreeTip(self.tree, row_tips=self.tips)

    def clear(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.checked.clear()
        self.labels.clear()
        self.checkable.clear()
        self.tips.clear()
        self._sync_empty()

    def add(self, iid: str, label: str, values=(), checked=False, checkable=True, tags=(), tip: str = "") -> None:
        self.labels[iid] = label
        self.checked[iid] = bool(checked)
        self.checkable[iid] = checkable
        if tip:
            self.tips[iid] = tip
        self.tree.insert("", "end", iid=iid, text=self._text(iid), values=list(values), tags=tuple(tags))
        self._sync_empty()

    def _text(self, iid: str) -> str:
        if not self.checkable.get(iid, True):
            return "   " + self.labels[iid]
        return (CHECK_ON if self.checked[iid] else CHECK_OFF) + self.labels[iid]

    def set(self, iid: str, value: bool) -> None:
        if iid in self.checked and self.checkable.get(iid, True):
            self.checked[iid] = bool(value)
            self.tree.item(iid, text=self._text(iid))

    def set_all(self, value: bool) -> None:
        for iid in self.checked:
            self.set(iid, value)
        self._changed()

    def toggle(self, iids) -> None:
        for iid in iids:
            self.set(iid, not self.checked.get(iid, False))
        self._changed()

    def checked_ids(self) -> List[str]:
        return [i for i in self.tree.get_children() if self.checked.get(i)]

    def _changed(self) -> None:
        if self.on_change:
            self.on_change()

    def _click(self, event):
        if self.tree.identify_region(event.x, event.y) not in ("tree", "cell"):
            return None
        if self.tree.identify_column(event.x) != "#0":
            return None
        iid = self.tree.identify_row(event.y)
        if iid:
            self.toggle([iid])
        return None

    def _space(self, _event):
        self.toggle(self.tree.selection())
        return "break"


class InfoTree(ttk.Frame, EmptyHint):
    """Treeview biasa (tanpa centang)."""

    def __init__(self, master, columns, widths, height=12):
        super().__init__(master)
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=height)
        for c, w in zip(columns, widths):              # semua kolom ikut melebar/menyempit bersama jendela
            self.tree.heading(c, text=c, anchor="w")
            self.tree.column(c, width=w, minwidth=50, anchor="w", stretch=True)
        ys = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._init_empty()
        self.tip = TreeTip(self.tree, row_tips=self.tips)

    def clear(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tips.clear()
        self._sync_empty()

    def add(self, values, iid: Optional[str] = None, tags=(), tip: str = "") -> str:
        if iid is None:
            iid = self.tree.insert("", "end", values=list(values), tags=tuple(tags))
        else:
            iid = self.tree.insert("", "end", iid=iid, values=list(values), tags=tuple(tags))
        if tip:
            self.tips[iid] = tip
        self._sync_empty()
        return iid

    def set_row(self, iid: str, values, tags=None) -> None:
        if iid in self.tree.get_children():
            if tags is None:
                self.tree.item(iid, values=list(values))
            else:
                self.tree.item(iid, values=list(values), tags=tuple(tags))


BATCH_TAG = {"ok": "ok", "catatan": "warn", "gagal": "error", "jalan": "run", "dibatalkan": "muted",
             "menunggu": "muted"}
SINGLE_HINT = N_("Pilih file .aep untuk mulai.")
BATCH_HINT = N_("Tambahkan project ke daftar, lalu klik Analisa semua atau Collect semua.")
NOT_ANALYZED = N_("Belum ada hasil. Klik Analisa.")
TIP_FOOTAGE = N_("Copy footage yang dipakai, lalu relink project ke folder (Footage).")
TIP_FONTS = N_("Copy file font yang dipakai text layer. Adobe Fonts tidak dicopy: aktifkan di Creative Cloud.")
TIP_PLUGINS = N_("Copy file plugin pihak ketiga, hanya yang efeknya dipakai project.")
TIP_REDUCE = N_("Buang comp dan footage yang tidak dipakai comp yang dicentang (seperti File > Reduce Project "
                "di After Effects).")
TIP_SKIP_OFF = N_("Efek dengan ikon fx mati tidak dihitung, jadi pluginnya tidak ikut dicopy.")
TIP_SUPPORT = N_("Ikut copy DLL dan file data di folder yang sama dengan file plugin.")
TIP_PRESETS = N_("Ikut copy animation preset (.ffx) yang namanya sama dengan efek yang di-rename.")
TIP_AUTO_SCOPE = N_("Comp di Render Queue. Kalau kosong, comp yang aktif saat project disimpan. Kalau tidak ada, "
                    "semua comp.")


class App:
    def __init__(self, root: tk.Tk, initial: Optional[str] = None, batch: Optional[List[str]] = None):
        self.root = root
        self.settings = load_settings()
        # pemakai lama (settings sudah ada) tetap bahasa Indonesia; pemakai baru ikut bahasa sistem
        set_language(self.settings.get("lang") or ("id" if self.settings else system_language()))
        self.aep = None
        self.aep_stale = False            # project di memori sudah diubah collect: baca ulang sebelum dipakai
        self.rq_ids: set = set()
        self.active_id: Optional[int] = None
        self.comp_rows: list = []         # (id, nama, dipakai sebagai precomp di n comp, dicentang awal)
        self.analysis = None
        self.analysis_key = None
        self.result = None
        self.events: "queue.Queue[tuple]" = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.cancel = threading.Event()
        self.batch_paths: List[Path] = []
        self.batch_run = None
        self.batch_total = 0
        self.last_folder: Optional[Path] = None
        self.last_report: Optional[Path] = None
        self.update_info = None
        self.update_dismissed = False
        self.row_paths: Dict[str, Dict[str, Path]] = {}

        self.scale = ui_scale(root)
        root.title("%s %s" % (APP_TITLE, __version__))
        w, h = self._saved_size()                       # ukuran terakhir, muat di layar
        screen = self._screen()
        if screen:                                      # di tengah layar utama
            root.geometry("%dx%d+%d+%d" % (w, h, max(0, (screen[0] - w) // 2),
                                            max(0, (screen[1] - h - self.px(100)) // 2)))
        else:
            root.geometry("%dx%d" % (w, h))
        root.minsize(*self._min_size())
        if self.settings.get("maximized"):
            try:
                root.state("zoomed")
            except Exception:  # noqa: BLE001 - tidak semua sistem punya "zoomed"
                pass
        set_icon(root)

        s = self.settings
        self.var_aep = tk.StringVar(value=initial or "")
        self.var_dest = tk.StringVar(value=s.get("dest", ""))
        self.var_status = tk.StringVar(value=_(SINGLE_HINT))
        self.opt_footage = tk.BooleanVar(value=s.get("footage", True))
        self.opt_reduce = tk.BooleanVar(value=s.get("reduce", False))
        self.opt_fonts = tk.BooleanVar(value=s.get("fonts", True))
        self.opt_plugins = tk.BooleanVar(value=s.get("plugins", True))
        self.opt_skip_off = tk.BooleanVar(value=s.get("skip_disabled", True))
        self.opt_support = tk.BooleanVar(value=s.get("support_files", False))
        self.opt_presets = tk.BooleanVar(value=s.get("presets", False))
        self.var_batch_scope = tk.StringVar(value=s.get("batch_scope", "auto"))
        self.var_lang = tk.StringVar(value=get_language())
        self.var_theme = tk.StringVar(value=s.get("theme", "system"))
        self.var_auto_update = tk.BooleanVar(value=s.get("check_updates", True))
        self.var_sendto = tk.BooleanVar(value=sendto.available() and sendto.installed())

        self.theme_name = ""
        self.ctx_menu = None
        self.is_busy = False
        self._apply_theme()
        self._build()
        self._bind_keys()
        root.after_idle(self._sync_titlebar)       # setelah jendela tampil (title bar gelap/terang)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self._poll)
        self.dnd_ok = self._setup_dnd()
        if initial:
            root.after(200, self.load_project)
        if batch:
            self.add_batch_paths(batch)
        result = updater.take_update_result()          # baru saja di-update oleh skrip pemasang?
        if result is not None:
            root.after(300, lambda: self._show_update_result(*result))
        if (self.var_auto_update.get() and not os.environ.get(updater.NO_CHECK_ENV)
                and not os.environ.get("COLLECT_FILES_PLUS_AUTOCLOSE_MS")):
            root.after(1500, self.check_updates)

    # ------------------------------------------------------------ tampilan

    def px(self, n: float) -> int:
        return int(round(n * self.scale))

    def _screen(self):
        try:
            return int(self.root.winfo_screenwidth()), int(self.root.winfo_screenheight())
        except Exception:  # noqa: BLE001
            return None

    def _min_size(self):
        """Batas minimum jendela; di layar kecil (mis. laptop 1366x768 dengan skala 125%) ikut mengecil
        supaya tombol di bawah tetap terlihat."""
        w, h = self.px(920), self.px(600)
        screen = self._screen()
        if screen:
            w = max(480, min(w, screen[0]))
            h = max(400, min(h, screen[1] - self.px(100)))   # title bar + menu + taskbar
        return w, h

    def _saved_size(self):
        """Ukuran jendela terakhir, tidak lebih besar dari layar dan tidak lebih kecil dari batas minimum."""
        m = re.match(r"^(\d{3,5})x(\d{3,5})", str(self.settings.get("geometry") or ""))
        w, h = (int(m.group(1)), int(m.group(2))) if m else (self.px(1100), self.px(740))
        screen = self._screen()
        if screen:
            w = min(w, screen[0])
            h = min(h, screen[1] - self.px(100))
        min_w, min_h = self._min_size()
        return max(w, min_w), max(h, min_h)

    def _w(self, *widths: int) -> List[int]:
        return [self.px(w) for w in widths]

    def _apply_theme(self) -> None:
        """Tema + font sesuai bahasa + ukuran baris tabel. Dipanggil saat mulai, ganti tema, ganti bahasa."""
        self.theme_name = theme.apply(self.root, self.var_theme.get(), self.scale)
        theme.apply_fonts(self.root, get_language())
        style = ttk.Style(self.root)
        try:  # baris tabel ikut membesar di layar high-DPI dan untuk huruf Jepang
            style.configure("Treeview", rowheight=self._row_height())
        except Exception:  # noqa: BLE001
            pass
        self.accent = "TButton"
        if self.theme_name:
            try:
                style.layout("Accent.TButton")
                self.accent = "Accent.TButton"
                style.configure("TButton", padding=(self.px(10), self.px(3)))
                style.configure("Accent.TButton", padding=(self.px(14), self.px(3)))
            except Exception:  # noqa: BLE001
                pass

    def _row_height(self) -> int:
        try:
            from tkinter import font as tkfont
            name = "SunValleyBodyFont" if self.theme_name else "TkDefaultFont"
            return max(self.px(24), int(tkfont.nametofont(name, root=self.root).metrics("linespace")) + self.px(8))
        except Exception:  # noqa: BLE001 - tanpa Tk asli
            return self.px(22) + 4

    def _sync_titlebar(self) -> None:
        theme.titlebar(self.root, self.theme_name == "dark")

    def _recolor(self) -> None:
        """Warna status di tabel + kotak Log sesuai tema."""
        colors = theme.STATUS_COLORS["dark" if self.theme_name == "dark" else "light"]
        for tree in self._trees():
            for tag, color in colors.items():
                try:
                    tree.tag_configure(tag, foreground=color)
                except Exception:  # noqa: BLE001
                    pass
        try:  # petunjuk di tabel kosong: warna redup, latar sama dengan tabel
            style = ttk.Style(self.root)
            field = style.lookup("Treeview", "fieldbackground") or style.lookup("Treeview", "background")
            style.configure("Empty.TLabel", foreground=colors["muted"], **({"background": field} if field else {}))
        except Exception:  # noqa: BLE001
            pass
        bg, fg = theme.TEXT_COLORS["dark" if self.theme_name == "dark" else "light"]
        try:
            self.log.configure(background=bg, foreground=fg, insertbackground=fg, relief="flat",
                               borderwidth=0, highlightthickness=0)
        except Exception:  # noqa: BLE001
            pass

    def _trees(self):
        return [t.tree for t in (self.comp_tree, self.plugin_tree, self.font_tree, self.foot_tree,
                                 self.fx_tree, self.batch_tree)]

    def _build(self) -> None:
        self._build_menu()
        pad = {"padx": 6, "pady": 4}

        # bar pemberitahuan update (ditampilkan kalau ada versi baru)
        self.update_bar = ttk.Frame(self.root, padding=(8, 6))
        self.update_label = ttk.Label(self.update_bar, text="")
        self.update_label.pack(side="left", padx=(4, 12))
        self.btn_update = ttk.Button(self.update_bar, text=_("Update sekarang"), command=self.start_update,
                                     style=self.accent)
        self.btn_update.pack(side="left", padx=2)
        ttk.Button(self.update_bar, text=_("Lihat perubahan"), command=self.open_release_page).pack(side="left", padx=2)
        ttk.Button(self.update_bar, text=_("Tutup"), command=self.hide_update_bar).pack(side="left", padx=2)

        top = ttk.Frame(self.root, padding=(8, 8, 8, 2))
        top.pack(fill="x")
        self._top = top
        ttk.Label(top, text=_("Project")).grid(row=0, column=0, sticky="w", **pad)
        self.ent_aep = ttk.Entry(top, textvariable=self.var_aep)
        self.ent_aep.grid(row=0, column=1, sticky="ew", **pad)
        self.btn_aep = ttk.Button(top, text=_("Pilih..."), command=self.choose_aep)
        self.btn_aep.grid(row=0, column=2, sticky="ew", **pad)
        ttk.Label(top, text=_("Folder tujuan")).grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(top, textvariable=self.var_dest).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(top, text=_("Pilih..."), command=self.choose_dest).grid(row=1, column=2, sticky="ew", **pad)
        top.columnconfigure(1, weight=1)

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=4)
        self.tab_names: List[str] = []

        def add_tab(frame, name: str) -> None:
            self.nb.add(frame, text=name)
            self.tab_names.append(name)

        def small(parent, text: str, command) -> None:
            """Tombol sekunder (datar) untuk aksi kecil di bawah tabel."""
            ttk.Button(parent, text=text, command=command, style="Toolbutton").pack(side="left", padx=(0, 2))

        # Tab comp + opsi: daftar comp di kiri, yang dikumpulkan + opsi di kanan
        tab1 = ttk.Frame(self.nb, padding=6)
        add_tab(tab1, _("Comp & opsi"))
        right = ttk.Frame(tab1)
        right.pack(side="right", fill="y", padx=(8, 0))
        left = ttk.Frame(tab1)
        left.pack(side="left", fill="both", expand=True)
        row = ttk.Frame(left)
        row.pack(side="bottom", fill="x", pady=(4, 0))
        ttk.Label(row, text=_("Pilih:")).pack(side="left", padx=(0, 6))
        small(row, _("Render Queue"), lambda: self.select_comps("rq"))
        small(row, _("Comp aktif"), lambda: self.select_comps("active"))
        small(row, _("Semua"), lambda: self.comp_tree.set_all(True))
        small(row, _("Kosongkan"), lambda: self.comp_tree.set_all(False))
        self.comp_tree = CheckTree(left, [_("Comp"), _("Keterangan")], self._w(340, 260), height=8)
        self.comp_tree.pack(fill="both", expand=True)
        groups = (
            (_("Yang dikumpulkan"), ((self.opt_footage, N_("Footage"), TIP_FOOTAGE),
                                     (self.opt_fonts, N_("Font"), TIP_FONTS),
                                     (self.opt_plugins, N_("Plugin"), TIP_PLUGINS))),
            (_("Opsi"), ((self.opt_reduce, N_("Reduce Project"), TIP_REDUCE),
                         (self.opt_skip_off, N_("Lewati efek yang dimatikan"), TIP_SKIP_OFF),
                         (self.opt_support, N_("File pendukung plugin"), TIP_SUPPORT),
                         (self.opt_presets, N_("Preset animasi (.ffx)"), TIP_PRESETS))),
        )
        for n, (title, items) in enumerate(groups):
            box = ttk.LabelFrame(right, text=title, padding=(10, 4, 10, 6))
            box.pack(fill="x", pady=(0 if n == 0 else 8, 0))
            for var, text, tip in items:
                cb = ttk.Checkbutton(box, text=_(text), variable=var)
                cb.pack(anchor="w", pady=2)
                Tip(cb, _(tip))

        # Tab plugin
        tab2 = ttk.Frame(self.nb, padding=6)
        add_tab(tab2, _("Plugin"))
        row2 = ttk.Frame(tab2)
        row2.pack(side="bottom", fill="x", pady=(4, 0))
        small(row2, _("Centang semua"), lambda: self.plugin_tree.set_all(True))
        small(row2, _("Hapus semua centang"), lambda: self.plugin_tree.set_all(False))
        self.plugin_total = ttk.Label(row2, text="")
        self.plugin_total.pack(side="right")
        self.plugin_tree = CheckTree(tab2, [_("File plugin"), _("Efek yang dipakai"), _("Ukuran"), _("Kecocokan")],
                                     self._w(380, 340, 80, 110), height=8)
        self.plugin_tree.pack(fill="both", expand=True)
        self.plugin_tree.on_change = self._update_plugin_total

        # Tab font, footage, efek
        tab3 = ttk.Frame(self.nb, padding=6)
        add_tab(tab3, _("Font"))
        self.font_tree = InfoTree(tab3, [_("Font"), _("File"), _("Status")], self._w(260, 520, 220))
        self.font_tree.pack(fill="both", expand=True)

        tab4 = ttk.Frame(self.nb, padding=6)
        add_tab(tab4, _("Footage"))
        self.foot_tree = InfoTree(tab4, [_("Item"), _("File"), _("Ukuran"), _("Status")], self._w(260, 520, 90, 170))
        self.foot_tree.pack(fill="both", expand=True)

        tab5 = ttk.Frame(self.nb, padding=6)
        add_tab(tab5, _("Semua efek"))
        self.fx_tree = InfoTree(tab5, [_("Efek"), _("Nama di layer"), _("Match name"), _("Dipakai"), _("Status")],
                                self._w(220, 220, 220, 70, 230))
        self.fx_tree.pack(fill="both", expand=True)
        for tree in (self.plugin_tree, self.font_tree, self.foot_tree, self.fx_tree):
            tree.set_empty_text(_(NOT_ANALYZED))

        # Tab batch: banyak project sekaligus (tombol Analisa/Collect di bawah berlaku untuk daftar ini)
        tabb = ttk.Frame(self.nb, padding=6)
        add_tab(tabb, _("Batch"))
        self.batch_tab = tabb
        rs = ttk.Frame(tabb)
        rs.pack(side="bottom", fill="x", pady=(6, 0))
        rb = ttk.Frame(tabb)
        rb.pack(side="bottom", fill="x", pady=(4, 0))
        ttk.Button(rb, text=_("Tambah file .aep..."), command=self.batch_add_files).pack(side="left", padx=(0, 4))
        ttk.Button(rb, text=_("Tambah folder..."), command=self.batch_add_folder).pack(side="left", padx=(0, 8))
        small(rb, _("Hapus yang dipilih"), self.batch_remove_selected)
        small(rb, _("Kosongkan"), self.batch_clear)
        self.batch_count = ttk.Label(rb, text="")
        self.batch_count.pack(side="right")
        ttk.Label(rs, text=_("Comp yang dibaca:")).pack(side="left", padx=(0, 4))
        auto = ttk.Radiobutton(rs, text=_("Otomatis"), value="auto", variable=self.var_batch_scope)
        auto.pack(side="left", padx=4)
        Tip(auto, _(TIP_AUTO_SCOPE))
        ttk.Radiobutton(rs, text=_("Semua comp"), value="all", variable=self.var_batch_scope).pack(side="left", padx=4)
        self.batch_tree = InfoTree(tabb, [_("Project"), _("Lokasi"), _("Comp"), _("Status"), _("Hasil")],
                                   self._w(150, 180, 140, 250, 250), height=8)
        self.batch_tree.pack(fill="both", expand=True)
        self.batch_tree.set_empty_text(_("Drag file .aep atau folder ke sini\natau klik \"Tambah file .aep...\""))

        tab6 = ttk.Frame(self.nb, padding=6)
        add_tab(tab6, _("Log"))
        self.log = tk.Text(tab6, height=10, wrap="word", padx=8, pady=6, state="disabled")
        self.log.pack(fill="both", expand=True)

        # baris bawah: Batal + progress hanya saat ada proses, "Buka folder hasil" hanya kalau ada hasil
        bottom = ttk.Frame(self.root, padding=(8, 4, 8, 8))
        self.btn_analyze = ttk.Button(bottom, text=_("Analisa"), command=self.start_analyze)
        self.btn_analyze.pack(side="left", padx=(0, 4))
        self.btn_collect = ttk.Button(bottom, text=_("Collect"), command=self.start_collect, style=self.accent)
        self.btn_collect.pack(side="left", padx=4)
        self.btn_open = ttk.Button(bottom, text=_("Buka folder hasil"), command=self.open_result)
        self.btn_cancel = ttk.Button(bottom, text=_("Batal"), command=self.cancel.set)
        self.progress = ttk.Progressbar(bottom, mode="determinate", length=self.px(170))
        self.status_label = ttk.Label(bottom, textvariable=self.var_status)
        self.status_label.pack(side="left", fill="x", expand=True, padx=(10, 0))
        bottom.pack(side="bottom", fill="x", before=self.nb)   # tombol tetap terlihat walau jendela pendek
        self._frames = [f for f in (self.menu_frame, self.update_bar, top, self.nb, bottom) if f is not None]
        self._layout_bottom()

        self._bind_tree_actions()
        self._update_comp_hint()
        self._recolor()
        # tombol Analisa/Collect di bawah: di tab Batch berlaku untuk semua project di daftar
        self.nb.bind("<<NotebookTabChanged>>", self._sync_action_buttons, add="+")
        self._sync_action_buttons()

    def _layout_bottom(self) -> None:
        """Tombol di kanan bawah hanya yang berguna saat ini: [progress][Batal] saat ada proses,
        [Buka folder hasil] kalau sudah ada hasil."""
        for w in (self.btn_open, self.btn_cancel, self.progress):
            w.pack_forget()
        if self.last_folder is not None:
            self.btn_open.pack(side="right", before=self.status_label)
        if self.is_busy:
            self.btn_cancel.pack(side="right", padx=(4, 8), before=self.status_label)
            self.progress.pack(side="right", padx=(10, 4), before=self.status_label)

    def _sync_action_buttons(self, _event=None) -> None:
        """Label tombol bawah mengikuti tab: "Analisa/Collect" (satu project) atau
        "Analisa semua/Collect semua" (daftar Batch)."""
        batch = self._on_batch_tab()
        try:
            self.btn_analyze.configure(text=_("Analisa semua") if batch else _("Analisa"))
            self.btn_collect.configure(text=_("Collect semua") if batch else _("Collect"))
            for w in (self.ent_aep, self.btn_aep):      # kolom Project tidak dipakai di tab Batch
                w.configure(state="disabled" if batch else "normal")
        except Exception:  # noqa: BLE001 - jendela sedang dibangun ulang
            return
        hints = (_(SINGLE_HINT), _(BATCH_HINT))
        if not self._busy_now(quiet=True) and self.var_status.get() in hints:
            self.var_status.set(hints[1] if batch else hints[0])

    @staticmethod
    def _autowrap(label, pack: bool = True) -> None:
        """Teks label membungkus mengikuti lebar jendela (dipasang di atas, selebar tab)."""
        if pack:
            label.pack(anchor="w", fill="x")
        label.bind("<Configure>", lambda e: label.configure(wraplength=max(200, e.width - 4)), add="+")

    def _build_menu(self) -> None:
        """Menu File / Pengaturan / Bantuan. Di Windows & Linux berupa baris tombol bertema (menu bar
        bawaan Windows selalu putih); di macOS menu bar sistem di atas layar."""
        dark = self.theme_name == "dark"
        bar = self._new_menu()
        m_file = self._new_menu(bar)
        m_file.add_command(label=_("Buka project..."), accelerator="Ctrl+O", command=self.choose_aep)
        m_file.add_command(label=_("Tambah project ke Batch..."), command=self.batch_add_files)
        m_file.add_command(label=_("Tambah folder ke Batch..."), command=self.batch_add_folder)
        m_file.add_separator()
        m_file.add_command(label=_("Buka folder hasil"), command=self.open_result)
        m_file.add_command(label=_("Buka laporan terakhir"), command=self.open_last_report)
        m_file.add_separator()
        m_file.add_command(label=_("Keluar"), command=self.on_close)
        bar.add_cascade(label=_("File"), menu=m_file)

        m_set = self._new_menu(bar)
        m_lang = self._new_menu(m_set)
        for code, name in LANGS.items():
            m_lang.add_radiobutton(label=name, value=code, variable=self.var_lang, command=self._on_lang_menu)
        m_set.add_cascade(label="Bahasa / Language / 言語", menu=m_lang)
        m_theme = self._new_menu(m_set)
        follow = _("Ikuti sistem") if sys.platform == "darwin" else _("Ikuti Windows")
        for code, label in (("system", follow), ("light", _("Terang")), ("dark", _("Gelap"))):
            m_theme.add_radiobutton(label=label, value=code, variable=self.var_theme, command=self._on_theme_menu)
        m_set.add_cascade(label=_("Tema"), menu=m_theme)
        m_set.add_separator()
        m_set.add_checkbutton(label=_("Cek update saat aplikasi dibuka"), variable=self.var_auto_update,
                              command=lambda: self._save_settings(None))
        if sendto.available():
            m_set.add_checkbutton(label=_("Menu klik kanan \"Send to\" di Explorer"), variable=self.var_sendto,
                                  command=self._on_sendto_menu)
        bar.add_cascade(label=_("Pengaturan"), menu=m_set)

        m_help = self._new_menu(bar)
        m_help.add_command(label=_("Cara pakai"), accelerator="F1", command=self.open_readme)
        m_help.add_command(label=_("Cek update..."), command=lambda: self.check_updates(manual=True))
        m_help.add_command(label=_("Halaman GitHub"), command=lambda: webbrowser.open(GITHUB_URL))
        m_help.add_separator()
        m_help.add_command(label=_("Tentang Collect Files Plus"), command=self.show_about)
        bar.add_cascade(label=_("Bantuan"), menu=m_help)

        if self.theme_name or not self.native_menus:
            for menu in (bar, m_file, m_set, m_lang, m_theme, m_help):
                theme.style_menu(menu, dark)
        self.menu_frame = None
        self.menu_buttons: List = []
        if self.native_menus:
            self.root.configure(menu=bar)
        else:
            self.menu_frame = ttk.Frame(self.root, padding=(self.px(4), self.px(2), self.px(4), 0))
            self.menu_frame.pack(side="top", fill="x")
            for label, menu in ((_("File"), m_file), (_("Pengaturan"), m_set), (_("Bantuan"), m_help)):
                button = ttk.Button(self.menu_frame, text=label, style="Toolbutton", takefocus=False)
                button.configure(command=lambda m=menu, b=button: self._post_menu(m, b))
                button.pack(side="left")
                self.menu_buttons.append((button, menu))
        self.menubar = bar

    @property
    def native_menus(self) -> bool:
        """macOS: menu sistem (sudah ikut mode gelap). Windows & Linux: menu bertema buatan sendiri."""
        return sys.platform == "darwin"

    def _new_menu(self, parent=None):
        if self.native_menus:
            return tk.Menu(parent if parent is not None else self.root, tearoff=0)
        return menus.FlyoutMenu(self.root, scale=self.scale, on_outside=self._menu_outside)

    def _post_menu(self, menu, button) -> None:
        """Buka menu drop-down tepat di bawah tombolnya (klik lagi: tutup)."""
        if getattr(menu, "is_open", False):
            menu.unpost()
            return
        for _b, other in self.menu_buttons:
            if other is not menu and getattr(other, "is_open", False):
                other.unpost()
        try:
            x, y = button.winfo_rootx(), button.winfo_rooty() + button.winfo_height()
            menu.tk_popup(x, y)
        except Exception:  # noqa: BLE001
            pass
        finally:
            try:
                menu.grab_release()
            except Exception:  # noqa: BLE001
                pass

    def _menu_outside(self, closed, x: int, y: int) -> bool:
        """Menu ditutup karena klik di luar. Kalau yang diklik tombol menu lain, buka menu itu."""
        try:
            widget = self.root.winfo_containing(x, y)
        except Exception:  # noqa: BLE001
            return False
        for button, menu in self.menu_buttons:
            if widget is button and menu is not closed:
                self.root.after_idle(lambda m=menu, b=button: self._post_menu(m, b))
                return True
        return False

    def _post_menu_key(self, index: int) -> str:
        if 0 <= index < len(self.menu_buttons):
            self._post_menu(self.menu_buttons[index][1], self.menu_buttons[index][0])
        return "break"

    def _bind_keys(self) -> None:
        r = self.root
        if sys.platform != "darwin":       # menu bar buatan sendiri: Alt+F / Alt+S / Alt+H, F10
            for i, key in enumerate(("f", "s", "h")):
                r.bind("<Alt-%s>" % key, lambda _e, n=i: self._post_menu_key(n))
                r.bind("<Alt-%s>" % key.upper(), lambda _e, n=i: self._post_menu_key(n))
            r.bind("<F10>", lambda _e: self._post_menu_key(0))
        r.bind("<Control-o>", lambda _e: self.choose_aep())
        r.bind("<F5>", lambda _e: self.start_analyze())
        r.bind("<Control-Return>", lambda _e: self.start_collect())
        r.bind("<F1>", lambda _e: self.open_readme())
        r.bind("<Escape>", lambda _e: self.cancel.set() if self.worker is not None and self.worker.is_alive() else None)
        if sys.platform == "darwin":
            r.bind("<Command-o>", lambda _e: self.choose_aep())
            r.bind("<Command-Return>", lambda _e: self.start_collect())

    def _bind_tree_actions(self) -> None:
        """Klik dua kali / klik kanan pada baris tabel."""
        for name, info in (("plugin", self.plugin_tree), ("font", self.font_tree), ("foot", self.foot_tree)):
            info.tree.bind("<Double-1>", lambda e, n=name, t=info.tree: self._reveal_row(n, t.identify_row(e.y)))
        self.batch_tree.tree.bind("<Double-1>", lambda e: self._batch_double(self.batch_tree.tree.identify_row(e.y)))
        self.batch_tree.tree.bind("<Button-2>" if sys.platform == "darwin" else "<Button-3>", self._batch_menu)

    def _message(self, kind: str, text: str) -> bool:
        """Kotak pesan (kind: showinfo / showwarning / showerror / askyesno). Dengan tema Sun Valley
        memakai jendela bertema (gelap/terang); tanpa tema memakai messagebox bawaan."""
        if self.theme_name:
            try:
                return bool(dialogs.show(self.root, APP_TITLE, text, kind, dark=self.theme_name == "dark",
                                         scale=self.scale))
            except tk.TclError:
                pass
        return bool(getattr(messagebox, kind)(APP_TITLE, text))

    def _reveal_row(self, kind: str, iid: str) -> None:
        path = self.row_paths.get(kind, {}).get(iid)
        if path is not None:
            reveal(path)

    def _set_tab_count(self, index: int, count: Optional[int]) -> None:
        try:
            base = self.tab_names[index]
            self.nb.tab(index, text=base if count is None else "%s (%d)" % (base, count))
        except Exception:  # noqa: BLE001
            pass

    def _update_comp_hint(self) -> None:
        """Petunjuk di tengah daftar comp selama daftarnya kosong."""
        if self.aep is None:
            text = _("Drag file .aep ke sini\natau klik \"Pilih...\" di atas")
        else:
            text = _("Project ini tidak punya comp.")
        self.comp_tree.set_empty_text(text)

    # ------------------------------------------------------- aksi

    def choose_aep(self) -> None:
        start = self.settings.get("aep_dir") or str(Path.home())
        path = filedialog.askopenfilename(title=_("Pilih project After Effects"), initialdir=start,
                                          filetypes=[(_("Project After Effects"), "*.aep"), (_("Semua file"), "*.*")])
        if path:
            self.var_aep.set(path)
            self.load_project()

    def choose_dest(self) -> None:
        start = self.var_dest.get() or self.settings.get("dest") or str(Path.home())
        path = filedialog.askdirectory(title=_("Pilih folder tujuan"), initialdir=start, mustexist=False)
        if path:
            self.var_dest.set(path)

    def load_project(self) -> None:
        path = self.var_aep.get().strip()
        if not path or not Path(path).is_file():
            self._message("showerror", _("File .aep tidak ditemukan."))
            return
        self.settings["aep_dir"] = str(Path(path).parent)
        if not self.var_dest.get().strip():
            self.var_dest.set(str(Path(path).parent))
        self.analysis = None
        self._run("load", self._job_load, path)

    def select_comps(self, mode: str) -> None:
        if not self.aep:
            return
        if mode == "rq":
            ids = set(self.rq_ids)
            if not ids:
                self._message("showinfo", _("Render Queue di project ini kosong."))
                return
        else:
            if self.active_id is None:
                self._message("showinfo", _("Tidak ada comp aktif yang tersimpan di project ini."))
                return
            ids = {self.active_id}
        for iid in self.comp_tree.checked:
            self.comp_tree.set(iid, int(iid) in ids)

    def current_options(self):
        opt = self._base_options()
        ids = [int(i) for i in self.comp_tree.checked_ids()]
        all_ids = [int(i) for i in self.comp_tree.tree.get_children()]
        opt.comp_ids = None if sorted(ids) == sorted(all_ids) else ids
        return opt

    def _base_options(self):
        """Opsi dari kotak centang di tab 1 (tanpa pilihan comp)."""
        from .collector import Options
        return Options(
            dest_dir=Path(self.var_dest.get().strip() or "."),
            comp_ids=None,
            collect_footage=self.opt_footage.get(),
            reduce_project=self.opt_reduce.get(),
            collect_fonts=self.opt_fonts.get(),
            collect_plugins=self.opt_plugins.get(),
            skip_disabled=self.opt_skip_off.get(),
            support_files=self.opt_support.get(),
            presets=self.opt_presets.get(),
        )

    @staticmethod
    def options_key(opt) -> tuple:
        return (tuple(sorted(opt.comp_ids)) if opt.comp_ids is not None else None,
                opt.collect_footage, opt.reduce_project, opt.collect_fonts, opt.collect_plugins,
                opt.skip_disabled, opt.support_files, opt.presets)

    def _validate_inputs(self, need_dest: bool) -> bool:
        if not self.aep:
            self._message("showwarning", _("Buka file .aep dulu."))
            return False
        if not self.comp_tree.checked_ids():
            self._message("showwarning", _("Centang minimal satu comp di tab \"1. Comp & opsi\"."))
            return False
        if need_dest and not self.var_dest.get().strip():
            self._message("showwarning", _("Pilih folder tujuan dulu."))
            return False
        return True

    def start_analyze(self) -> None:
        if self._on_batch_tab():
            self.start_batch_analyze()
            return
        if self._busy_now() or not self._validate_inputs(False):
            return
        opt = self.current_options()
        self._run("analyze", self._job_analyze, opt)

    def start_collect(self) -> None:
        if self._on_batch_tab():
            self.start_batch()
            return
        if self._busy_now() or not self._validate_inputs(True):
            return
        opt = self.current_options()
        self._save_settings(opt)
        if self.analysis is not None and self.analysis_key == self.options_key(opt):
            self._apply_plugin_checks()
            self.analysis.options.dest_dir = opt.dest_dir
            self._run("collect", self._job_collect, None)
        else:
            # opsi berubah sejak analisa terakhir: analisa ulang, centang plugin yang sudah diubah tetap dipakai
            self._run("collect", self._job_collect, (opt, self._plugin_choices()))

    def open_result(self) -> None:
        if self.last_folder is not None:
            open_folder(self.last_folder)

    def open_last_report(self) -> None:
        if self.last_report is not None and Path(self.last_report).is_file():
            open_folder(self.last_report)
        else:
            self._message("showinfo", _("Belum ada laporan. Jalankan Collect dulu."))

    def open_readme(self) -> None:
        path = docs_dir() / ("README_%s.txt" % get_language())
        if not path.is_file():
            path = docs_dir() / "README_en.txt"
        open_folder(path)

    def show_about(self) -> None:
        self._message("showinfo", _("Collect Files Plus %s\n\nKumpulkan footage, font, dan plugin yang dipakai "
                                         "project After Effects tanpa membuka After Effects.\n\nLisensi MIT\n%s")
                            % (__version__, GITHUB_URL))

    # ------------------------------------------------- bahasa & tema

    def _on_lang_menu(self) -> None:
        code = self.var_lang.get()
        self.root.after_idle(lambda: self.change_language(code))

    def change_language(self, code: str) -> None:
        if code == get_language() or code not in LANGS:
            return
        if self.worker is not None and self.worker.is_alive():
            self.var_lang.set(get_language())
            self.var_status.set(_("Tunggu proses yang sedang berjalan selesai dulu."))
            return
        set_language(code)
        self.var_lang.set(code)
        self.settings["lang"] = code
        save_settings(self.settings)
        self._apply_theme()                     # font Jepang + tinggi baris tabel
        self._rebuild()
        self.var_status.set(_("Bahasa diganti ke %s.") % LANGS[code])

    def _on_theme_menu(self) -> None:
        self.root.after_idle(self.change_theme)        # setelah menu tertutup (menu lama dibuang)

    def change_theme(self) -> None:
        """Pasang tema terang/gelap dan bangun ulang jendela (menu, tabel, warna) dengan tema itu."""
        if self.worker is not None and self.worker.is_alive():
            self.var_theme.set(self.settings.get("theme", "system"))
            self.var_status.set(_("Tunggu proses yang sedang berjalan selesai dulu."))
            return
        self._apply_theme()
        self._rebuild()
        self._sync_titlebar()
        self.settings["theme"] = self.var_theme.get()
        save_settings(self.settings)

    def _rebuild(self) -> None:
        """Bangun ulang semua widget dengan bahasa baru, data yang sudah ada tetap."""
        comp_checked = dict(self.comp_tree.checked)
        plugin_checked = dict(self.plugin_tree.checked)
        log_text = self.log.get("1.0", "end-1c")
        try:
            tab = self.nb.index(self.nb.select())
        except Exception:  # noqa: BLE001
            tab = 0
        old_menu = self.menubar
        for w in self._frames:
            w.destroy()
        self._build()
        try:
            old_menu.destroy()
        except Exception:  # noqa: BLE001
            pass
        if self.comp_rows:
            self._render_comps(comp_checked)
        if self.analysis is not None:
            self._fill_analysis(log=False)
            for iid, val in plugin_checked.items():
                self.plugin_tree.set(iid, val)
            self._update_plugin_total()
        self._refresh_batch()
        if self.batch_run is not None:
            for i, it in enumerate(self.batch_run.items):
                self.batch_tree.set_row(str(i), self._batch_values(it.path, it.scope, it.status_text, it.result_name),
                                        tags=(BATCH_TAG.get(it.status, "muted"),))
        if log_text:
            self._log(log_text, end="")
        self.nb.select(tab)
        self._sync_action_buttons()
        if self.update_info is not None and not self.update_dismissed:
            self._show_update_bar()

    # ------------------------------------------------- update

    def check_updates(self, manual: bool = False) -> None:
        """Cek rilis terbaru di GitHub di thread latar (tidak menahan jendela)."""
        kind = "manual" if manual else "auto"

        def job() -> None:
            try:
                self.events.put(("update-check", kind, (updater.check_latest(), "")))
            except Exception as exc:  # noqa: BLE001 - jaringan mati dsb.
                self.events.put(("update-check", kind, (None, str(exc) or type(exc).__name__)))

        if manual:
            self.var_status.set(_("Mengecek update..."))
        threading.Thread(target=job, daemon=True).start()

    def _on_update_check(self, manual: bool, info, error: str) -> None:
        if manual:
            self.var_status.set("")
        if error:
            if manual:
                self._message("showwarning", _("Tidak bisa mengecek update:\n%s") % error)
            return
        if info is None:
            if manual:
                self._message("showinfo", _("Belum ada rilis di GitHub."))
            return
        if info.newer:
            self.update_info = info
            self.update_dismissed = False
            self._show_update_bar()
        elif manual:
            self._message("showinfo", _("Kamu sudah memakai versi terbaru (%s).") % __version__)

    def _show_update_bar(self) -> None:
        info = self.update_info
        if info is None:
            return
        self.update_label.configure(text=_("Versi baru %s tersedia (kamu memakai %s).") % (info.version, __version__))
        mode = updater.update_mode(info)
        self.btn_update.configure(text=_("Update sekarang") if mode in ("zip", "msi") else _("Download"))
        self.update_bar.pack(fill="x", before=self._top)

    def hide_update_bar(self) -> None:
        self.update_dismissed = True
        self.update_bar.pack_forget()

    def open_release_page(self) -> None:
        webbrowser.open(self.update_info.page if self.update_info is not None else updater.RELEASES_PAGE)

    def start_update(self) -> None:
        info = self.update_info
        if info is None:
            return
        mode = updater.update_mode(info)
        if mode == "manual":
            self.open_release_page()          # macOS / dari source / folder tidak bisa ditulisi
            return
        if self._busy_now():
            return
        if mode == "msi":
            question = _("Download dan pasang versi %s sekarang?\n\nInstaller akan berjalan dan Windows mungkin "
                         "meminta izin (UAC). Aplikasi dibuka lagi setelah selesai.")
        else:
            question = _("Download dan pasang versi %s sekarang?\n\nAplikasi akan ditutup lalu dibuka lagi otomatis.")
        if not self._message("askyesno", question % info.version):
            return
        self._run("update", self._job_update, (info, mode), determinate=True)

    def _job_update(self, arg):
        import tempfile
        from .collector import Cancelled
        from .report import fmt_bytes
        info, mode = arg
        tmp = Path(tempfile.mkdtemp(prefix="CollectFilesPlus-update-"))
        last = [0]

        def prog(done: int, total: int) -> None:
            if done - last[0] >= (1 << 19) or done == total:
                last[0] = done
                self._progress(_("Mengunduh update: %s dari %s") % (fmt_bytes(done), fmt_bytes(total) if total else "?"))
                if total:
                    self.events.put(("fraction", "", done / total))
        try:
            path = updater.download(info, tmp, progress=prog, cancel=self.cancel, kind=mode)
        except updater.UpdateCancelled:
            raise Cancelled()
        self._progress(_("Menyiapkan update..."))
        if mode == "msi":
            return mode, tmp, path, info.version
        return mode, tmp, updater.extract_app(path, tmp / "baru"), info.version

    def _show_update_result(self, ok: bool, detail: str) -> None:
        if ok:
            self._message("showinfo", _("Update berhasil. Sekarang memakai versi %s.") % (detail or __version__))
        else:
            self._message("showwarning", _("Update gagal, versi lama tetap dipakai.\nCatatan: %s") % detail)

    # ------------------------------------------------- drag & drop, batch

    def _setup_dnd(self) -> bool:
        try:
            if not dnd.available() or not hasattr(self.root, "winfo_id"):
                return False
            # jangan panggil Tk dari callback drop: cukup masukkan ke antrean, diproses _poll
            return dnd.enable(self.root, lambda files: self.events.put(("drop", "", list(files)))) is not None
        except Exception:  # noqa: BLE001 - tanpa drag & drop aplikasi tetap jalan
            return False

    def _busy_now(self, quiet: bool = False) -> bool:
        if self.worker is not None and self.worker.is_alive():
            if not quiet:
                self.var_status.set(_("Tunggu proses yang sedang berjalan selesai dulu."))
            return True
        return False

    def _on_batch_tab(self) -> bool:
        try:
            return str(self.nb.select()) == str(self.batch_tab)
        except Exception:  # noqa: BLE001
            return False

    def on_drop(self, paths) -> None:
        """File/folder di-drop ke jendela (atau dikirim lewat ikon Dock di macOS)."""
        paths = [str(p) for p in paths if p]
        aeps = [p for p in paths if p.lower().endswith(".aep") and os.path.isfile(p)]
        dirs = [p for p in paths if os.path.isdir(p)]
        if not aeps and not dirs:
            self.var_status.set(_("Yang di-drop bukan file .aep atau folder."))
            return
        if self._busy_now():
            return
        if len(aeps) == 1 and not dirs and not self._on_batch_tab():
            self.var_aep.set(aeps[0])
            self.load_project()
        else:
            self.add_batch_paths(aeps + dirs)

    def _batch_values(self, path: Path, scope: str = "", status: Optional[str] = None, result: str = "") -> list:
        return [path.name, str(path.parent), scope, _("menunggu") if status is None else status, result]

    def _refresh_batch(self) -> None:
        self.batch_tree.clear()
        for i, p in enumerate(self.batch_paths):
            self.batch_tree.add(self._batch_values(p), iid=str(i), tags=("muted",))
        n = len(self.batch_paths)
        self.batch_count.configure(text=(_("%d project") % n) if n else "")
        self._set_tab_count(5, n or None)

    def add_batch_paths(self, paths) -> int:
        if self._busy_now():
            return 0
        from .batch import find_projects
        found = find_projects(paths)
        known = {os.path.normcase(os.path.abspath(str(p))) for p in self.batch_paths}
        new = [p for p in found if os.path.normcase(os.path.abspath(str(p))) not in known]
        self.batch_paths.extend(new)
        self.batch_run = None
        self._refresh_batch()
        self.nb.select(self.batch_tab)
        if not self.var_dest.get().strip() and self.batch_paths:
            try:
                self.var_dest.set(os.path.commonpath([str(p.parent) for p in self.batch_paths]))
            except ValueError:
                pass
        if not found:
            self.var_status.set(_("Tidak ada file .aep yang ditemukan."))
        else:
            self.var_status.set(_("%d project ditambahkan ke daftar batch (total %d).") % (len(new), len(self.batch_paths)))
        return len(new)

    def batch_add_files(self) -> None:
        start = self.settings.get("aep_dir") or str(Path.home())
        paths = filedialog.askopenfilenames(title=_("Pilih project After Effects (boleh banyak)"), initialdir=start,
                                            filetypes=[(_("Project After Effects"), "*.aep"), (_("Semua file"), "*.*")])
        if paths:
            self.settings["aep_dir"] = str(Path(paths[0]).parent)
            self.add_batch_paths(list(paths))

    def batch_add_folder(self) -> None:
        start = self.settings.get("aep_dir") or str(Path.home())
        path = filedialog.askdirectory(title=_("Pilih folder berisi project .aep"), initialdir=start, mustexist=True)
        if path:
            self.add_batch_paths([path])

    def batch_remove_selected(self) -> None:
        if self._busy_now():
            return
        sel = {int(i) for i in self.batch_tree.tree.selection()}
        self.batch_paths = [p for i, p in enumerate(self.batch_paths) if i not in sel]
        self.batch_run = None
        self._refresh_batch()

    def batch_clear(self) -> None:
        if self._busy_now():
            return
        self.batch_paths = []
        self.batch_run = None
        self._refresh_batch()

    def _batch_item(self, iid: str):
        """Hasil batch untuk baris ini (urutan baris = urutan project saat batch dijalankan)."""
        if self.batch_run is None or not iid:
            return None
        try:
            return self.batch_run.items[int(iid)]
        except (ValueError, IndexError):
            return None

    def batch_open(self, iid: str, report: bool = False) -> None:
        it = self._batch_item(iid)
        if it is None or it.result is None:
            return
        if report and it.result.report is not None:
            open_folder(it.result.report)
        else:
            open_folder(it.result.dest_root)

    def _batch_double(self, iid: str) -> None:
        """Klik dua kali: sudah di-collect -> buka folder hasil, belum -> lihat detail analisanya."""
        it = self._batch_item(iid)
        if it is not None and it.result is not None:
            self.batch_open(iid)
        elif iid:
            self.batch_show(iid)

    def batch_show(self, iid: str) -> None:
        """Buka project dari daftar batch di tab 1-5 dan analisa (comp dipilih sama seperti batch)."""
        try:
            path = self.batch_paths[int(iid)]
        except (ValueError, IndexError):
            return
        if self._busy_now():
            return
        self.analysis = None
        self._run("open-analyze", self._job_open_analyze, (path, self._base_options(), self.var_batch_scope.get()))

    def _batch_menu(self, event) -> None:
        iid = self.batch_tree.tree.identify_row(event.y)
        if not iid:
            return
        self.batch_tree.tree.selection_set([iid])
        it = self._batch_item(iid)
        state = "normal" if it is not None and it.result is not None else "disabled"
        if self.ctx_menu is None:
            self.ctx_menu = self._new_menu()
            if not self.native_menus:
                self.ctx_menu.on_outside = None
        menu = self.ctx_menu
        if self.theme_name or not self.native_menus:
            theme.style_menu(menu, self.theme_name == "dark")
        menu.delete(0, "end")
        menu.add_command(label=_("Lihat detail analisa"), command=lambda: self.batch_show(iid),
                         state="disabled" if self._busy_now(quiet=True) else "normal")
        menu.add_separator()
        menu.add_command(label=_("Buka folder hasil"), command=lambda: self.batch_open(iid), state=state)
        menu.add_command(label=_("Buka laporan"), command=lambda: self.batch_open(iid, report=True), state=state)
        menu.add_separator()
        menu.add_command(label=_("Hapus dari daftar"), command=self.batch_remove_selected)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def start_batch(self) -> None:
        if self._busy_now():
            return
        if not self.batch_paths:
            self._message("showwarning", _("Daftar batch masih kosong. Klik \"Tambah file .aep...\" atau "
                                                "drag file .aep ke jendela ini."))
            return
        if not self.var_dest.get().strip():
            self._message("showwarning", _("Pilih folder tujuan dulu."))
            return
        opt = self._base_options()
        self._save_settings(None)
        paths = list(self.batch_paths)
        for i, p in enumerate(paths):
            self.batch_tree.set_row(str(i), self._batch_values(p), tags=("muted",))
        self.batch_total = len(paths)
        self._run("batch", self._job_batch, (paths, opt, self.var_batch_scope.get()), determinate=True)

    def _job_batch(self, arg):
        from .batch import collect_many
        paths, opt, scope = arg
        return collect_many(paths, opt, scope, progress=self._progress, cancel=self.cancel,
                            on_item=self._batch_item_event)

    def _batch_item_event(self, i: int, it) -> None:
        self.events.put(("item", it.status, (i, self._batch_values(it.path, it.scope, it.status_text,
                                                                      it.result_name))))

    def start_batch_analyze(self) -> None:
        """Analisa semua project di daftar batch (tidak ada yang dicopy)."""
        if self._busy_now():
            return
        if not self.batch_paths:
            self._message("showwarning", _("Daftar batch masih kosong. Klik \"Tambah file .aep...\" atau "
                                                "drag file .aep ke jendela ini."))
            return
        opt = self._base_options()
        self._save_settings(None)
        paths = list(self.batch_paths)
        for i, p in enumerate(paths):
            self.batch_tree.set_row(str(i), self._batch_values(p), tags=("muted",))
        self.batch_total = len(paths)
        self._run("batch-analyze", self._job_batch_analyze, (paths, opt, self.var_batch_scope.get()),
                  determinate=True)

    def _job_batch_analyze(self, arg):
        from .batch import analyze_many
        paths, opt, scope = arg
        return analyze_many(paths, opt, scope, progress=self._progress, cancel=self.cancel,
                            on_item=self._batch_item_event)

    def _job_open_analyze(self, arg):
        import dataclasses

        from .batch import scope_parts
        from .collector import analyze
        from .project import AepProject
        path, base, scope = arg
        self._progress(_("Membaca %s ...") % Path(path).name)
        aep = AepProject(path)
        try:
            ids, _kind, _names, _n = scope_parts(aep, scope)
        except ValueError:
            ids = None
        if ids is not None and set(ids) == {c.id for c in aep.comps}:
            ids = None
        opt = dataclasses.replace(base, comp_ids=ids)
        an = analyze(aep, opt, progress=self._progress, cancel=self.cancel)
        return path, aep, an, self.options_key(opt)

    def _on_sendto_menu(self) -> None:
        want = self.var_sendto.get()
        try:
            if want:
                sendto.install()
                self._message("showinfo", _("Terpasang.\n\nCara pakai: di Explorer pilih satu atau banyak file "
                                                 ".aep (atau folder), klik kanan > Send to > Collect Files Plus.\n"
                                                 "Windows 11: klik \"Show more options\" dulu untuk melihat Send to.\n\n"
                                                 "Kalau folder aplikasi ini dipindah, pasang ulang dari sini."))
            else:
                sendto.uninstall()
                self._message("showinfo", _("Collect Files Plus sudah dihapus dari menu Send to."))
        except Exception as exc:  # noqa: BLE001
            self._message("showerror", _("Gagal: %s") % exc)
        self.var_sendto.set(sendto.installed())

    def on_close(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            if not self._message("askyesno", _("Proses masih berjalan. Hentikan dan tutup?")):
                return
            self.cancel.set()
        self._save_settings(None)
        self.root.destroy()

    # ------------------------------------------------- pekerjaan latar

    def _run(self, kind: str, fn, arg, determinate: bool = False) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        self.cancel.clear()
        self._busy(True, determinate)
        self.worker = threading.Thread(target=self._wrap, args=(kind, fn, arg), daemon=True)
        self.worker.start()

    def _wrap(self, kind: str, fn, arg) -> None:
        from .collector import Cancelled
        try:
            self.events.put(("done", kind, fn(arg)))
        except Cancelled:
            self.events.put(("cancelled", kind, None))
        except Exception as exc:  # noqa: BLE001
            self.events.put(("error", kind, "%s\n\n%s" % (exc, traceback.format_exc())))

    def _progress(self, msg: str) -> None:
        if self.cancel.is_set():
            from .collector import Cancelled
            raise Cancelled()
        self.events.put(("progress", "", msg))

    def _job_load(self, path: str):
        from .project import AepProject
        self._progress(_("Membaca %s ...") % Path(path).name)
        return AepProject(path)

    def _fresh_aep(self):
        """Project di memori sudah diubah collect sebelumnya (relink/reduce): baca ulang dulu."""
        if self.aep_stale:
            from .project import AepProject
            self._progress(_("Membaca %s ...") % self.aep.path.name)
            self.aep = AepProject(self.aep.path)
            self.aep_stale = False
        return self.aep

    def _job_analyze(self, opt):
        from .collector import analyze
        return analyze(self._fresh_aep(), opt, progress=self._progress, cancel=self.cancel), self.options_key(opt)

    def _job_collect(self, arg):
        from .collector import analyze, collect
        if arg is not None:
            # analisa ulang dengan opsi terbaru (tanpa review daftar plugin)
            opt, prev = arg
            self.analysis = analyze(self._fresh_aep(), opt, progress=self._progress, cancel=self.cancel)
            self.analysis_key = self.options_key(opt)
            for cd in self.analysis.candidates:
                if cd.label in prev:
                    cd.selected = prev[cd.label]
        res = collect(self.analysis, progress=self._progress, cancel=self.cancel)
        # project di memori sudah diubah (relink/reduce): dibaca ulang nanti, saat diperlukan.
        # Tabel tetap menampilkan analisa ini; Collect berikutnya menganalisa ulang (centang plugin tetap).
        self.aep_stale = True
        self.analysis_key = None
        return res

    def _poll(self) -> None:
        try:
            while True:
                ev, kind, payload = self.events.get_nowait()
                if ev == "progress":
                    self.var_status.set(payload)
                elif ev == "fraction":
                    self.progress.configure(value=max(0.0, min(100.0, payload * 100)))
                elif ev == "item":
                    i, values = payload
                    self.batch_tree.set_row(str(i), values, tags=(BATCH_TAG.get(kind, "muted"),))
                    if kind != "jalan" and self.batch_total:
                        self.progress.configure(value=100.0 * (i + 1) / self.batch_total)
                elif ev == "drop":
                    self.on_drop(payload)
                elif ev == "update-check":
                    info, error = payload
                    self._on_update_check(kind == "manual", info, error)
                elif ev == "error":
                    self._busy(False)
                    self._log("ERROR: " + payload)
                    first = payload.split("\n", 1)[0]
                    if kind in ("load", "open-analyze"):
                        self._message("showerror", _("File .aep tidak bisa dibaca:\n%s\n\n"
                                               "Kalau project dibuat dengan versi After Effects yang sangat baru, "
                                               "coba pakai script JSX (folder jsx) dari dalam After Effects.") % first)
                    else:
                        self._message("showerror", _("Terjadi error:\n%s\n\nDetail ada di tab Log.") % first)
                    self.var_status.set(_("Error."))
                elif ev == "cancelled":
                    self._busy(False)
                    self.var_status.set(_("Dibatalkan."))
                elif ev == "done":
                    self._busy(False)
                    self._done(kind, payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _busy(self, busy: bool, determinate: bool = False) -> None:
        self.is_busy = busy
        state = "disabled" if busy else "normal"
        self.btn_analyze.configure(state=state)
        self.btn_collect.configure(state=state)
        self._layout_bottom()                 # Batal + progress hanya tampil saat ada proses
        if busy and determinate:
            self.progress.configure(mode="determinate", value=0)
        elif busy:
            self.progress.configure(mode="indeterminate")
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)

    def _done(self, kind: str, payload) -> None:
        if kind == "update":
            mode, tmp, path, version = payload
            try:
                if mode == "msi":
                    updater.launch_msi(path, tmp, version)
                else:
                    updater.launch_apply(path, tmp, version)
            except Exception as exc:  # noqa: BLE001
                self._message("showerror", _("Gagal memulai update: %s") % exc)
                return
            self._save_settings(None)
            self.root.destroy()                 # skrip pemasang menunggu aplikasi tertutup
            return
        if kind == "load":
            self.aep = payload
            self.aep_stale = False
            self._fill_comps()
            self._update_comp_hint()
            for idx in (1, 2, 3, 4):
                self._set_tab_count(idx, None)
            self.var_status.set(_("Project terbaca: %d comp. Centang comp utama, lalu klik Analisa.") % len(self.aep.comps))
            self._log(_("Membuka %s") % self.aep.path)
            self.nb.select(0)
        elif kind == "analyze":
            self.analysis, self.analysis_key = payload
            self._fill_analysis()
            self.var_status.set(_("Analisa selesai. Cek tab Plugin/Font/Footage, lalu klik Collect."))
            self.nb.select(1 if self.analysis.candidates else 3)
        elif kind == "open-analyze":
            path, aep, an, key = payload
            self.var_aep.set(str(path))
            self.settings["aep_dir"] = str(Path(path).parent)
            self.aep, self.aep_stale = aep, False
            self._fill_comps(log=False)
            ids = an.options.comp_ids
            self._render_comps({str(cid): ids is None or cid in ids for cid, *_rest in self.comp_rows})
            self._update_comp_hint()
            self.analysis, self.analysis_key = an, key
            self._log(_("Membuka %s") % path)
            self._fill_analysis()
            self.var_status.set(_("Analisa selesai. Cek tab Plugin/Font/Footage, lalu klik Collect."))
            self.nb.select(1 if an.candidates else 3)
        elif kind == "batch-analyze":
            run = payload
            self.batch_run = run
            self._log(_("Analisa batch selesai: %s") % run.headline())
            for it in run.items:
                if it.status in ("catatan", "gagal"):
                    self._log("  %s: %s" % (it.path, it.status_text))
            self.var_status.set(_("Analisa selesai: %s. Klik kanan sebuah project untuk melihat detailnya.")
                                % run.headline())
        elif kind == "batch":
            run = payload
            self.batch_run = run
            self.last_folder = run.dest
            self.last_report = run.summary
            self._layout_bottom()
            msg = _("Batch selesai: %s\n\nFolder tujuan: %s") % (run.headline(), run.dest)
            if run.summary is not None:
                msg += _("\nRingkasan: %s") % run.summary.name
            self._log(msg)
            for it in run.items:
                if it.status == "gagal":
                    self._log(_("GAGAL %s: %s") % (it.path, it.error))
            self.var_status.set(_("Batch selesai: %s") % run.headline())
            if self._message("askyesno", msg + _("\n\nBuka folder tujuan?")):
                open_folder(run.dest)
        elif kind == "collect":
            self.result = payload
            self.last_folder = payload.dest_root
            self.last_report = payload.report
            self._layout_bottom()
            msg = _("Selesai.\n\nHasil: %s") % payload.dest_root
            if not payload.saved_ok:
                msg += _("\n\nPERHATIAN: %s\nPakai project di folder (Backup).") % payload.validation_error
            if payload.errors:
                msg += _("\n\n%d error, lihat laporan.") % len(payload.errors)
            self._log(msg)
            self.var_status.set(_("Selesai: %s") % payload.dest_root)
            if self._message("askyesno", msg + _("\n\nBuka folder hasil?")):
                open_folder(payload.dest_root)

    def _fill_comps(self, log: bool = True) -> None:
        """Baca daftar comp dari project yang baru dibuka (disimpan, dipakai lagi saat ganti bahasa)."""
        aep = self.aep
        self.rq_ids = {c.id for c in aep.rq_comps()}
        act = aep.active_comp()
        self.active_id = act.id if act is not None else None
        users = aep.precomp_users()
        mode, roots = aep.default_roots()
        default_ids = {c.id for c in roots}
        self.comp_rows = [(c.id, c.name, users.get(c.id, 0), c.id in default_ids) for c in aep.comps]
        self._render_comps()
        if log:
            note = {"rq": _("comp di Render Queue"), "active": _("comp aktif saat project disimpan"),
                    "all": _("semua comp")}[mode]
            self._log(_("Pilihan awal: %s.") % note)

    def _render_comps(self, checked: Optional[Dict[str, bool]] = None) -> None:
        self.comp_tree.clear()
        for cid, name, n_users, default in self.comp_rows:
            notes = []
            if cid in self.rq_ids:
                notes.append(_("Render Queue"))
            if cid == self.active_id:
                notes.append(_("comp aktif"))
            if n_users:
                notes.append(_("precomp di %d comp") % n_users)
            iid = str(cid)
            self.comp_tree.add(iid, name, ["; ".join(notes)],
                               checked=default if checked is None else checked.get(iid, default),
                               tags=("run",) if cid in self.rq_ids else ())

    def _fill_analysis(self, log: bool = True) -> None:
        from .plugins import how_label
        from .report import effect_status, effect_status_key, fmt_bytes

        an = self.analysis
        opt = an.options
        self.row_paths = {"plugin": {}, "font": {}, "foot": {}}
        self.plugin_tree.clear()
        for i, cd in enumerate(an.candidates):
            names = ", ".join(e.title for e in cd.effects)
            how = sorted({how_label(e.match.how) for e in cd.effects if e.match})
            tip = [str(cd.plugin.target), names + (_("  (+%d efek lain di file ini)") % cd.others if cd.others else ""),
                   "%s: %s" % (_("Cara ketemu"), "; ".join(how))]
            self.plugin_tree.add(str(i), cd.label, [names, fmt_bytes(cd.size), _("Pasti") if cd.strict else _("Perkiraan")],
                                 checked=cd.selected, tags=() if cd.strict else ("muted",), tip="\n".join(tip))
            self.row_paths["plugin"][str(i)] = cd.plugin.target
        missing_fx = [e for e in an.plugin_effects if e.candidate is None]
        for j, e in enumerate(missing_fx):
            self.plugin_tree.add("x%d" % j, _("TIDAK KETEMU: ") + e.title, [e.match_name, "", ""], checkable=False,
                                 tags=("error",))
        self._update_plugin_total()

        self.font_tree.clear()
        for f in an.fonts:
            status = {"ada": _("akan dicopy"), "adobe": _("Adobe Fonts (aktifkan di CC)"),
                      "tidak-ketemu": _("tidak terinstall di sini")}[f.status]
            tag = {"ada": (), "adobe": ("muted",), "tidak-ketemu": ("warn",)}[f.status]
            iid = self.font_tree.add([f.post_script_name, str(f.face.path) if f.face else "", status], tags=tag)
            if f.face is not None:
                self.row_paths["font"][iid] = f.face.path

        self.foot_tree.clear()
        for fe in an.footage:
            status = _("akan dicopy") if fe.exists else _("HILANG")
            if fe.is_sequence:
                status += _(" (sequence %d frame)") % len(fe.files)
            iid = self.foot_tree.add([", ".join(fe.names), str(fe.src), fmt_bytes(fe.size) if fe.exists else "", status],
                                     tags=() if fe.exists else ("error",))
            self.row_paths["foot"][iid] = fe.src

        self.fx_tree.clear()
        for e in an.effects:
            _tag, status = effect_status(e)
            key = effect_status_key(e)
            tag = {"not_found": ("error",), "copy_failed": ("error",), "guess": ("muted",), "unchecked": ("muted",),
                   "builtin": ("muted",)}.get(key, ())
            self.fx_tree.add([e.title, ", ".join(e.names), e.match_name, e.count, status], tags=tag)
        for e in an.disabled_only:
            self.fx_tree.add([e.title, ", ".join(e.names), e.match_name, e.count, _("dimatikan (dilewati)")],
                             tags=("muted",))

        def empty(enabled: bool, option: str, none: str) -> str:
            return _(none) if enabled else _("Tidak dicek: opsi \"%s\" dimatikan.") % _(option)
        self.plugin_tree.set_empty_text(empty(opt.collect_plugins, "Plugin", N_("Tidak ada plugin pihak ketiga.")))
        self.font_tree.set_empty_text(empty(opt.collect_fonts, "Font", N_("Tidak ada font.")))
        self.foot_tree.set_empty_text(empty(opt.collect_footage, "Footage", N_("Tidak ada footage.")))
        self.fx_tree.set_empty_text(_("Tidak ada efek."))
        self._set_tab_count(1, len(an.candidates) + len(missing_fx))
        self._set_tab_count(2, len(an.fonts))
        self._set_tab_count(3, len(an.footage))
        self._set_tab_count(4, len(an.effects) + len(an.disabled_only))
        if log:
            self._log(_("Analisa: %d efek (%d plugin pihak ketiga), %d file plugin, %d font, %d footage.") % (
                len(an.effects), len(an.plugin_effects), len(an.candidates), len(an.fonts), len(an.footage)))

    def _plugin_choices(self) -> Dict[str, bool]:
        if self.analysis is None:
            return {}
        return {cd.label: bool(self.plugin_tree.checked.get(str(i)))
                for i, cd in enumerate(self.analysis.candidates)}

    def _apply_plugin_checks(self) -> None:
        if self.analysis is None:
            return
        for i, cd in enumerate(self.analysis.candidates):
            cd.selected = bool(self.plugin_tree.checked.get(str(i)))

    def _update_plugin_total(self) -> None:
        if self.analysis is None:
            self.plugin_total.configure(text="")
            return
        from .report import fmt_bytes
        n = 0
        size = 0
        for i, cd in enumerate(self.analysis.candidates):
            if self.plugin_tree.checked.get(str(i)):
                n += 1
                size += cd.size
        self.plugin_total.configure(text=_("%d/%d dicentang · %s") % (n, len(self.analysis.candidates),
                                                                         fmt_bytes(size)))

    def _log(self, text: str, end: str = "\n") -> None:
        self.log.configure(state="normal")       # kotak Log hanya-baca untuk pengguna
        self.log.insert("end", text + end)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _save_settings(self, opt) -> None:
        s = self.settings
        s["dest"] = self.var_dest.get().strip()
        s["footage"] = self.opt_footage.get()
        s["reduce"] = self.opt_reduce.get()
        s["fonts"] = self.opt_fonts.get()
        s["plugins"] = self.opt_plugins.get()
        s["skip_disabled"] = self.opt_skip_off.get()
        s["support_files"] = self.opt_support.get()
        s["presets"] = self.opt_presets.get()
        s["batch_scope"] = self.var_batch_scope.get()
        s["check_updates"] = self.var_auto_update.get()
        s["theme"] = self.var_theme.get()
        try:
            zoomed = self.root.state() == "zoomed"
        except Exception:  # noqa: BLE001
            zoomed = False
        s["maximized"] = zoomed
        try:
            geom = self.root.geometry()
            if not zoomed and isinstance(geom, str) and re.match(r"^\d+x\d+", geom):
                s["geometry"] = geom
        except Exception:  # noqa: BLE001
            pass
        save_settings(s)


def main(initial: Optional[str] = None, batch: Optional[List[str]] = None) -> int:
    if sys.platform == "win32":
        try:  # tampilan tajam di layar high-DPI
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
    root = tk.Tk()
    app = App(root, initial, batch)
    if sys.platform == "darwin":
        def open_document(*paths):  # file .aep di-drop ke ikon aplikasi di Dock/Finder
            app.on_drop([str(p) for p in paths])
        try:
            root.createcommand("::tk::mac::OpenDocument", open_document)
        except Exception:  # noqa: BLE001
            pass
    close_ms = os.environ.get("COLLECT_FILES_PLUS_AUTOCLOSE_MS")  # dipakai uji build di CI
    if close_ms:
        root.after(int(close_ms), app.on_close)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
