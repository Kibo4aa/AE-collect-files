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

        def bind(self, seq=None, fn=None, add=None):
            self.bindings = getattr(self, "bindings", {})
            self.bindings.setdefault(seq, []).append(fn)

        def after(self, ms, fn=None):
            return "after#%d" % id(fn)

        def after_cancel(self, ident):
            pass

        def after_idle(self, fn):
            return self.after(0, fn)

        def winfo_exists(self):
            return not getattr(self, "destroyed", False)

        def configure(self, cnf=None, **kw):
            self.kw.update(cnf or {}, **kw)

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

        def geometry(self, g=None):
            if g is None:
                return self.geom
            self.geom = g

        def minsize(self, *a):
            pass

        def protocol(self, name, fn):
            self.protocols[name] = fn

        def after(self, ms, fn=None):
            self.after_calls.append(fn)
            return "after#%d" % len(self.after_calls)

        def mainloop(self):
            pass

        def destroy(self):
            self.destroyed = True

    class Text(Widget):
        def __init__(self, master=None, **kw):
            super().__init__(master, **kw)
            self.content = ""

        def insert(self, index, text, *tags):
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

        def insert(self, parent, index, iid=None, text="", values=(), tags=()):
            if iid is None:
                self._n += 1
                iid = "I%03d" % self._n
            self.items[iid] = {"text": text, "values": list(values), "tags": tuple(tags)}
            return iid

        def tag_configure(self, tag, **kw):
            self.tag_styles = getattr(self, "tag_styles", {})
            self.tag_styles.setdefault(tag, {}).update(kw)

        def delete(self, *iids):
            for i in iids:
                self.items.pop(i, None)

        def get_children(self, item=""):
            return tuple(self.items.keys())

        def item(self, iid, option=None, **kw):
            if kw:
                self.items[iid].update(kw)
            if option is not None:
                return self.items[iid].get(option)
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
            """Seperti Tk: yang dikembalikan selalu widget tab (bukan nomor)."""
            if idx is not None:
                self.selected = self.tabs[idx][0] if isinstance(idx, int) else idx
            return self.selected if not isinstance(self.selected, int) else self.tabs[self.selected][0]

        def index(self, tab):
            if isinstance(tab, int):
                return tab
            for i, (child, _text) in enumerate(self.tabs):
                if child is tab:
                    return i
            return 0

        def tab(self, tab, option=None, **kw):
            i = self.index(tab)
            if "text" in kw:
                self.tabs[i] = (self.tabs[i][0], kw["text"])
            if option == "text":
                return self.tabs[i][1]
            return {"text": self.tabs[i][1]}

        def tab_texts(self):
            return [t for _c, t in self.tabs]

        def extra_texts(self):
            return self.tab_texts()

    class Menu(Widget):
        """Menu: entri disimpan supaya test bisa mencari dan 'mengklik' item menu."""

        def __init__(self, master=None, **kw):
            super().__init__(master, **kw)
            self.entries = []

        def _add(self, kind, **kw):
            kw["kind"] = kind
            self.entries.append(kw)

        def add_command(self, **kw):
            self._add("command", **kw)

        def add_cascade(self, **kw):
            self._add("cascade", **kw)

        def add_radiobutton(self, **kw):
            self._add("radiobutton", **kw)

        def add_checkbutton(self, **kw):
            self._add("checkbutton", **kw)

        def add_separator(self, **kw):
            self._add("separator", **kw)

        def delete(self, first, last=None):
            self.entries = []

        def tk_popup(self, x, y, entry=""):
            self.popped = (x, y)

        def grab_release(self):
            pass

        def extra_texts(self):
            return [e["label"] for e in self.entries if isinstance(e.get("label"), str)]

        def labels(self):
            return [e.get("label") for e in self.entries if e["kind"] != "separator"]

        def entry(self, label):
            for e in self.entries:
                if e.get("label") == label:
                    return e
            raise KeyError(label)

        def invoke(self, label):
            """Seperti pengguna memilih item menu ini."""
            e = self.entry(label)
            if e["kind"] == "radiobutton":
                e["variable"].set(e["value"])
            elif e["kind"] == "checkbutton":
                e["variable"].set(not e["variable"].get())
            if e.get("command"):
                return e["command"]()

    class Toplevel(Widget):
        def wm_overrideredirect(self, flag=None):
            pass

        def wm_geometry(self, g=None):
            self.geom = g

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
    tk.Menu = Menu
    tk.Toplevel = Toplevel
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
