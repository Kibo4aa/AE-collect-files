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
            pass

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

    class Treeview(Widget):
        def __init__(self, master=None, columns=(), height=10, selectmode=None, show=None, **kw):
            super().__init__(master, **kw)
            self.items = {}
            self._sel = ()
            self._n = 0
            self.row_at = None

        def heading(self, *a, **kw):
            pass

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
            self.tabs.append(text)

        def select(self, idx=None):
            if idx is not None:
                self.selected = idx
            return self.selected

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

    def _rec(kind):
        def f(title, msg, **kw):
            messagebox.log.append((kind, msg))
            return False
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
