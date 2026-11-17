"""tkinter tiruan untuk menguji logika GUI tanpa layar (dan tanpa Tk)."""

from __future__ import annotations

import sys
import types


def build():
    tk = types.ModuleType("tkinter")
    ttk = types.ModuleType("tkinter.ttk")
    filedialog = types.ModuleType("tkinter.filedialog")
    messagebox = types.ModuleType("tkinter.messagebox")

    class Var:
        def __init__(self, master=None, value=None):
            self._v = value

        def get(self):
            return self._v

        def set(self, v):
            self._v = v

    class Widget:
        def __init__(self, master=None, **kw):
            self.master = master
            self.kw = dict(kw)
            self.children_list = []
            if master is not None and hasattr(master, "children_list"):
                master.children_list.append(self)

        def pack(self, **kw):
            self.packed = True

        def pack_forget(self):
            self.packed = False

        def destroy(self):
            self.destroyed = True
            if self.master is not None and self in getattr(self.master, "children_list", []):
                self.master.children_list.remove(self)

        def all_texts(self):
            """Semua teks yang tampil di widget ini dan anak-anaknya (untuk uji bahasa)."""
            out = []
            for key in ("text", "title"):
                if isinstance(self.kw.get(key), str):
                    out.append(self.kw[key])
            out.extend(getattr(self, "extra_texts", lambda: [])())
            for c in self.children_list:
                out.extend(c.all_texts())
            return out

        def grid(self, **kw):
            pass

        def columnconfigure(self, *a, **kw):
            pass

        def rowconfigure(self, *a, **kw):
            pass

        def bind(self, *a, **kw):
            pass

        def configure(self, **kw):
            self.kw.update(kw)

        config = configure

        def cget(self, key):
            return self.kw.get(key)

    class Tk(Widget):
        dpi = 96.0

        def __init__(self):
            super().__init__(None)
            self.after_calls = []
            self.protocols = {}
            self.commands = {}
            self.destroyed = False
            self.geom = ""
            self.icon = None

        def winfo_fpixels(self, what):
            assert what == "1i"
            return self.dpi

        def iconphoto(self, default, img):
            self.icon = img

        def createcommand(self, name, fn):
            self.commands[name] = fn

        def title(self, t):
            self.kw["title"] = t

        def geometry(self, g):
            self.geom = g

        def minsize(self, *a):
            pass

        def protocol(self, name, fn):
            self.protocols[name] = fn

        def after(self, ms, fn):
            self.after_calls.append(fn)

        def mainloop(self):
            pass

        def destroy(self):
            self.destroyed = True

    class Text(Widget):
        def __init__(self, master=None, **kw):
            super().__init__(master, **kw)
            self.content = ""

        def insert(self, index, text):
            self.content += text

        def see(self, index):
            pass

        def get(self, start, end=None):
            return self.content  # seperti Tk: get("1.0", "end-1c") = semua teks yang dimasukkan

    class Treeview(Widget):
        def __init__(self, master=None, columns=(), height=10, selectmode=None, show=None, **kw):
            super().__init__(master, **kw)
            self.items = {}
            self._sel = ()
            self._n = 0
            self.row_at = None

        def heading(self, col, text="", **kw):
            self.headings = getattr(self, "headings", {})
            self.headings[col] = text

        def extra_texts(self):
            return list(getattr(self, "headings", {}).values())

        def column(self, *a, **kw):
            pass

        def yview(self, *a):
            pass

        def insert(self, parent, index, iid=None, text="", values=()):
            if iid is None:
                self._n += 1
                iid = "I%03d" % self._n
            self.items[iid] = {"text": text, "values": list(values)}
            return iid

        def delete(self, *iids):
            for i in iids:
                self.items.pop(i, None)

        def get_children(self, item=""):
            return tuple(self.items.keys())

        def item(self, iid, **kw):
            if kw:
                self.items[iid].update(kw)
            return self.items[iid]

        def selection(self):
            return self._sel

        def selection_set(self, items):
            self._sel = tuple(items)

        def identify_region(self, x, y):
            return "tree"

        def identify_column(self, x):
            return "#0"

        def identify_row(self, y):
            return self.row_at or ""

    class Notebook(Widget):
        def __init__(self, master=None, **kw):
            super().__init__(master, **kw)
            self.tabs = []
            self.selected = 0

        def add(self, child, text=""):
            self.tabs.append((child, text))

        def select(self, idx=None):
            if idx is not None:
                self.selected = idx
            return self.selected

        def index(self, tab):
            if isinstance(tab, int):
                return tab
            for i, (child, _text) in enumerate(self.tabs):
                if child is tab:
                    return i
            return 0

        def tab_texts(self):
            return [t for _c, t in self.tabs]

        def extra_texts(self):
            return self.tab_texts()

    class Progressbar(Widget):
        def start(self, *a):
            self.running = True

        def stop(self):
            self.running = False

    class Scrollbar(Widget):
        def set(self, *a):
            pass

    for name in ("Frame", "Label", "Entry", "Button", "LabelFrame", "Checkbutton", "Radiobutton"):
        setattr(ttk, name, type(name, (Widget,), {}))
    ttk.Scrollbar = Scrollbar

    class Combobox(Widget):
        def __init__(self, master=None, values=(), **kw):
            super().__init__(master, **kw)
            self.values = list(values)
            self.value = ""
            self.handlers = {}

        def set(self, v):
            self.value = v

        def get(self):
            return self.value

        def bind(self, event, fn, *a):
            self.handlers[event] = fn

        def choose(self, v):
            """Seperti pengguna memilih item dari daftar."""
            self.value = v
            self.handlers["<<ComboboxSelected>>"](None)

    ttk.Combobox = Combobox
    ttk.Treeview = Treeview
    ttk.Notebook = Notebook
    ttk.Progressbar = Progressbar

    class Style:
        configured = {}

        def __init__(self, master=None):
            pass

        def configure(self, style, **kw):
            Style.configured.setdefault(style, {}).update(kw)

    class PhotoImage:
        def __init__(self, file=None, **kw):
            self.file = file

    ttk.Style = Style
    tk.Tk = Tk
    tk.PhotoImage = PhotoImage
    tk.Text = Text
    tk.StringVar = Var
    tk.BooleanVar = Var
    tk.END = "end"
    tk.ttk = ttk
    tk.filedialog = filedialog
    tk.messagebox = messagebox

    filedialog.next_open = ""
    filedialog.next_open_many = ()
    filedialog.next_dir = ""
    filedialog.askopenfilename = lambda **kw: filedialog.next_open
    filedialog.askopenfilenames = lambda **kw: filedialog.next_open_many
    filedialog.askdirectory = lambda **kw: filedialog.next_dir

    messagebox.log = []
    messagebox.answer_yes = False          # jawaban untuk askyesno

    def _rec(kind):
        def f(title, msg, **kw):
            messagebox.log.append((kind, msg))
            return messagebox.answer_yes if kind == "askyesno" else None
        return f

    for kind in ("showerror", "showinfo", "showwarning", "askyesno"):
        setattr(messagebox, kind, _rec(kind))

    return {"tkinter": tk, "tkinter.ttk": ttk, "tkinter.filedialog": filedialog,
            "tkinter.messagebox": messagebox}


def install(monkeypatch):
    mods = build()
    for name, mod in mods.items():
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.delitem(sys.modules, "collect_files_plus.gui", raising=False)
    import collect_files_plus.gui as gui  # noqa: E402
    return gui, mods
