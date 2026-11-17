"""Jendela aplikasi (tkinter)."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import traceback
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__, dnd, sendto, updater
from .i18n import LANGS, _, get_language, set_language, system_language

APP_TITLE = "Collect Files Plus"
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


class CheckTree(ttk.Frame):
    """Treeview dengan kotak centang di kolom pertama."""

    def __init__(self, master, columns, widths, height=12):
        super().__init__(master)
        self.tree = ttk.Treeview(self, columns=[c for c in columns[1:]], height=height, selectmode="extended")
        self.tree.heading("#0", text=columns[0], anchor="w")
        self.tree.column("#0", width=widths[0], anchor="w")
        for i, c in enumerate(columns[1:], start=1):
            self.tree.heading(c, text=c, anchor="w")
            self.tree.column(c, width=widths[i], anchor="w")
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

    def clear(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.checked.clear()
        self.labels.clear()
        self.checkable.clear()

    def add(self, iid: str, label: str, values=(), checked=False, checkable=True) -> None:
        self.labels[iid] = label
        self.checked[iid] = bool(checked)
        self.checkable[iid] = checkable
        self.tree.insert("", "end", iid=iid, text=self._text(iid), values=list(values))

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


class InfoTree(ttk.Frame):
    """Treeview biasa (tanpa centang)."""

    def __init__(self, master, columns, widths, height=12):
        super().__init__(master)
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=height)
        for c, w in zip(columns, widths):
            self.tree.heading(c, text=c, anchor="w")
            self.tree.column(c, width=w, anchor="w")
        ys = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def clear(self) -> None:
        self.tree.delete(*self.tree.get_children())

    def add(self, values, iid: Optional[str] = None) -> None:
        if iid is None:
            self.tree.insert("", "end", values=list(values))
        else:
            self.tree.insert("", "end", iid=iid, values=list(values))

    def set_row(self, iid: str, values) -> None:
        if iid in self.tree.get_children():
            self.tree.item(iid, values=list(values))


class App:
    def __init__(self, root: tk.Tk, initial: Optional[str] = None, batch: Optional[List[str]] = None):
        self.root = root
        self.settings = load_settings()
        # pemakai lama (settings sudah ada) tetap bahasa Indonesia; pemakai baru ikut bahasa sistem
        set_language(self.settings.get("lang") or ("id" if self.settings else system_language()))
        self.aep = None
        self.analysis = None
        self.analysis_key = None
        self.result = None
        self.events: "queue.Queue[tuple]" = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.cancel = threading.Event()
        self.batch_paths: List[Path] = []
        self.batch_run = None
        self.last_folder: Optional[Path] = None
        self.update_info = None
        self.update_dismissed = False

        self.scale = ui_scale(root)
        root.title("%s %s" % (APP_TITLE, __version__))
        root.geometry("%dx%d" % (self.px(1080), self.px(720)))
        root.minsize(self.px(900), self.px(600))
        try:  # baris tabel ikut membesar di layar high-DPI (Tk tidak melakukannya sendiri)
            ttk.Style(root).configure("Treeview", rowheight=self.px(20) + 2)
        except Exception:  # noqa: BLE001
            pass
        set_icon(root)

        self.var_aep = tk.StringVar(value=initial or "")
        self.var_dest = tk.StringVar(value=self.settings.get("dest", ""))
        self.var_status = tk.StringVar(value=_("Pilih file .aep untuk mulai."))
        s = self.settings
        self.opt_footage = tk.BooleanVar(value=s.get("footage", True))
        self.opt_reduce = tk.BooleanVar(value=s.get("reduce", False))
        self.opt_fonts = tk.BooleanVar(value=s.get("fonts", True))
        self.opt_plugins = tk.BooleanVar(value=s.get("plugins", True))
        self.opt_skip_off = tk.BooleanVar(value=s.get("skip_disabled", True))
        self.opt_support = tk.BooleanVar(value=s.get("support_files", False))
        self.opt_presets = tk.BooleanVar(value=s.get("presets", False))
        self.var_batch_scope = tk.StringVar(value=s.get("batch_scope", "auto"))

        self._build()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self._poll)
        self.dnd_ok = self._setup_dnd()
        self._show_hint()
        if initial:
            root.after(200, self.load_project)
        if batch:
            self.add_batch_paths(batch)
        result = updater.take_update_result()          # baru saja di-update oleh skrip pemasang?
        if result is not None:
            root.after(300, lambda: self._show_update_result(*result))
        if (self.settings.get("check_updates", True) and not os.environ.get(updater.NO_CHECK_ENV)
                and not os.environ.get("COLLECT_FILES_PLUS_AUTOCLOSE_MS")):
            root.after(1500, self.check_updates)

    # ------------------------------------------------------------ UI

    def px(self, n: float) -> int:
        return int(round(n * self.scale))

    def _w(self, *widths: int) -> List[int]:
        return [self.px(w) for w in widths]

    def _build(self) -> None:
        pad = {"padx": 6, "pady": 4}
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=(8, 2))
        self._top = top
        ttk.Label(top, text="Project (.aep)").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(top, textvariable=self.var_aep).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(top, text=_("Pilih..."), command=self.choose_aep).grid(row=0, column=2, **pad)
        langf = ttk.Frame(top)
        langf.grid(row=0, column=3, sticky="e", padx=(12, 4))
        ttk.Label(langf, text="Bahasa / Language").pack(side="left", padx=(0, 4))
        self.lang_box = ttk.Combobox(langf, values=list(LANGS.values()), state="readonly", width=17)
        self.lang_box.set(LANGS[get_language()])
        self.lang_box.bind("<<ComboboxSelected>>", self._on_lang_selected)
        self.lang_box.pack(side="left")
        ttk.Button(langf, text=_("Cek update"), command=lambda: self.check_updates(manual=True)).pack(
            side="left", padx=(8, 0))
        ttk.Label(top, text=_("Folder tujuan")).grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(top, textvariable=self.var_dest).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(top, text=_("Pilih..."), command=self.choose_dest).grid(row=1, column=2, **pad)
        self.hint = ttk.Label(top, text="")
        self.hint.grid(row=2, column=1, sticky="w", padx=6)
        top.columnconfigure(1, weight=1)

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=4)

        # Tab 1: comp + opsi
        tab1 = ttk.Frame(self.nb)
        self.nb.add(tab1, text=_("1. Comp & opsi"))
        left = ttk.Frame(tab1)
        left.pack(side="left", fill="both", expand=True, padx=(6, 3), pady=6)
        ttk.Label(left, text=_("Centang comp utama yang dipakai. Precomp di dalamnya ikut dibaca otomatis.")).pack(anchor="w")
        self.comp_tree = CheckTree(left, ["Comp", _("Keterangan")], self._w(360, 300), height=14)
        self.comp_tree.pack(fill="both", expand=True, pady=4)
        row = ttk.Frame(left)
        row.pack(fill="x")
        ttk.Button(row, text="Render Queue", command=lambda: self.select_comps("rq")).pack(side="left", padx=2)
        ttk.Button(row, text=_("Comp aktif"), command=lambda: self.select_comps("active")).pack(side="left", padx=2)
        ttk.Button(row, text=_("Semua"), command=lambda: self.comp_tree.set_all(True)).pack(side="left", padx=2)
        ttk.Button(row, text=_("Kosongkan"), command=lambda: self.comp_tree.set_all(False)).pack(side="left", padx=2)

        right = ttk.LabelFrame(tab1, text=_("Yang dikumpulkan"))
        right.pack(side="left", fill="y", padx=(3, 6), pady=6)
        opts = [
            (self.opt_footage, _("Footage (copy + relink ke folder (Footage))")),
            (self.opt_reduce, _("Buang comp & footage yang tidak dipakai\n(Reduce Project)")),
            (self.opt_fonts, _("Font yang dipakai text layer")),
            (self.opt_plugins, _("Plugin pihak ketiga\n(hanya file plugin yang efeknya dipakai)")),
            (self.opt_skip_off, _("Lewati efek yang dimatikan (ikon fx mati)")),
            (self.opt_support, _("Ikut file pendukung plugin\n(DLL/data di folder yang sama)")),
            (self.opt_presets, _("Ikut animation preset (.ffx) yang\nnamanya sama dengan efek yang di-rename")),
        ]
        for var, text in opts:
            ttk.Checkbutton(right, text=text, variable=var).pack(anchor="w", padx=8, pady=3)

        # Tab 2: plugin
        tab2 = ttk.Frame(self.nb)
        self.nb.add(tab2, text=_("2. Plugin"))
        ttk.Label(tab2, text=_("File plugin yang akan dicopy. Klik kotak centang untuk memilih. "
                               "\"(perkiraan)\" = tidak dicentang otomatis.")).pack(anchor="w", padx=6, pady=(6, 0))
        self.plugin_tree = CheckTree(tab2, [_("File plugin"), _("Efek yang dipakai"), _("Ukuran"), _("Cara ketemu")],
                                     self._w(360, 330, 80, 220), height=14)
        self.plugin_tree.pack(fill="both", expand=True, padx=6, pady=4)
        self.plugin_tree.on_change = self._update_plugin_total
        row2 = ttk.Frame(tab2)
        row2.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(row2, text=_("Centang semua"), command=lambda: self.plugin_tree.set_all(True)).pack(side="left", padx=2)
        ttk.Button(row2, text=_("Hapus semua centang"), command=lambda: self.plugin_tree.set_all(False)).pack(side="left", padx=2)
        self.plugin_total = ttk.Label(row2, text="")
        self.plugin_total.pack(side="left", padx=12)

        # Tab 3-5: font, footage, efek
        tab3 = ttk.Frame(self.nb)
        self.nb.add(tab3, text=_("3. Font"))
        self.font_tree = InfoTree(tab3, [_("Font (PostScript)"), _("File"), _("Status")], self._w(260, 520, 200))
        self.font_tree.pack(fill="both", expand=True, padx=6, pady=6)

        tab4 = ttk.Frame(self.nb)
        self.nb.add(tab4, text="4. Footage")
        self.foot_tree = InfoTree(tab4, [_("Item"), _("File"), _("Ukuran"), _("Status")], self._w(260, 520, 80, 140))
        self.foot_tree.pack(fill="both", expand=True, padx=6, pady=6)

        tab5 = ttk.Frame(self.nb)
        self.nb.add(tab5, text=_("5. Semua efek"))
        self.fx_tree = InfoTree(tab5, [_("Efek"), _("Nama di layer"), _("Match name"), _("Jenis"), _("Dipakai"), _("Status")],
                                self._w(200, 200, 200, 150, 70, 180))
        self.fx_tree.pack(fill="both", expand=True, padx=6, pady=6)

        # Tab batch: banyak project sekaligus
        tabb = ttk.Frame(self.nb)
        self.nb.add(tabb, text=_("Batch (banyak project)"))
        self.batch_tab = tabb
        ttk.Label(tabb, text=_("Collect banyak project sekaligus. Semua hasil masuk ke \"Folder tujuan\" di atas, "
                               "tiap project ke folder <nama>_Collected sendiri.\nOpsi yang dicentang di tab "
                               "\"1. Comp & opsi\" dipakai untuk semua project. File .aep atau folder juga bisa "
                               "di-drag ke jendela ini."), justify="left").pack(anchor="w", padx=6, pady=(6, 0))
        self.batch_tree = InfoTree(tabb, [_("Project"), _("Lokasi"), _("Comp"), _("Status"), _("Hasil")],
                                   self._w(200, 300, 200, 300, 200))
        self.batch_tree.pack(fill="both", expand=True, padx=6, pady=4)
        rb = ttk.Frame(tabb)
        rb.pack(fill="x", padx=6)
        ttk.Button(rb, text=_("Tambah file .aep..."), command=self.batch_add_files).pack(side="left", padx=2)
        ttk.Button(rb, text=_("Tambah folder..."), command=self.batch_add_folder).pack(side="left", padx=2)
        ttk.Button(rb, text=_("Hapus yang dipilih"), command=self.batch_remove_selected).pack(side="left", padx=2)
        ttk.Button(rb, text=_("Kosongkan"), command=self.batch_clear).pack(side="left", padx=2)
        self.batch_count = ttk.Label(rb, text="")
        self.batch_count.pack(side="left", padx=12)
        rs = ttk.Frame(tabb)
        rs.pack(fill="x", padx=6, pady=(6, 0))
        ttk.Label(rs, text=_("Comp yang dibaca:")).pack(side="left", padx=2)
        ttk.Radiobutton(rs, text=_("Otomatis (Render Queue, kalau kosong comp aktif, kalau tidak ada semua comp)"),
                        value="auto", variable=self.var_batch_scope).pack(side="left", padx=4)
        ttk.Radiobutton(rs, text=_("Semua comp"), value="all", variable=self.var_batch_scope).pack(side="left", padx=4)
        rc = ttk.Frame(tabb)
        rc.pack(fill="x", padx=6, pady=6)
        self.btn_batch = ttk.Button(rc, text=_("Collect semua project"), command=self.start_batch)
        self.btn_batch.pack(side="left", padx=2)
        self.btn_sendto = None
        if sendto.available():
            self.btn_sendto = ttk.Button(rc, text=self._sendto_label(), command=self.toggle_sendto)
            self.btn_sendto.pack(side="right", padx=2)

        tab6 = ttk.Frame(self.nb)
        self.nb.add(tab6, text="Log")
        self.log = tk.Text(tab6, height=10, wrap="word")
        self.log.pack(fill="both", expand=True, padx=6, pady=6)

        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=8, pady=(2, 8))
        self.btn_analyze = ttk.Button(bottom, text=_("Analisa"), command=self.start_analyze)
        self.btn_analyze.pack(side="left", padx=2)
        self.btn_collect = ttk.Button(bottom, text="Collect", command=self.start_collect)
        self.btn_collect.pack(side="left", padx=2)
        self.btn_cancel = ttk.Button(bottom, text=_("Batal"), command=self.cancel.set, state="disabled")
        self.btn_cancel.pack(side="left", padx=2)
        self.btn_open = ttk.Button(bottom, text=_("Buka folder hasil"), command=self.open_result, state="disabled")
        self.btn_open.pack(side="right", padx=2)
        self.progress = ttk.Progressbar(bottom, mode="indeterminate", length=self.px(160))
        self.progress.pack(side="left", padx=8)
        ttk.Label(bottom, textvariable=self.var_status).pack(side="left", padx=4, fill="x", expand=True)
        # bar pemberitahuan update (ditampilkan kalau ada versi baru)
        self.update_bar = ttk.Frame(self.root)
        self.update_label = ttk.Label(self.update_bar, text="")
        self.update_label.pack(side="left", padx=(4, 10))
        self.btn_update = ttk.Button(self.update_bar, text=_("Update sekarang"), command=self.start_update)
        self.btn_update.pack(side="left", padx=2)
        ttk.Button(self.update_bar, text=_("Lihat perubahan"), command=self.open_release_page).pack(side="left", padx=2)
        ttk.Button(self.update_bar, text=_("Tutup"), command=self.hide_update_bar).pack(side="left", padx=2)
        self._frames = [self.update_bar, top, self.nb, bottom]

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
            messagebox.showerror(APP_TITLE, _("File .aep tidak ditemukan."))
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
            ids = {c.id for c in self.aep.rq_comps()}
            if not ids:
                messagebox.showinfo(APP_TITLE, _("Render Queue di project ini kosong."))
                return
        else:
            act = self.aep.active_comp()
            if act is None:
                messagebox.showinfo(APP_TITLE, _("Tidak ada comp aktif yang tersimpan di project ini."))
                return
            ids = {act.id}
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
            messagebox.showwarning(APP_TITLE, _("Buka file .aep dulu."))
            return False
        if not self.comp_tree.checked_ids():
            messagebox.showwarning(APP_TITLE, _("Centang minimal satu comp di tab \"1. Comp & opsi\"."))
            return False
        if need_dest and not self.var_dest.get().strip():
            messagebox.showwarning(APP_TITLE, _("Pilih folder tujuan dulu."))
            return False
        return True

    def start_analyze(self) -> None:
        if not self._validate_inputs(False):
            return
        opt = self.current_options()
        self._run("analyze", self._job_analyze, opt)

    def start_collect(self) -> None:
        if not self._validate_inputs(True):
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

    # ------------------------------------------------- bahasa

    def _show_hint(self) -> None:
        if self.dnd_ok:
            self.hint.configure(text=_("Tip: drag file .aep ke jendela ini. Banyak file atau folder sekaligus "
                                       "masuk ke tab Batch."))

    def _on_lang_selected(self, _event=None) -> None:
        names = {v: k for k, v in LANGS.items()}
        self.change_language(names.get(self.lang_box.get(), "id"))

    def change_language(self, code: str) -> None:
        if code == get_language() or code not in LANGS:
            return
        if self.worker is not None and self.worker.is_alive():
            self.lang_box.set(LANGS[get_language()])
            self.var_status.set(_("Tunggu proses yang sedang berjalan selesai dulu."))
            return
        set_language(code)
        self.settings["lang"] = code
        save_settings(self.settings)
        self._rebuild()
        self.var_status.set(_("Bahasa diganti ke %s.") % LANGS[code])

    def _rebuild(self) -> None:
        """Bangun ulang semua widget dengan bahasa baru, data yang sudah ada tetap."""
        comp_checked = dict(self.comp_tree.checked)
        plugin_checked = dict(self.plugin_tree.checked)
        log_text = self.log.get("1.0", "end-1c")
        try:
            tab = self.nb.index(self.nb.select())
        except Exception:  # noqa: BLE001
            tab = 0
        for w in self._frames:
            w.destroy()
        self._build()
        if self.aep is not None:
            self._fill_comps(log=False)
            for iid, val in comp_checked.items():
                self.comp_tree.set(iid, val)
        if self.analysis is not None:
            self._fill_analysis(log=False)
            for iid, val in plugin_checked.items():
                self.plugin_tree.set(iid, val)
            self._update_plugin_total()
        self._refresh_batch()
        if self.batch_run is not None:
            done = {os.path.normcase(str(it.path)): it for it in self.batch_run.items}
            for i, p in enumerate(self.batch_paths):
                it = done.get(os.path.normcase(str(p)))
                if it is not None:
                    self.batch_tree.set_row(str(i), self._batch_values(it.path, it.scope, it.status_text,
                                                                       it.result_name))
        if log_text:
            self.log.insert("end", log_text)
        self.nb.select(tab)
        if self.last_folder is not None:
            self.btn_open.configure(state="normal")
        self._show_hint()
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
                messagebox.showwarning(APP_TITLE, _("Tidak bisa mengecek update:\n%s") % error)
            return
        if info is None:
            if manual:
                messagebox.showinfo(APP_TITLE, _("Belum ada rilis di GitHub."))
            return
        if info.newer:
            self.update_info = info
            self.update_dismissed = False
            self._show_update_bar()
        elif manual:
            messagebox.showinfo(APP_TITLE, _("Kamu sudah memakai versi terbaru (%s).") % __version__)

    def _show_update_bar(self) -> None:
        info = self.update_info
        if info is None:
            return
        self.update_label.configure(text=_("Versi baru %s tersedia (kamu memakai %s).") % (info.version, __version__))
        self.btn_update.configure(text=_("Update sekarang") if updater.can_self_update() and info.asset_url
                                  else _("Download"))
        self.update_bar.pack(fill="x", padx=8, pady=(8, 0), before=self._top)

    def hide_update_bar(self) -> None:
        self.update_dismissed = True
        self.update_bar.pack_forget()

    def open_release_page(self) -> None:
        webbrowser.open(self.update_info.page if self.update_info is not None else updater.RELEASES_PAGE)

    def start_update(self) -> None:
        info = self.update_info
        if info is None:
            return
        if not (updater.can_self_update() and info.asset_url):
            self.open_release_page()          # macOS / dari source / folder tidak bisa ditulisi
            return
        if self._busy_now():
            return
        if not messagebox.askyesno(APP_TITLE, _("Download dan pasang versi %s sekarang?\n\nAplikasi akan ditutup "
                                                "lalu dibuka lagi otomatis.") % info.version):
            return
        self._run("update", self._job_update, info)

    def _job_update(self, info):
        import tempfile
        from .collector import Cancelled
        from .report import fmt_bytes
        tmp = Path(tempfile.mkdtemp(prefix="CollectFilesPlus-update-"))
        last = [0]

        def prog(done: int, total: int) -> None:
            if done - last[0] >= (1 << 19) or done == total:
                last[0] = done
                self._progress(_("Mengunduh update: %s dari %s") % (fmt_bytes(done), fmt_bytes(total) if total else "?"))
        try:
            zip_path = updater.download(info, tmp, progress=prog, cancel=self.cancel)
        except updater.UpdateCancelled:
            raise Cancelled()
        self._progress(_("Menyiapkan update..."))
        return tmp, updater.extract_app(zip_path, tmp / "baru"), info.version

    def _show_update_result(self, ok: bool, detail: str) -> None:
        if ok:
            messagebox.showinfo(APP_TITLE, _("Update berhasil. Sekarang memakai versi %s.") % (detail or __version__))
        else:
            messagebox.showwarning(APP_TITLE, _("Update gagal, versi lama tetap dipakai.\nCatatan: %s") % detail)

    # ------------------------------------------------- drag & drop, batch

    def _setup_dnd(self) -> bool:
        try:
            if not dnd.available() or not hasattr(self.root, "winfo_id"):
                return False
            # jangan panggil Tk dari callback drop: cukup masukkan ke antrean, diproses _poll
            return dnd.enable(self.root, lambda files: self.events.put(("drop", "", list(files)))) is not None
        except Exception:  # noqa: BLE001 - tanpa drag & drop aplikasi tetap jalan
            return False

    def _busy_now(self) -> bool:
        if self.worker is not None and self.worker.is_alive():
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
            self.batch_tree.add(self._batch_values(p), iid=str(i))
        n = len(self.batch_paths)
        self.batch_count.configure(text=(_("%d project") % n) if n else "")

    def add_batch_paths(self, paths) -> int:
        if self._busy_now():
            return 0
        from .batch import find_projects
        found = find_projects(paths)
        known = {os.path.normcase(os.path.abspath(str(p))) for p in self.batch_paths}
        new = [p for p in found if os.path.normcase(os.path.abspath(str(p))) not in known]
        self.batch_paths.extend(new)
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
        self._refresh_batch()

    def batch_clear(self) -> None:
        if self._busy_now():
            return
        self.batch_paths = []
        self._refresh_batch()

    def start_batch(self) -> None:
        if self._busy_now():
            return
        if not self.batch_paths:
            messagebox.showwarning(APP_TITLE, _("Daftar batch masih kosong. Klik \"Tambah file .aep...\" atau "
                                                "drag file .aep ke jendela ini."))
            return
        if not self.var_dest.get().strip():
            messagebox.showwarning(APP_TITLE, _("Pilih folder tujuan dulu."))
            return
        opt = self._base_options()
        self._save_settings(None)
        paths = list(self.batch_paths)
        for i, p in enumerate(paths):
            self.batch_tree.set_row(str(i), self._batch_values(p))
        self._run("batch", self._job_batch, (paths, opt, self.var_batch_scope.get()))

    def _job_batch(self, arg):
        from .batch import collect_many
        paths, opt, scope = arg

        def on_item(i, it) -> None:
            self.events.put(("item", "batch", (i, self._batch_values(it.path, it.scope, it.status_text,
                                                                      it.result_name))))
        return collect_many(paths, opt, scope, progress=self._progress, cancel=self.cancel, on_item=on_item)

    def _sendto_label(self) -> str:
        return (_("Hapus dari menu klik kanan \"Send to\"") if sendto.installed()
                else _("Pasang di menu klik kanan \"Send to\""))

    def toggle_sendto(self) -> None:
        try:
            if sendto.installed():
                sendto.uninstall()
                messagebox.showinfo(APP_TITLE, _("Collect Files Plus sudah dihapus dari menu Send to."))
            else:
                sendto.install()
                messagebox.showinfo(APP_TITLE, _("Terpasang.\n\nCara pakai: di Explorer pilih satu atau banyak file "
                                                 ".aep (atau folder), klik kanan > Send to > Collect Files Plus.\n"
                                                 "Windows 11: klik \"Show more options\" dulu untuk melihat Send to.\n\n"
                                                 "Kalau folder aplikasi ini dipindah, pasang ulang dari sini."))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, _("Gagal: %s") % exc)
        if self.btn_sendto is not None:
            self.btn_sendto.configure(text=self._sendto_label())

    def on_close(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            if not messagebox.askyesno(APP_TITLE, _("Proses masih berjalan. Hentikan dan tutup?")):
                return
            self.cancel.set()
        self._save_settings(None)
        self.root.destroy()

    # ------------------------------------------------- pekerjaan latar

    def _run(self, kind: str, fn, arg) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        self.cancel.clear()
        self._busy(True)
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

    def _job_analyze(self, opt):
        from .collector import analyze
        return analyze(self.aep, opt, progress=self._progress, cancel=self.cancel), self.options_key(opt)

    def _job_collect(self, arg):
        from .collector import analyze, collect
        if arg is not None:
            # analisa ulang dengan opsi terbaru (tanpa review daftar plugin)
            opt, prev = arg
            self.analysis = analyze(self.aep, opt, progress=self._progress, cancel=self.cancel)
            self.analysis_key = self.options_key(opt)
            for cd in self.analysis.candidates:
                if cd.label in prev:
                    cd.selected = prev[cd.label]
        res = collect(self.analysis, progress=self._progress, cancel=self.cancel)
        # project di memori sudah diubah (relink/reduce): baca ulang untuk proses berikutnya
        from .project import AepProject
        self.aep = AepProject(self.aep.path)
        self.analysis = None
        self.analysis_key = None
        return res

    def _poll(self) -> None:
        try:
            while True:
                ev, kind, payload = self.events.get_nowait()
                if ev == "progress":
                    self.var_status.set(payload)
                elif ev == "item":
                    i, values = payload
                    self.batch_tree.set_row(str(i), values)
                elif ev == "drop":
                    self.on_drop(payload)
                elif ev == "update-check":
                    info, error = payload
                    self._on_update_check(kind == "manual", info, error)
                elif ev == "error":
                    self._busy(False)
                    self._log("ERROR: " + payload)
                    first = payload.split("\n", 1)[0]
                    if kind == "load":
                        messagebox.showerror(APP_TITLE, _("File .aep tidak bisa dibaca:\n%s\n\n"
                                               "Kalau project dibuat dengan versi After Effects yang sangat baru, "
                                               "coba pakai script JSX (folder jsx) dari dalam After Effects.") % first)
                    else:
                        messagebox.showerror(APP_TITLE, _("Terjadi error:\n%s\n\nDetail ada di tab Log.") % first)
                    self.var_status.set("Error.")
                elif ev == "cancelled":
                    self._busy(False)
                    self.var_status.set(_("Dibatalkan."))
                elif ev == "done":
                    self._busy(False)
                    self._done(kind, payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.btn_analyze.configure(state=state)
        self.btn_collect.configure(state=state)
        self.btn_batch.configure(state=state)
        self.btn_cancel.configure(state="normal" if busy else "disabled")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _done(self, kind: str, payload) -> None:
        if kind == "update":
            tmp, new_dir, version = payload
            try:
                updater.launch_apply(new_dir, tmp, version)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(APP_TITLE, _("Gagal memulai update: %s") % exc)
                return
            self._save_settings(None)
            self.root.destroy()                 # skrip pemasang menunggu aplikasi tertutup
            return
        if kind == "load":
            self.aep = payload
            self._fill_comps()
            self.var_status.set(_("Project terbaca: %d comp. Centang comp utama, lalu klik Analisa.") % len(self.aep.comps))
            self._log(_("Membuka %s") % self.aep.path)
        elif kind == "analyze":
            self.analysis, self.analysis_key = payload
            self._fill_analysis()
            self.var_status.set(_("Analisa selesai. Cek tab Plugin/Font/Footage, lalu klik Collect."))
            self.nb.select(1 if self.analysis.candidates else 3)
        elif kind == "batch":
            run = payload
            self.batch_run = run
            self.last_folder = run.dest
            self.btn_open.configure(state="normal")
            msg = _("Batch selesai: %s\n\nFolder tujuan: %s") % (run.headline(), run.dest)
            if run.summary is not None:
                msg += _("\nRingkasan: %s") % run.summary.name
            self._log(msg)
            for it in run.items:
                if it.status == "gagal":
                    self._log(_("GAGAL %s: %s") % (it.path, it.error))
            self.var_status.set(_("Batch selesai: %s") % run.headline())
            if messagebox.askyesno(APP_TITLE, msg + _("\n\nBuka folder tujuan?")):
                open_folder(run.dest)
        elif kind == "collect":
            self.result = payload
            self.last_folder = payload.dest_root
            self.btn_open.configure(state="normal")
            msg = _("Selesai.\n\nHasil: %s") % payload.dest_root
            if not payload.saved_ok:
                msg += _("\n\nPERHATIAN: %s\nPakai project di folder (Backup).") % payload.validation_error
            if payload.errors:
                msg += _("\n\n%d error, lihat laporan.") % len(payload.errors)
            self._log(msg)
            self.var_status.set(_("Selesai: %s") % payload.dest_root)
            if messagebox.askyesno(APP_TITLE, msg + _("\n\nBuka folder hasil?")):
                open_folder(payload.dest_root)

    def _fill_comps(self, log: bool = True) -> None:
        self.comp_tree.clear()
        rq = {c.id for c in self.aep.rq_comps()}
        act = self.aep.active_comp()
        users = self.aep.precomp_users()
        mode, roots = self.aep.default_roots()
        default_ids = {c.id for c in roots}
        for c in self.aep.comps:
            tags = []
            if c.id in rq:
                tags.append("Render Queue")
            if act is not None and c.id == act.id:
                tags.append(_("comp aktif"))
            if users.get(c.id):
                tags.append(_("precomp di %d comp") % users[c.id])
            self.comp_tree.add(str(c.id), c.name, ["; ".join(tags)], checked=c.id in default_ids)
        if log:
            note = {"rq": _("comp di Render Queue"), "active": _("comp aktif saat project disimpan"),
                    "all": _("semua comp")}[mode]
            self._log(_("Pilihan awal: %s.") % note)

    def _fill_analysis(self, log: bool = True) -> None:
        from .plugins import how_label
        from .report import effect_status, fmt_bytes, kind_label

        an = self.analysis
        self.plugin_tree.clear()
        for i, cd in enumerate(an.candidates):
            names = ", ".join(e.title for e in cd.effects)
            if cd.others:
                names += _("  (+%d efek lain di file ini)") % cd.others
            how = sorted({how_label(e.match.how) for e in cd.effects if e.match})
            label = ("" if cd.strict else _("(perkiraan) ")) + cd.label
            self.plugin_tree.add(str(i), label, [names, fmt_bytes(cd.size), "; ".join(how)], checked=cd.selected)
        for j, e in enumerate([e for e in an.plugin_effects if e.candidate is None]):
            self.plugin_tree.add("x%d" % j, _("TIDAK KETEMU: ") + e.title, [e.match_name, "", ""], checkable=False)
        self._update_plugin_total()

        self.font_tree.clear()
        for f in an.fonts:
            status = {"ada": _("akan dicopy"), "adobe": _("Adobe Fonts (aktifkan di CC)"),
                      "tidak-ketemu": _("tidak terinstall di sini")}[f.status]
            self.font_tree.add([f.post_script_name, str(f.face.path) if f.face else "", status])

        self.foot_tree.clear()
        for fe in an.footage:
            status = _("akan dicopy") if fe.exists else _("HILANG")
            if fe.is_sequence:
                status += _(" (sequence %d frame)") % len(fe.files)
            self.foot_tree.add([", ".join(fe.names), str(fe.src), fmt_bytes(fe.size) if fe.exists else "", status])

        self.fx_tree.clear()
        for e in an.effects:
            _tag, status = effect_status(e)
            self.fx_tree.add([e.title, ", ".join(e.names), e.match_name, kind_label(e.kind), e.count, status])
        for e in an.disabled_only:
            self.fx_tree.add([e.title, ", ".join(e.names), e.match_name, kind_label(e.kind), e.count,
                              _("dimatikan (dilewati)")])
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
        self.plugin_total.configure(text=_("%d dari %d file plugin dicentang, total %s") % (
            n, len(self.analysis.candidates), fmt_bytes(size)))

    def _log(self, text: str) -> None:
        self.log.insert("end", text + "\n")
        self.log.see("end")

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
