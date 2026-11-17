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
