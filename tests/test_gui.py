"""Uji alur GUI dengan tkinter tiruan (logika), plus uji asap Tk asli kalau ada layar."""

import sys

import pytest

import fake_tkinter
from collect_files_plus.plugins import PluginRoot
from helpers import env_for, files_under, make_fx_project, make_plugin_tree, make_project


def _finish(app):
    app.worker.join(timeout=120)
    app._poll()


@pytest.fixture
def gui(monkeypatch, tmp_path):
    gui, mods = fake_tkinter.install(monkeypatch)
    monkeypatch.setattr(gui, "settings_path", lambda: tmp_path / "settings.json")
    monkeypatch.setattr(gui, "open_folder", lambda p: None)
    return gui, mods


def test_gui_flow_footage(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import collector
    env = env_for(tmp_path)
    monkeypatch.setattr(collector, "Environment", lambda: env)
    proj = make_project(tmp_path)

    root = mods["tkinter"].Tk()
    app = gui.App(root, initial=str(proj))
    for fn in list(root.after_calls):
        fn()
    _finish(app)
    names = {app.comp_tree.labels[i]: i for i in app.comp_tree.checked}
    assert set(names) == {"Main", "Precomp Logo", "Template Tak Dipakai"}
    assert all(app.comp_tree.checked.values())          # tidak ada RQ/comp aktif -> semua
    assert app.var_dest.get() == str(proj.parent)

    # hanya comp Main
    for label, iid in names.items():
        app.comp_tree.set(iid, label == "Main")
    app.opt_reduce.set(True)
    app.var_dest.set(str(tmp_path / "out"))
    app.start_analyze()
    _finish(app)
    assert app.analysis is not None
    foot = [v["values"][0] for v in app.foot_tree.tree.items.values()]
    assert "music.wav" not in foot and "logo.png" in foot

    app.start_collect()
    _finish(app)
    assert app.result is not None and app.result.saved_ok
    files = files_under(app.result.dest_root)
    assert "(Footage)/Render/shot_0003.png" in files and not any("music" in f for f in files)
    assert ("askyesno" in [k for k, _m in mods["tkinter.messagebox"].log])
    assert (tmp_path / "settings.json").is_file()


def test_gui_plugin_checkboxes(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import collector
    mc = make_plugin_tree(tmp_path)
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)])
    monkeypatch.setattr(collector, "Environment", lambda: env)
    proj = make_fx_project(tmp_path)

    root = mods["tkinter"].Tk()
    app = gui.App(root)
    mods["tkinter.filedialog"].next_open = str(proj)
    app.choose_aep()
    _finish(app)
    app.var_dest.set(str(tmp_path / "out"))
    app.start_analyze()
    _finish(app)
    labels = {app.plugin_tree.labels[i]: i for i in app.plugin_tree.checked}
    deep = [i for l, i in labels.items() if l.endswith("Deep Glow.aex")][0]
    # klik kotak centang Deep Glow -> tidak dicentang
    app.plugin_tree.tree.row_at = deep
    app.plugin_tree._click(type("E", (), {"x": 1, "y": 1})())
    assert app.plugin_tree.checked[deep] is False
    assert "2 dari 3 file plugin dicentang" in app.plugin_total.kw["text"]

    app.start_collect()
    _finish(app)
    files = files_under(app.result.dest_root)
    assert "(Plugins)/MediaCore/BorisFX/Continuum/BCC_Blur.aex" in files
    assert not any(f.endswith("Deep Glow.aex") for f in files)


def test_gui_bad_file_shows_error(gui, tmp_path):
    gui, mods = gui
    bad = tmp_path / "rusak.aep"
    bad.write_bytes(b"bukan project")
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    app.var_aep.set(str(bad))
    app.load_project()
    _finish(app)
    assert any(k == "showerror" and "tidak bisa dibaca" in m for k, m in mods["tkinter.messagebox"].log)


def test_gui_keeps_plugin_choice_when_options_change(gui, tmp_path, monkeypatch):
    """Centang plugin yang diubah user tetap dipakai walau opsi diganti sebelum Collect."""
    gui, mods = gui
    from collect_files_plus import collector
    mc = make_plugin_tree(tmp_path)
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)])
    monkeypatch.setattr(collector, "Environment", lambda: env)
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    app.var_aep.set(str(make_fx_project(tmp_path)))
    app.load_project()
    _finish(app)
    app.var_dest.set(str(tmp_path / "out"))
    app.start_analyze()
    _finish(app)
    kaca = [i for i, l in app.plugin_tree.labels.items() if l.endswith("Kaca.aex")][0]
    app.plugin_tree.toggle([kaca])
    app.opt_fonts.set(False)            # opsi berubah -> analisa ulang saat Collect
    app.start_collect()
    _finish(app)
    files = files_under(app.result.dest_root)
    assert not any(f.endswith("Kaca.aex") for f in files)
    assert any(f.endswith("BCC_Blur.aex") for f in files)


def test_gui_scales_on_high_dpi(gui, tmp_path):
    gui, mods = gui
    root = mods["tkinter"].Tk()
    root.dpi = 144.0                    # Windows 150%
    app = gui.App(root)
    assert app.scale == 1.5
    assert root.geom == "1620x1080"
    assert mods["tkinter.ttk"].Style.configured["Treeview"]["rowheight"] == 32
    assert root.icon is not None and root.icon.file.endswith("icon.png")


def test_gui_batch_flow(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import collector
    env = env_for(tmp_path)
    monkeypatch.setattr(collector, "Environment", lambda: env)
    p1 = make_project(tmp_path / "A")
    p2 = make_project(tmp_path / "B")
    bad = tmp_path / "C" / "rusak.aep"
    bad.parent.mkdir()
    bad.write_bytes(b"bukan project")

    root = mods["tkinter"].Tk()
    app = gui.App(root)
    mods["tkinter.filedialog"].next_open_many = (str(p1), str(bad))
    app.batch_add_files()
    assert app.nb.select() is app.batch_tab
    # tab Batch sedang aktif -> drop 1 file .aep pun masuk ke daftar batch; file lain diabaikan
    app.on_drop([str(p2), str(tmp_path / "catatan.txt"), str(p1)])
    assert [p.name for p in app.batch_paths] == ["Proyek Saya.aep", "rusak.aep", "Proyek Saya.aep"]
    assert app.batch_count.kw["text"] == "3 project"

    app.var_dest.set(str(tmp_path / "out"))
    app.start_batch()
    _finish(app)
    run = app.batch_run
    assert [it.status for it in run.items] == ["catatan", "gagal", "catatan"]
    rows = [app.batch_tree.tree.items[str(i)]["values"] for i in range(3)]
    assert rows[0][3] == "OK, 1 footage hilang; 1 font tidak ketemu"
    assert rows[1][3].startswith("GAGAL: ") and rows[2][4] == "Proyek Saya_Collected (2)"
    assert any(k == "askyesno" and "Batch selesai" in m for k, m in mods["tkinter.messagebox"].log)
    assert app.last_folder == tmp_path / "out"
    assert any(f.name.startswith("CollectFilesPlus_batch_") for f in (tmp_path / "out").iterdir())

    app.batch_tree.tree.selection_set(["1"])
    app.batch_remove_selected()
    assert [p.parent.parent.name for p in app.batch_paths] == ["A", "B"]


def test_gui_drop_single_and_folder(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import collector
    env = env_for(tmp_path)
    monkeypatch.setattr(collector, "Environment", lambda: env)
    proj = make_project(tmp_path / "A")
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    app.on_drop([str(proj)])                    # satu file, bukan di tab batch -> dibuka biasa
    _finish(app)
    assert app.aep is not None and app.var_aep.get() == str(proj)
    assert app.batch_paths == []
    app.on_drop([str(tmp_path)])               # folder -> semua .aep di dalamnya ke batch
    assert app.batch_paths == [proj]
    app.on_drop([str(tmp_path / "x.txt")])
    assert "bukan file .aep" in app.var_status.get()


def test_main_routes_files_to_gui(gui, tmp_path, monkeypatch):
    gui, mods = gui
    calls = []
    monkeypatch.setattr(gui, "main", lambda initial=None, batch=None: calls.append((initial, batch)) or 0)
    a = tmp_path / "a.aep"
    b = tmp_path / "b.aep"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    from collect_files_plus import __main__ as entry
    for argv in ([str(a), str(b)], [str(a)], [str(tmp_path)]):
        monkeypatch.setattr(sys, "argv", ["cfp"] + argv)
        assert entry.main() == 0
    assert calls == [(None, [str(a), str(b)]), (str(a), None), (None, [str(tmp_path)])]


def test_gui_starts_with_batch_list(gui, tmp_path):
    gui, mods = gui
    a = tmp_path / "Edit" / "a.aep"
    a.parent.mkdir()
    a.write_bytes(b"x")
    root = mods["tkinter"].Tk()
    app = gui.App(root, batch=[str(tmp_path / "Edit")])
    assert app.batch_paths == [a] and app.nb.select() is app.batch_tab
    assert app.var_dest.get() == str(a.parent)


def _real_root():
    try:
        import tkinter as tk
    except ImportError:
        pytest.skip("tkinter tidak tersedia")
    try:
        return tk.Tk()
    except tk.TclError as exc:
        pytest.skip("tidak ada layar untuk Tk: %s" % exc)


def test_real_tk_smoke(tmp_path, monkeypatch):
    """Jalan di CI (Windows/macOS, Linux via xvfb): widget Tk asli dibuat dan alur dasar jalan."""
    root = _real_root()
    try:
        sys.modules.pop("collect_files_plus.gui", None)
        import collect_files_plus.gui as real_gui
        from tkinter import messagebox
        shown = []
        for kind in ("showerror", "showinfo", "showwarning", "askyesno"):
            monkeypatch.setattr(messagebox, kind, lambda *a, _k=kind, **kw: shown.append((_k, a)) and False)
        monkeypatch.setattr(real_gui, "settings_path", lambda: tmp_path / "settings.json")
        monkeypatch.setattr(real_gui, "open_folder", lambda p: None)
        from collect_files_plus import collector
        env = env_for(tmp_path)
        monkeypatch.setattr(collector, "Environment", lambda: env)
        proj = make_project(tmp_path)

        app = real_gui.App(root)
        app.var_aep.set(str(proj))
        app.load_project()
        _finish(app)
        root.update()
        assert len(app.comp_tree.tree.get_children()) == 3
        first = app.comp_tree.tree.get_children()[0]
        assert app.comp_tree.tree.item(first, "text").startswith(real_gui.CHECK_ON)
        app.var_dest.set(str(tmp_path / "out"))
        app.start_analyze()
        _finish(app)
        root.update()
        assert app.analysis is not None
        assert len(app.foot_tree.tree.get_children()) >= 4
        app.start_collect()
        _finish(app)
        root.update()
        assert app.result is not None and app.result.saved_ok, shown
        assert not [s for s in shown if s[0] == "showerror"], shown
    finally:
        root.destroy()


def _send_drop(hwnd, files):
    """Kirim WM_DROPFILES seperti Explorer (memori HDROP berisi daftar file)."""
    import ctypes
    from ctypes import wintypes

    class DROPFILES(ctypes.Structure):
        _fields_ = [("pFiles", wintypes.DWORD), ("pt", wintypes.POINT), ("fNC", wintypes.BOOL),
                    ("fWide", wintypes.BOOL)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    u32 = ctypes.WinDLL("user32", use_last_error=True)
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u32.SendMessageW.restype = ctypes.c_ssize_t
    u32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    data = ("\0".join(files) + "\0\0").encode("utf-16-le")
    head = DROPFILES(ctypes.sizeof(DROPFILES), wintypes.POINT(0, 0), False, True)
    h = k32.GlobalAlloc(0x0042, ctypes.sizeof(head) + len(data))   # GMEM_MOVEABLE | GMEM_ZEROINIT
    p = k32.GlobalLock(h)
    ctypes.memmove(p, ctypes.byref(head), ctypes.sizeof(head))
    ctypes.memmove(p + ctypes.sizeof(head), data, len(data))
    k32.GlobalUnlock(h)
    u32.SendMessageW(hwnd, 0x0233, h, 0)     # handler memanggil DragFinish (memori dibebaskan di sana)


@pytest.mark.skipif(sys.platform != "win32", reason="drag & drop Explorer khusus Windows")
def test_real_windows_drag_and_drop(tmp_path, monkeypatch):
    root = _real_root()
    try:
        sys.modules.pop("collect_files_plus.gui", None)
        import collect_files_plus.gui as real_gui
        from collect_files_plus import dnd
        from tkinter import messagebox
        for kind in ("showerror", "showinfo", "showwarning", "askyesno"):
            monkeypatch.setattr(messagebox, kind, lambda *a, **kw: False)
        monkeypatch.setattr(real_gui, "settings_path", lambda: tmp_path / "settings.json")
        from collect_files_plus import collector
        env = env_for(tmp_path)
        monkeypatch.setattr(collector, "Environment", lambda: env)
        proj = make_project(tmp_path / "A")
        other = tmp_path / "B" / "Kedua Proyek.aep"
        other.parent.mkdir()
        other.write_bytes(b"x")

        app = real_gui.App(root)
        assert app.dnd_ok, "drag & drop tidak aktif"
        hwnd = dnd._hooks[-1].hwnd
        _send_drop(hwnd, [str(proj)])              # satu file -> dibuka sebagai project
        root.update()
        _finish(app)
        root.update()
        assert app.aep is not None and app.var_aep.get() == str(proj)

        _send_drop(hwnd, [str(proj), str(other)])  # banyak file -> tab Batch
        root.update()
        assert [p.name for p in app.batch_paths] == ["Proyek Saya.aep", "Kedua Proyek.aep"]
        assert str(app.nb.select()) == str(app.batch_tab)
    finally:
        root.destroy()
