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


def test_gui_switch_language_keeps_state(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import collector, i18n
    from test_i18n import _indonesian_words
    mc = make_plugin_tree(tmp_path)
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)])
    monkeypatch.setattr(collector, "Environment", lambda: env)
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    assert i18n.get_language() == "id" and app.lang_box.get() == "Bahasa Indonesia"
    app.var_aep.set(str(make_fx_project(tmp_path)))
    app.load_project()
    _finish(app)
    app.var_dest.set(str(tmp_path / "out"))
    app.start_analyze()
    _finish(app)
    kaca = [i for i, l in app.plugin_tree.labels.items() if l.endswith("Kaca.aex")][0]
    app.plugin_tree.toggle([kaca])
    app.batch_paths = [tmp_path / "x.aep"]
    old_nb = app.nb

    app.lang_box.choose("English")
    assert i18n.get_language() == "en" and app.nb is not old_nb and old_nb.destroyed
    assert app.nb.tab_texts()[:3] == ["1. Comps & options", "2. Plugins", "3. Fonts"]
    assert app.plugin_tree.checked[kaca] is False                 # centang tetap
    assert all(app.comp_tree.checked.values())
    assert app.plugin_total.kw["text"] == "2 of 3 plugin files ticked, total %s" % \
        app.plugin_total.kw["text"].split("total ")[1]
    assert app.batch_tree.tree.items["0"]["values"][3] == "waiting"
    assert "Membuka" in app.log.get("1.0", "end-1c")             # isi log lama tetap ada
    assert app.var_status.get() == "Language changed to English."
    assert gui.load_settings()["lang"] == "en"
    texts = root.all_texts()
    assert "Analyze" in texts and "Collect all projects" in texts
    assert _indonesian_words(" | ".join(texts)) == []

    app.start_collect()                                        # collect dengan opsi sama -> pakai centang tadi
    _finish(app)
    files = files_under(app.result.dest_root)
    assert not any(f.endswith("Kaca.aex") for f in files)
    assert (app.result.dest_root / "Efek_effect_list.csv").is_file()

    app.lang_box.choose("Bahasa Indonesia")
    assert i18n.get_language() == "id" and app.nb.tab_texts()[0] == "1. Comp & opsi"


def test_gui_language_defaults(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import i18n
    monkeypatch.setenv(i18n.ENV_VAR, "en")
    gui.App(mods["tkinter"].Tk())                    # pemakai baru -> bahasa sistem
    assert i18n.get_language() == "en"
    gui.save_settings({"dest": str(tmp_path)})       # pemakai lama (sebelum ada pilihan bahasa) -> Indonesia
    gui.App(mods["tkinter"].Tk())
    assert i18n.get_language() == "id"
    gui.save_settings({"dest": str(tmp_path), "lang": "en"})
    app = gui.App(mods["tkinter"].Tk())
    assert i18n.get_language() == "en" and app.lang_box.get() == "English"


def _wait_update_event(app, attr="update_info", tries=200):
    import time
    for _i in range(tries):
        app._poll()
        if getattr(app, attr):
            return
        time.sleep(0.01)


def test_gui_update_banner_and_install(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import updater
    info = updater.UpdateInfo("9.9.0", "v9.9.0", "https://github.com/Kibo4aa/AE-collect-files/releases/tag/v9.9.0",
                              asset_name="u.zip", asset_url="https://example.invalid/u.zip")
    monkeypatch.setattr(updater, "check_latest", lambda timeout=10.0: info)
    opened = []
    monkeypatch.setattr(gui.webbrowser, "open", lambda url: opened.append(url))
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    assert not getattr(app.update_bar, "packed", False)
    app.check_updates()
    _wait_update_event(app)
    assert app.update_bar.packed
    assert app.update_label.kw["text"] == "Versi baru 9.9.0 tersedia (kamu memakai %s)." % gui.__version__
    assert app.btn_update.kw["text"] == "Download"           # dari source: tidak bisa ganti diri sendiri
    app.start_update()
    assert opened == [info.page]

    # build exe Windows: download -> extract -> skrip pemasang -> aplikasi ditutup
    monkeypatch.setattr(updater, "can_self_update", lambda: True)
    calls = []
    monkeypatch.setattr(updater, "download", lambda i, d, progress=None, cancel=None:
                        (progress(10, 20), progress(20, 20), calls.append(("dl", d)), d / "u.zip")[-1])
    monkeypatch.setattr(updater, "extract_app", lambda z, d: calls.append(("ex", z)) or d / "CollectFilesPlus")
    monkeypatch.setattr(updater, "launch_apply", lambda new, tmp, ver: calls.append(("apply", new, tmp, ver)))
    app._show_update_bar()
    assert app.btn_update.kw["text"] == "Update sekarang"
    app.start_update()                                       # dijawab "tidak" -> tidak ada apa-apa
    assert app.worker is None and not calls
    mods["tkinter.messagebox"].answer_yes = True
    app.start_update()
    _finish(app)
    kinds = [c[0] for c in calls]
    assert kinds == ["dl", "ex", "apply"] and calls[2][3] == "9.9.0"
    assert calls[2][1] == calls[2][2] / "baru" / "CollectFilesPlus"
    assert root.destroyed


def test_gui_update_manual_messages(gui, monkeypatch):
    gui, mods = gui
    from collect_files_plus import updater
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    log = mods["tkinter.messagebox"].log
    cases = [(lambda timeout=10.0: updater.UpdateInfo(gui.__version__, "v" + gui.__version__, "p"),
              "sudah memakai versi terbaru"),
             (lambda timeout=10.0: None, "Belum ada rilis"),
             (lambda timeout=10.0: (_ for _ in ()).throw(OSError("offline")), "Tidak bisa mengecek update")]
    for fn, expect in cases:
        monkeypatch.setattr(updater, "check_latest", fn)
        n = len(log)
        app.check_updates(manual=True)
        for _i in range(200):
            app._poll()
            if len(log) > n:
                break
            __import__("time").sleep(0.01)
        assert expect in log[-1][1], log[-1]
    assert app.update_info is None and not getattr(app.update_bar, "packed", False)


def test_gui_update_bar_hidden_stays_hidden_after_language_switch(gui, monkeypatch):
    gui, mods = gui
    from collect_files_plus import updater
    monkeypatch.setattr(updater, "check_latest",
                        lambda timeout=10.0: updater.UpdateInfo("9.9.0", "v9.9.0", "p", asset_url="u"))
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    app.check_updates()
    _wait_update_event(app)
    app.lang_box.choose("English")
    assert app.update_bar.packed
    assert app.update_label.kw["text"] == "New version 9.9.0 is available (you have %s)." % gui.__version__
    app.hide_update_bar()
    app.lang_box.choose("Bahasa Indonesia")
    assert not getattr(app.update_bar, "packed", False)


def test_gui_update_startup(gui, monkeypatch):
    gui, mods = gui
    from collect_files_plus import updater
    monkeypatch.delenv(updater.NO_CHECK_ENV)
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    assert app.check_updates in root.after_calls             # cek otomatis saat dibuka
    monkeypatch.setenv(updater.NO_CHECK_ENV, "1")
    monkeypatch.setenv(updater.RESULT_ENV, "ok:9.9.0")       # dibuka ulang oleh skrip pemasang
    root = mods["tkinter"].Tk()
    gui.App(root)
    for fn in list(root.after_calls):
        if getattr(fn, "__name__", "") == "<lambda>":
            fn()
    assert any(k == "showinfo" and "Update berhasil" in m and "9.9.0" in m for k, m in mods["tkinter.messagebox"].log)
    import os
    assert updater.RESULT_ENV not in os.environ


@pytest.fixture(scope="module")
def real_root():
    """Satu jendela Tk asli untuk semua test di modul ini, seperti aplikasinya
    (membuat interpreter Tk kedua dalam satu proses tidak andal di Windows)."""
    try:
        import tkinter as tk
    except ImportError:
        pytest.skip("tkinter tidak tersedia")
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip("tidak ada layar untuk Tk: %s" % exc)
    yield root
    try:
        root.destroy()
    except Exception:  # noqa: BLE001
        pass


def _clear(root):
    for w in root.winfo_children():
        w.destroy()
    root.update()


def test_real_tk_smoke(real_root, tmp_path, monkeypatch):
    """Jalan di CI (Windows/macOS, Linux via xvfb): widget Tk asli dibuat dan alur dasar jalan."""
    root = real_root
    _clear(root)
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
        app.change_language("en")                  # bangun ulang widget asli dalam bahasa lain
        root.update()
        assert app.nb.tab(0, "text") == "1. Comps & options" and app.lang_box.get() == "English"
        assert len(app.foot_tree.tree.get_children()) >= 4
        app.change_language("id")
        root.update()
        assert app.nb.tab(0, "text") == "1. Comp & opsi"
        from collect_files_plus import updater
        app.update_info = updater.UpdateInfo("9.9.0", "v9.9.0", "p", asset_url="u")
        app._show_update_bar()                     # bar update dengan widget asli
        root.update()
        assert app.update_bar.winfo_manager() == "pack"
        app.hide_update_bar()
        root.update()
        assert app.update_bar.winfo_manager() == ""
        app.start_collect()
        _finish(app)
        root.update()
        assert app.result is not None and app.result.saved_ok, shown
        assert not [s for s in shown if s[0] == "showerror"], shown
    finally:
        _clear(root)


def _post_drop(hwnd, files):
    """Kirim WM_DROPFILES seperti Explorer: memori HDROP berisi daftar file, lewat PostMessage
    (diproses nanti oleh event loop Tk, persis seperti drop sungguhan)."""
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
    u32.PostMessageW.restype = wintypes.BOOL
    u32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    data = ("\0".join(files) + "\0\0").encode("utf-16-le")
    head = DROPFILES(ctypes.sizeof(DROPFILES), wintypes.POINT(0, 0), False, True)
    h = k32.GlobalAlloc(0x0042, ctypes.sizeof(head) + len(data))   # GMEM_MOVEABLE | GMEM_ZEROINIT
    p = k32.GlobalLock(h)
    ctypes.memmove(p, ctypes.byref(head), ctypes.sizeof(head))
    ctypes.memmove(p + ctypes.sizeof(head), data, len(data))
    k32.GlobalUnlock(h)
    assert u32.PostMessageW(hwnd, 0x0233, h, 0)   # handler memanggil DragFinish (memori dibebaskan di sana)


@pytest.mark.skipif(sys.platform != "win32", reason="drag & drop Explorer khusus Windows")
def test_real_windows_drag_and_drop(real_root, tmp_path, monkeypatch):
    root = real_root
    _clear(root)
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

        def run_mainloop(ms):
            root.after(ms, root.quit)
            root.mainloop()

        # drop datang saat mainloop berjalan, persis seperti file dari Explorer
        root.after(50, lambda: _post_drop(hwnd, [str(proj)]))
        run_mainloop(1200)
        assert app.worker is not None, "drop satu file tidak diproses"
        _finish(app)
        root.update()
        assert app.aep is not None and app.var_aep.get() == str(proj)

        root.after(50, lambda: _post_drop(hwnd, [str(proj), str(other)]))
        run_mainloop(1200)
        assert [p.name for p in app.batch_paths] == ["Proyek Saya.aep", "Kedua Proyek.aep"]
        assert str(app.nb.select()) == str(app.batch_tab)

        # drop berulang-ulang + interaksi lain tetap aman
        for i in range(5):
            root.after(20 * i + 10, lambda: _post_drop(hwnd, [str(other)]))
        root.after(150, lambda: app.change_language("en"))
        run_mainloop(1000)
        assert app.nb.tab(0, "text") == "1. Comps & options"
        assert len(app.batch_paths) == 2
        app.change_language("id")
    finally:
        _clear(root)
