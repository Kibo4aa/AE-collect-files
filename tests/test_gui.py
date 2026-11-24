"""Uji alur GUI dengan tkinter tiruan (logika), plus uji asap Tk asli kalau ada layar."""

import sys

import pytest

import fake_tkinter
from collect_files_plus.plugins import PluginRoot
from helpers import env_for, files_under, make_fx_project, make_plugin_tree, make_project


def _finish(app):
    app.worker.join(timeout=120)
    app._poll()


def _scanned(app, timeout=60.0):
    """Tunggu daftar comp project batch selesai dibaca (thread latar), lalu proses hasilnya."""
    import time
    end = time.time() + timeout
    while app._scan_thread is not None and time.time() < end:
        time.sleep(0.02)
    app._poll()


def _shows(app, tree, iid, state):
    """Baris tabel menampilkan kotak centang dengan status ini (gambar tema, atau karakter tanpa tema)."""
    from collect_files_plus import gui as g
    if app.check_images:
        return str(tree.item(iid, "image")[0]) == app.check_images[state]
    return str(tree.item(iid, "text")).startswith(g.CHECK_MARK[state])


def _rows(app):
    """Nilai kolom (Comp, Status, Hasil) tiap baris project di daftar batch."""
    return [app.batch_tree.tree.items[e.iid]["values"] for e in app.batch_entries]


def _submenu(menu, label):
    return menu.entry(label)["menu"]


def _menu_with(app, label):
    """Menu (di menubar) yang berisi item dengan label ini."""
    for top in app.menubar.entries:
        if top["kind"] == "cascade" and label in top["menu"].labels():
            return top["menu"]
    raise KeyError(label)


def _choose_language(app, root, name):
    """Seperti memilih bahasa dari menu Pengaturan > Bahasa / Language / 言語."""
    lang = _submenu(_menu_with(app, "Bahasa / Language / 言語"), "Bahasa / Language / 言語")
    lang.invoke(name)
    root.after_calls.pop()()                 # bahasa diganti setelah menu tertutup (after_idle)


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
    assert app.plugin_total.kw["text"].startswith("2/3 dicentang · ")

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
    assert root.geom == "1650x1110"
    assert mods["tkinter.ttk"].Style.configured["Treeview"]["rowheight"] == 37
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

    _scanned(app)
    assert [r[0] for r in _rows(app)] == ["semua comp (3)", "gagal dibaca", "semua comp (3)"]
    assert "rusak.aep" in app.batch_tree.tips[app.batch_entries[1].iid]
    app.var_dest.set(str(tmp_path / "out"))
    app.start_batch()
    _finish(app)
    run = app.batch_run
    assert [it.status for it in run.items] == ["catatan", "gagal", "catatan"]
    rows = _rows(app)
    assert rows[0][1] == "OK, 1 footage hilang; 1 font tidak ketemu"
    assert rows[1][1].startswith("GAGAL: ") and rows[2][2] == "Proyek Saya_Collected (2)"
    assert any(k == "askyesno" and "Batch selesai" in m for k, m in mods["tkinter.messagebox"].log)
    assert app.last_folder == tmp_path / "out"
    assert any(f.name.startswith("CollectFilesPlus_batch_") for f in (tmp_path / "out").iterdir())

    app.batch_tree.tree.selection_set([app.batch_entries[1].iid + "/1"])     # baris comp -> project-nya
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
    assert i18n.get_language() == "id" and app.var_lang.get() == "id"
    app.var_aep.set(str(make_fx_project(tmp_path)))
    app.load_project()
    _finish(app)
    app.var_dest.set(str(tmp_path / "out"))
    app.start_analyze()
    _finish(app)
    kaca = [i for i, l in app.plugin_tree.labels.items() if l.endswith("Kaca.aex")][0]
    app.plugin_tree.toggle([kaca])
    app.batch_entries = [app._new_entry(tmp_path / "x.aep")]
    app._refresh_batch()
    old_nb = app.nb

    old_menu = app.menubar
    _choose_language(app, root, "English")
    assert i18n.get_language() == "en" and app.nb is not old_nb and old_nb.destroyed and old_menu.destroyed
    assert app.nb.tab_texts()[:3] == ["Comps & options", "Plugins (3)", "Fonts (1)"]
    assert [e["label"] for e in app.menubar.entries] == ["File", "Settings", "Help"]
    assert app.plugin_tree.checked[kaca] is False                 # centang tetap
    assert all(app.comp_tree.checked.values())
    assert app.plugin_total.kw["text"] == "2/3 ticked · %s" % app.plugin_total.kw["text"].split("· ")[1]
    assert _rows(app)[0][1:] == ["waiting", ""]
    assert "Membuka" in app.log.get("1.0", "end-1c")             # isi log lama tetap ada
    assert app.var_status.get() == "Language changed to English."
    assert gui.load_settings()["lang"] == "en"
    texts = root.all_texts()
    assert "Analyze" in texts and "Collect" in texts and "Collect all projects" not in texts
    assert _indonesian_words(" | ".join(texts)) == []
    tab = app.nb.select()
    app.set_mode("batch")                                      # tombol bawah ikut mode, dalam bahasa baru
    assert (app.btn_analyze.kw["text"], app.btn_collect.kw["text"]) == ("Analyze all", "Collect all")
    app.set_mode("single")
    app.nb.select(tab)
    assert (app.btn_analyze.kw["text"], app.btn_collect.kw["text"]) == ("Analyze", "Collect")

    app.start_collect()                                        # collect dengan opsi sama -> pakai centang tadi
    _finish(app)
    files = files_under(app.result.dest_root)
    assert not any(f.endswith("Kaca.aex") for f in files)
    assert (app.result.dest_root / "Efek_effect_list.csv").is_file()

    _choose_language(app, root, "Bahasa Indonesia")
    assert i18n.get_language() == "id" and app.nb.tab_texts()[0] == "Comp & opsi"
    assert [e["label"] for e in app.menubar.entries] == ["File", "Pengaturan", "Bantuan"]


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
    assert i18n.get_language() == "en" and app.var_lang.get() == "en"
    monkeypatch.setenv(i18n.ENV_VAR, "ja")
    (tmp_path / "settings.json").unlink()
    app = gui.App(mods["tkinter"].Tk())               # Windows berbahasa Jepang -> 日本語
    assert i18n.get_language() == "ja" and app.nb.tab_texts()[0] == "コンポとオプション"


def test_gui_menus_help_and_theme(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import i18n
    opened = []
    monkeypatch.setattr(gui, "open_folder", lambda p: opened.append(p))
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    assert [e["label"] for e in app.menubar.entries] == ["File", "Pengaturan", "Bantuan"]
    m_file = _menu_with(app, "Buka project...")
    assert m_file.labels() == ["Buka project...", "Tambah project ke Batch...", "Tambah folder ke Batch...",
                               "Buka folder hasil", "Buka laporan terakhir", "Keluar"]
    m_file.invoke("Buka laporan terakhir")                       # belum ada laporan
    assert "Belum ada laporan" in mods["tkinter.messagebox"].log[-1][1]

    m_help = _menu_with(app, "Cara pakai")
    m_help.invoke("Cara pakai")
    assert opened[-1].name == "README_id.txt" and opened[-1].is_file()
    app.change_language("ja")
    _menu_with(app, "使い方").invoke("使い方")
    assert opened[-1].name == "README_ja.txt" and opened[-1].is_file()
    app.change_language("en")
    _menu_with(app, "How to use").invoke("How to use")
    assert opened[-1].name == "README_en.txt" and i18n.get_language() == "en"

    m_set = _menu_with(app, "Theme")
    old_nb = app.nb
    _submenu(m_set, "Theme").invoke("Dark")
    root.after_calls.pop()()                                      # tema diganti setelah menu tertutup
    assert app.var_theme.get() == "dark" and gui.load_settings()["theme"] == "dark"
    assert app.nb is not old_nb and old_nb.destroyed              # jendela dibangun ulang dengan tema baru
    m_set = _menu_with(app, "Theme")
    m_set.invoke("Check for updates when the app opens")         # dimatikan
    assert gui.load_settings()["check_updates"] is False
    app.on_close()
    root2 = mods["tkinter"].Tk()
    app2 = gui.App(root2)
    assert app2.var_theme.get() == "dark" and app2.var_auto_update.get() is False
    assert app2.check_updates not in root2.after_calls           # cek otomatis dimatikan

    keys = root2.bindings
    for seq in ("<Control-o>", "<F5>", "<Control-Return>", "<F1>", "<Escape>"):
        assert seq in keys, seq


def test_gui_dark_theme_menus_and_dialogs(gui, monkeypatch):
    """Tema gelap: menu bar dari tombol bertema, menu drop-down gelap, kotak pesan bertema (bukan putih)."""
    gui, mods = gui
    monkeypatch.setattr(gui.theme, "apply", lambda root, mode, scale=1.0: "light" if mode == "system" else mode)
    monkeypatch.setattr(gui.App, "native_menus", property(lambda self: False))   # juga di macOS
    shown = []
    monkeypatch.setattr(gui.dialogs, "show", lambda root, title, text, kind="showinfo", dark=False, scale=1.0:
                        shown.append((kind, dark)) or True)
    gui.save_settings({"theme": "dark", "lang": "en"})
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    assert app.theme_name == "dark"
    assert app.menubar.kw["background"] == gui.theme.MENU_COLORS["dark"]["background"]
    assert app.menubar.kw["relief"] == "flat" and app.menubar.kw["borderwidth"] == 0
    assert [b.kw["text"] for b, _m in app.menu_buttons] == ["File", "Settings", "Help"]
    assert app.menu_frame in app._frames and "menu" not in root.kw   # bukan menu bar bawaan (putih)
    button, menu = app.menu_buttons[0]
    app._post_menu(menu, button)
    assert menu.popped == (0, 20) and menu.is_open                 # tepat di bawah tombol "File"
    assert all(c.kw["background"] == "#2c2c2c" for c in menu.rows[0][1])   # baris menu gelap
    app._post_menu(menu, button)                                   # klik tombol lagi: tutup
    assert not menu.is_open
    # menu terbuka, lalu tombol "Settings" diklik: menu File tutup, menu Settings terbuka
    app._post_menu(menu, button)
    settings_button, settings_menu = app.menu_buttons[1]
    root.winfo_containing = lambda x, y: settings_button
    menu._press(type("E", (), {"x_root": 600, "y_root": 600})())
    root.after_calls.pop()()
    assert not menu.is_open and settings_menu.is_open
    settings_menu.unpost()
    app.open_last_report()
    assert shown == [("showinfo", True)] and not mods["tkinter.messagebox"].log
    assert app._message("askyesno", "?") is True

    _submenu(_menu_with(app, "Theme"), "Theme").invoke("Light")
    root.after_calls.pop()()
    assert app.theme_name == "light"
    assert app.menubar.kw["background"] == gui.theme.MENU_COLORS["light"]["background"]
    app.open_last_report()
    assert shown[-1] == ("showinfo", False)


def test_gui_window_size_is_remembered(gui, tmp_path):
    gui, mods = gui
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    root.geom = "1200x800+40+30"                                 # jendela digeser & diperbesar
    app.on_close()
    assert gui.load_settings()["geometry"] == "1200x800+40+30"
    root2 = mods["tkinter"].Tk()
    gui.App(root2)
    assert root2.geom == "1200x800"                              # ukuran saja; posisi diatur Windows
    gui.save_settings({"geometry": "rusak"})
    root3 = mods["tkinter"].Tk()
    gui.App(root3)
    assert root3.geom == "1100x740"


def test_gui_tab_counts_reveal_and_lazy_reload(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import collector, project
    mc = make_plugin_tree(tmp_path)
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)])
    monkeypatch.setattr(collector, "Environment", lambda: env)
    shown = []
    monkeypatch.setattr(gui, "reveal", lambda p: shown.append(p))
    loads = []
    real = project.AepProject
    monkeypatch.setattr(project, "AepProject", lambda p: loads.append(p) or real(p))
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    assert app.comp_tree.empty_text.startswith("Drag file .aep ke sini") and app.comp_tree.empty_label.placed
    assert app.plugin_tree.empty_text == "Belum ada hasil. Klik Analisa."
    app.var_aep.set(str(make_project(tmp_path)))
    app.load_project()
    _finish(app)
    assert not app.comp_tree.empty_label.placed                 # petunjuk hilang begitu ada comp
    app.var_dest.set(str(tmp_path / "out"))
    app.opt_reduce.set(True)
    first = [i for i, l in app.comp_tree.labels.items() if l == "Main"][0]
    for iid in app.comp_tree.checked:
        app.comp_tree.set(iid, iid == first)
    app.start_analyze()
    _finish(app)
    tabs = app.nb.tab_texts()
    assert tabs[1] == "Plugin (0)" and tabs[2] == "Font (1)" and tabs[3].startswith("Footage (")
    assert app.plugin_tree.empty_text == "Tidak ada plugin pihak ketiga." and app.plugin_tree.empty_label.placed
    rows = app.foot_tree.tree.items
    missing = [i for i, r in rows.items() if r["values"][3] == "HILANG"]
    assert missing and rows[missing[0]]["tags"] == ("error",)
    app._reveal_row("foot", missing[0])
    assert shown and shown[-1].name == "missing.png"

    n = len(loads)
    app.start_collect()
    _finish(app)
    assert app.aep_stale and len(loads) == n                     # tidak dibaca ulang setelah collect
    assert app.last_report == app.result.report and app.result.report.is_file()
    app.change_language("en")                                    # daftar comp tetap 3 walau project di memori di-reduce
    assert len(app.comp_tree.labels) == 3 and app.comp_tree.checked[first] is True
    assert len(app.foot_tree.tree.items) == len(rows)            # tabel analisa tetap tampil
    app.start_analyze()                                          # baru dibaca ulang saat dibutuhkan
    _finish(app)
    assert len(loads) == n + 1 and not app.aep_stale

    opened = []
    monkeypatch.setattr(gui, "open_folder", lambda p: opened.append(p))
    _menu_with(app, "Open last report").invoke("Open last report")
    assert opened == [app.result.report]


def test_gui_batch_context_menu_and_progress(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import collector
    env = env_for(tmp_path)
    monkeypatch.setattr(collector, "Environment", lambda: env)
    opened = []
    monkeypatch.setattr(gui, "open_folder", lambda p: opened.append(p))
    p1 = make_project(tmp_path / "A")
    p2 = make_project(tmp_path / "B")
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    app.add_batch_paths([str(p1), str(p2)])
    _scanned(app)
    assert app.nb.tab_texts()[5] == "Batch (2)"
    app.var_dest.set(str(tmp_path / "out"))
    app.start_batch()
    assert app.progress.kw["mode"] == "determinate"
    _finish(app)
    assert app.progress.kw["value"] == 0                          # selesai -> direset
    tree = app.batch_tree.tree
    first, second = [e.iid for e in app.batch_entries]
    assert tree.items[first]["tags"] == ("warn",) and tree.items[second]["tags"] == ("warn",)

    event = type("E", (), {"x": 1, "y": 1, "x_root": 5, "y_root": 5})()
    tree.row_at = second
    app._batch_menu(event)
    menu = app.ctx_menu
    assert menu.labels() == ["Lihat detail analisa", "Buka folder hasil", "Buka laporan",
                             "Hapus dari daftar"] and menu.popped
    menu.invoke("Buka laporan")
    assert opened[-1] == app.batch_run.items[1].result.report
    menu.invoke("Buka folder hasil")
    assert opened[-1] == app.batch_run.items[1].result.dest_root
    assert opened[-1].name == "Proyek Saya_Collected (2)"
    app.batch_open(first)                                        # klik dua kali
    assert opened[-1].name == "Proyek Saya_Collected"
    menu.invoke("Hapus dari daftar")
    assert [p.parent.parent.name for p in app.batch_paths] == ["A"] and app.batch_run is None
    app._batch_menu(event)                                       # baris itu sudah tidak ada
    tree.row_at = first
    app._batch_menu(event)
    assert app.ctx_menu.entry("Buka laporan")["state"] == "disabled"   # belum di-collect lagi


def test_gui_batch_buttons_analyze_all_and_details(gui, tmp_path, monkeypatch):
    """Di tab Batch tombol bawah menjadi "Analisa semua" / "Collect semua" (tidak ada tombol Collect kedua)."""
    gui, mods = gui
    from collect_files_plus import collector
    env = env_for(tmp_path)
    monkeypatch.setattr(collector, "Environment", lambda: env)
    p1 = make_project(tmp_path / "A")
    p2 = make_project(tmp_path / "B")
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    assert (app.btn_analyze.kw["text"], app.btn_collect.kw["text"]) == ("Analisa", "Collect")
    assert app.var_status.get() == "Pilih file .aep untuk mulai."
    texts = root.all_texts()
    assert texts.count("Collect") == 1 and "Collect semua project" not in texts

    app.set_mode("batch")
    assert (app.btn_analyze.kw["text"], app.btn_collect.kw["text"]) == ("Analisa semua", "Collect semua")
    assert app.var_status.get().startswith("Tambahkan project ke daftar")
    app.start_analyze()                                         # daftar masih kosong
    assert any(k == "showwarning" and "masih kosong" in m for k, m in mods["tkinter.messagebox"].log)

    app.add_batch_paths([str(p1), str(p2)])
    _scanned(app)
    out = tmp_path / "out"
    app.var_dest.set(str(out))
    app.start_analyze()                                         # = Analisa semua (F5)
    assert app.btn_analyze.kw["state"] == "disabled" and app.progress.kw["mode"] == "determinate"
    _finish(app)
    run = app.batch_run
    assert run.kind == "analyze" and [it.status for it in run.items] == ["catatan", "catatan"]
    row = app.batch_tree.tree.items[app.batch_entries[0].iid]
    assert row["values"][1] == "OK, 1 footage hilang; 1 font tidak ketemu" and row["tags"] == ("warn",)
    assert row["values"][2].startswith("5 footage, 1 font, 0 plugin (")
    assert app.var_status.get().startswith("Analisa selesai: 0 OK, 2 ada catatan")
    assert not out.exists()                                     # analisa tidak menyalin apa pun
    assert not any("Batch selesai" in m for _k, m in mods["tkinter.messagebox"].log)

    # klik kanan > Lihat detail analisa: project dibuka di tab 1-5 dengan analisanya
    event = type("E", (), {"x": 1, "y": 1, "x_root": 5, "y_root": 5})()
    app.batch_tree.tree.row_at = app.batch_entries[1].iid
    app._batch_menu(event)
    assert app.ctx_menu.entry("Buka folder hasil")["state"] == "disabled"     # belum di-collect
    app.ctx_menu.invoke("Lihat detail analisa")
    _finish(app)
    assert app.var_aep.get() == str(p2) and app.aep.path == p2
    assert app.var_mode.get() == "single" and app.nb.select() is not app.batch_tab
    assert app.btn_collect.kw["text"] == "Collect"
    assert len(app.foot_tree.tree.items) == 5 and all(app.comp_tree.checked.values())
    assert app.analysis_key == app.options_key(app.current_options())      # Collect tidak menganalisa ulang
    app.start_collect()                                         # collect project ini saja
    _finish(app)
    assert app.result.dest_root == out / "Proyek Saya_Collected"

    # kembali ke tab Batch: Collect = Collect semua; klik dua kali baris yang sudah di-collect buka hasilnya
    opened = []
    monkeypatch.setattr(gui, "open_folder", lambda p: opened.append(p))
    app.set_mode("batch")
    app.start_collect()
    _finish(app)
    assert app.batch_run.kind == "collect" and app.batch_run.summary is not None
    assert sorted(d.name for d in out.iterdir() if d.is_dir()) == [
        "Proyek Saya_Collected", "Proyek Saya_Collected (2)", "Proyek Saya_Collected (3)"]
    app._batch_double(app.batch_entries[0].iid)
    assert opened[-1] == app.batch_run.items[0].result.dest_root
    extra = app._new_entry(tmp_path / "baru.aep")              # baris tanpa hasil -> lihat analisanya
    app.batch_entries.append(extra)
    app._refresh_batch()
    app._batch_double(extra.iid)
    _finish(app)
    assert "baru.aep" in app.log.get("1.0", "end-1c")          # file tidak ada -> error dilaporkan
    assert any(k == "showerror" and "tidak bisa dibaca" in m for k, m in mods["tkinter.messagebox"].log)


def _widgets(w):
    yield w
    for c in getattr(w, "children_list", []):
        yield from _widgets(c)


def test_gui_clean_layout(gui, tmp_path, monkeypatch):
    """Tampilan ringkas: label pendek + tooltip, petunjuk hanya di tabel kosong, tombol bawah hanya
    yang berguna saat itu."""
    gui, mods = gui
    from collect_files_plus import collector
    mc = make_plugin_tree(tmp_path)
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)])
    monkeypatch.setattr(collector, "Environment", lambda: env)
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    assert app.nb.tab_texts() == ["Comp & opsi", "Plugin", "Font", "Footage", "Semua efek", "Batch", "Log"]
    checks = [w for w in _widgets(root) if type(w).__name__ == "Checkbutton"]
    names = ["Footage", "Font", "Plugin", "Reduce Project", "Lewati efek yang dimatikan",
             "File pendukung plugin", "Preset animasi (.ffx)"]
    assert [w.kw["text"] for w in checks] == names * 2         # panel opsi di mode satu project + batch
    assert checks[0].kw["variable"] is checks[7].kw["variable"]   # centangnya sama
    boxes = {w.kw["text"]: w for w in checks}
    assert all("\n" not in t for t in boxes)                       # tidak ada lagi label 2 baris
    assert "relink" in boxes["Footage"].tooltip.text and "Adobe Fonts" in boxes["Font"].tooltip.text
    texts = " | ".join(root.all_texts())
    assert "Centang comp utama" not in texts and "File plugin yang akan dicopy" not in texts
    # tombol bawah: belum ada proses / hasil -> hanya Analisa & Collect
    assert not getattr(app.btn_cancel, "packed", False) and not getattr(app.progress, "packed", False)
    assert not getattr(app.btn_open, "packed", False)

    app.var_aep.set(str(make_fx_project(tmp_path)))
    app.load_project()
    assert app.btn_cancel.packed and app.progress.packed         # Batal muncul selama proses
    _finish(app)
    assert not app.btn_cancel.packed and not app.progress.packed
    app.opt_fonts.set(False)
    app.start_analyze()
    _finish(app)
    rows = app.plugin_tree.tree.items
    assert sorted(r["values"][2] for r in rows.values()) == ["Pasti", "Pasti", "Pasti"]
    kaca = [i for i, l in app.plugin_tree.labels.items() if l.endswith("Kaca.aex")][0]
    assert app.plugin_tree.labels[kaca] == "MediaCore/VendorA/Kaca.aex"   # tanpa awalan "(perkiraan)"
    tip = app.plugin_tree.tip.tip_at(kaca, "#2")
    assert tip.startswith(str(mc)) and "Cara ketemu: isi file" in tip
    assert app.font_tree.empty_text == 'Tidak dicek: opsi "Font" dimatikan.'
    assert app.fx_tree.tree.items and all(len(r["values"]) == 5 for r in app.fx_tree.tree.items.values())
    assert not getattr(app.btn_open, "packed", False)
    app.var_dest.set(str(tmp_path / "out"))
    app.start_collect()
    _finish(app)
    assert app.btn_open.packed                                    # sudah ada hasil -> tombol muncul

    # mode batch: baris Project disembunyikan, hanya tab Batch + Log
    app.set_mode("batch")
    assert not app.ent_aep.gridded and not app.lbl_aep.gridded and app.nb.visible_texts() == ["Batch", "Log"]
    assert app.batch_tree.empty_label.placed and "Drag file .aep atau folder" in app.batch_tree.empty_text
    pick = [w for w in _widgets(root) if type(w).__name__ == "Label" and w.kw.get("text") == "Pilih comp:"][0]
    assert "Render Queue" in pick.tooltip.text
    app.set_mode("single")
    assert app.ent_aep.gridded and app.nb.visible_texts()[0] == "Comp & opsi"


def test_gui_batch_mode_and_comp_selection(gui, tmp_path, monkeypatch):
    """Mode batch terpisah dari tab project; comp yang di-collect dipilih per project."""
    gui, mods = gui
    from collect_files_plus import collector
    env = env_for(tmp_path)
    monkeypatch.setattr(collector, "Environment", lambda: env)
    a = make_project(tmp_path / "A")                 # 3 comp, tanpa Render Queue / comp aktif -> semua
    fx = make_fx_project(tmp_path)                   # 1 comp (comp aktif)
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    assert app.var_mode.get() == "single" and app.nb.visible_texts() == [
        "Comp & opsi", "Plugin", "Font", "Footage", "Semua efek", "Log"]
    app.add_batch_paths([str(a), str(fx)])
    assert app.var_mode.get() == "batch" and app.nb.visible_texts() == ["Batch (2)", "Log"]
    ea, ef = app.batch_entries
    assert _rows(app)[0][0] == "membaca comp..."
    _scanned(app)
    tree = app.batch_tree.tree
    ids = {c[1]: c[0] for c in ea.comps}
    assert [r[0] for r in _rows(app)] == ["semua comp (3)", "semua comp (1)"]
    assert len(tree.get_children(ea.iid)) == 3 and tree.items[ea.iid]["text"].startswith(gui.CHECK_ON)
    main = "%s/%d" % (ea.iid, ids["Main"])
    assert tree.items[main]["text"] == gui.CHECK_ON + "Main"
    assert tree.items["%s/%d" % (ea.iid, ids["Precomp Logo"])]["values"][0] == "precomp di 1 comp"

    click = type("E", (), {"x": 1, "y": 1})()
    tree.row_at = "%s/%d" % (ea.iid, ids["Template Tak Dipakai"])
    app._batch_click(click)                            # hapus centang satu comp
    assert ea.checked == {ids["Main"], ids["Precomp Logo"]} and _rows(app)[0][0] == "Precomp Logo, Main"
    assert tree.items[ea.iid]["text"].startswith(gui.CHECK_PART)
    tree.element_at = "Treeitem.indicator"           # klik panah buka/tutup: centang tidak berubah
    app._batch_click(click)
    tree.element_at = "text"
    assert len(ea.checked) == 2
    tree.row_at = ea.iid
    app._batch_click(click)                            # centang project (sebagian) -> semua comp
    assert len(ea.checked) == 3
    app._batch_click(click)                            # sekali lagi -> tidak ada (dilewati)
    assert ea.checked == set() and _rows(app)[0][0] == "tidak ada (dilewati)"

    tree.selection_set([ea.iid])
    app.batch_select("rq")                             # project A tidak punya Render Queue: tidak berubah
    assert ea.checked == set() and "Pilihan tidak diubah di 1 project" in app.var_status.get()
    tree.selection_set([])
    app.batch_select("all")                            # tanpa pilihan baris -> semua project
    assert len(ea.checked) == 3 and len(ef.checked) == 1
    tree.selection_set([main])
    app._batch_space()                                 # spasi pada baris comp
    app.batch_select("active")                         # project A juga tidak punya comp aktif
    assert ids["Main"] not in ea.checked
    tree.row_at = ef.iid
    app._batch_click(click)                            # project fx tidak dicentang -> dilewati

    out = tmp_path / "out"
    app.var_dest.set(str(out))
    app.start_collect()
    _finish(app)
    assert [it.status for it in app.batch_run.items] == ["catatan", "dilewati"]
    assert sorted(app.batch_run.items[0].scope_names) == ["Precomp Logo", "Template Tak Dipakai"]
    assert _rows(app)[1][1] == "dilewati: tidak ada comp yang dicentang"
    assert [d.name for d in out.iterdir() if d.is_dir()] == ["Proyek Saya_Collected"]

    # semua project tidak dicentang -> tidak bisa dijalankan
    app.batch_select("none")
    app.start_analyze()
    assert app.worker is None or not app.worker.is_alive()
    assert any("Belum ada comp yang dicentang" in m for _k, m in mods["tkinter.messagebox"].log)

    # pilihan cepat sebelum comp selesai dibaca dipakai begitu daftarnya terbaca
    late = app._new_entry(a)
    app.batch_entries.append(late)
    app._refresh_batch()
    tree.selection_set([late.iid])
    app.batch_select("rq")
    assert late.pending == "rq" and _rows(app)[2][0] == "Render Queue"
    app._on_batch_comps(late.iid, (list(ea.comps), {ids["Main"]}, ""))
    assert late.checked == {ids["Main"]}              # tidak ada Render Queue -> pilihan awal project
    assert late.scope() == [ids["Main"]]

    # ganti bahasa: mode, daftar, dan centang tetap
    app.change_language("en")
    assert app.var_mode.get() == "batch" and app.nb.visible_texts() == ["Batch (3)", "Log"]
    assert app.batch_tree.tree.items[late.iid]["values"][0] == "Main"
    assert (app.btn_analyze.kw["text"], app.btn_collect.kw["text"]) == ("Analyze all", "Collect all")
    app.set_mode("single")
    assert app.nb.visible_texts()[0] == "Comps & options" and app.btn_collect.kw["text"] == "Collect"


def test_gui_japanese_ui_has_no_indonesian(gui, tmp_path, monkeypatch):
    gui, mods = gui
    from collect_files_plus import collector
    from test_i18n import _indonesian_words
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
    app.add_batch_paths([str(tmp_path / "fx")])
    app.change_language("ja")
    texts = root.all_texts()
    assert "すべて分析" in texts and "すべて収集" in texts               # tab Batch aktif
    assert app.nb.tab_texts() == ["コンポとオプション", "プラグイン (3)", "フォント (1)", "フッテージ (0)",
                                  "すべてのエフェクト (7)", "バッチ (1)", "ログ"]
    assert [e["label"] for e in app.menubar.entries] == ["ファイル", "設定", "ヘルプ"]
    values = [str(v) for t in app._trees() for r in t.items.values() for v in [r["text"]] + r["values"]]
    assert _indonesian_words(" | ".join(texts + values)) == []
    assert app.plugin_total.kw["text"].startswith("3/3 チェック · ")


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

    # build exe Windows (zip): download -> extract -> skrip pemasang -> aplikasi ditutup
    monkeypatch.setattr(updater, "update_mode", lambda i: "zip")
    calls = []
    monkeypatch.setattr(updater, "download", lambda i, d, progress=None, cancel=None, kind="zip":
                        (progress(10, 20), progress(20, 20), calls.append(("dl", d, kind)), d / "u.zip")[-1])
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
    assert kinds == ["dl", "ex", "apply"] and calls[2][3] == "9.9.0" and calls[0][2] == "zip"
    assert calls[2][1] == calls[2][2] / "baru" / "CollectFilesPlus"
    assert root.destroyed
    assert any(k == "askyesno" and "dibuka lagi otomatis" in m for k, m in mods["tkinter.messagebox"].log)


def test_gui_update_msi(gui, tmp_path, monkeypatch):
    """Dipasang lewat .msi: installer baru diunduh lalu dijalankan (tanpa extract)."""
    gui, mods = gui
    from collect_files_plus import updater
    info = updater.UpdateInfo("9.9.0", "v9.9.0", "p", asset_url="u.zip", msi_name="u.msi", msi_url="u.msi")
    monkeypatch.setattr(updater, "update_mode", lambda i: "msi")
    calls = []
    monkeypatch.setattr(updater, "download", lambda i, d, progress=None, cancel=None, kind="zip":
                        calls.append(("dl", kind)) or d / "u.msi")
    monkeypatch.setattr(updater, "extract_app", lambda z, d: calls.append(("ex",)))
    monkeypatch.setattr(updater, "launch_msi", lambda msi, tmp, ver: calls.append(("msi", msi.name, ver)))
    root = mods["tkinter"].Tk()
    app = gui.App(root)
    app.update_info = info
    app._show_update_bar()
    assert app.btn_update.kw["text"] == "Update sekarang"
    mods["tkinter.messagebox"].answer_yes = True
    app.start_update()
    _finish(app)
    assert calls == [("dl", "msi"), ("msi", "u.msi", "9.9.0")] and root.destroyed
    assert any(k == "askyesno" and "UAC" in m for k, m in mods["tkinter.messagebox"].log)


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
    app.change_language("en")
    assert app.update_bar.packed
    assert app.update_label.kw["text"] == "New version 9.9.0 is available (you have %s)." % gui.__version__
    app.hide_update_bar()
    app.change_language("id")
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


def ttk_rowheight(root):
    from tkinter import ttk
    return ttk.Style(root).configure("Treeview", "rowheight")


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
        monkeypatch.setattr(real_gui.dialogs, "show", lambda root, title, text, kind="showinfo", **kw:
                            shown.append((kind, (title, text))) and False)
        monkeypatch.setattr(real_gui, "settings_path", lambda: tmp_path / "settings.json")
        monkeypatch.setattr(real_gui, "open_folder", lambda p: None)
        from collect_files_plus import collector
        env = env_for(tmp_path)
        monkeypatch.setattr(collector, "Environment", lambda: env)
        proj = make_project(tmp_path)

        app = real_gui.App(root)
        root.update()
        # tampilan ringkas: petunjuk di daftar kosong, tombol bawah hanya yang berguna
        assert app.comp_tree.empty_label.winfo_manager() == "place"
        assert app.btn_cancel.winfo_manager() == "" and app.btn_open.winfo_manager() == ""
        def walk(w):
            yield w
            for c in w.winfo_children():
                yield from walk(c)
        tip = next(w.tooltip for w in walk(root) if hasattr(w, "tooltip"))      # opsi pertama: Footage
        tip._show()
        root.update()
        assert tip.win is not None and tip.win.winfo_exists() and "relink" in tip.text
        tip._hide()
        try:
            import sv_ttk  # noqa: F401
        except ImportError:
            sv_ttk = None
        if sv_ttk is not None:                         # tema Sun Valley benar-benar terpasang
            from tkinter import ttk
            assert app.theme_name in ("light", "dark")
            assert ttk.Style(root).theme_use().startswith("sun-valley")
            assert str(app.btn_collect.cget("style")) == "Accent.TButton"
            # kotak centang di tabel = gambar Checkbutton tema (bukan karakter ☑ ☐)
            assert app.check_images and set(app.check_images) == {"on", "off", "part"}
        assert str(app.log.cget("state")) == "disabled"
        assert int(ttk_rowheight(root)) >= app.px(24)
        app.var_aep.set(str(proj))
        app.load_project()
        _finish(app)
        root.update()
        assert len(app.comp_tree.tree.get_children()) == 3
        assert app.comp_tree.empty_label.winfo_manager() == ""      # petunjuk hilang
        first = app.comp_tree.tree.get_children()[0]
        assert _shows(app, app.comp_tree.tree, first, "on")
        app.var_dest.set(str(tmp_path / "out"))
        app.start_analyze()
        _finish(app)
        root.update()
        assert app.analysis is not None
        assert len(app.foot_tree.tree.get_children()) >= 4
        app.change_language("en")                  # bangun ulang widget asli dalam bahasa lain
        root.update()
        assert app.nb.tab(0, "text") == "Comps & options" and app.var_lang.get() == "en"
        app.change_language("ja")                  # font Jepang + tinggi baris tabel ikut diatur ulang
        root.update()
        assert app.nb.tab(0, "text") == "コンポとオプション"
        app.var_theme.set("dark")
        app._on_theme_menu()                       # tema gelap dengan widget asli
        root.update()
        app.var_theme.set("light")
        app._on_theme_menu()
        assert len(app.foot_tree.tree.get_children()) >= 4
        app.change_language("id")
        root.update()
        assert app.nb.tab(0, "text") == "Comp & opsi"
        from collect_files_plus import updater
        app.update_info = updater.UpdateInfo("9.9.0", "v9.9.0", "p", asset_url="u")
        app._show_update_bar()                     # bar update dengan widget asli
        root.update()
        assert app.update_bar.winfo_manager() == "pack"
        app.hide_update_bar()
        root.update()
        assert app.update_bar.winfo_manager() == ""
        # mode batch dengan widget asli: daftar project bertingkat, centang comp per project
        app.add_batch_paths([str(proj)])
        _scanned(app)
        root.update()
        entry = app.batch_entries[0]
        kids = app.batch_tree.tree.get_children(entry.iid)
        assert len(kids) == 3 and app.nb.tab(app.batch_tab, "state") == "normal"
        assert app.nb.tab(app.single_tabs[0], "state") == "hidden" and app.ent_aep.winfo_manager() == ""
        app._batch_toggle(kids[0])
        root.update()
        assert _shows(app, app.batch_tree.tree, entry.iid, "part")
        app.set_mode("single")
        root.update()
        assert app.nb.tab(app.batch_tab, "state") == "hidden" and app.ent_aep.winfo_manager() == "grid"
        app.start_collect()
        _finish(app)
        root.update()
        assert app.result is not None and app.result.saved_ok, shown
        assert not [s for s in shown if s[0] == "showerror"], shown
        assert app.btn_open.winfo_manager() == "pack" and app.btn_cancel.winfo_manager() == ""
    finally:
        _clear(root)


def test_real_tk_themed_dialog(real_root):
    """Kotak pesan bertema dengan Tk asli: Ya/Enter -> True, Tidak/Escape -> False, info -> True."""
    root = real_root
    _clear(root)
    from collect_files_plus import dialogs
    try:
        answers = []

        def when_open(action):
            """Jalankan action(dialog) begitu dialog tampil (dicoba lagi kalau belum)."""
            win = dialogs.current
            if win is None or not win.winfo_viewable():
                root.after(50, lambda: when_open(action))
                return
            answers.append(True)
            action(win)
        root.after(100, lambda: when_open(lambda w: w.answer(True)))
        assert dialogs.show(root, "Collect Files Plus", "Buka folder hasil?", "askyesno", dark=True) is True
        root.after(100, lambda: when_open(lambda w: w.answer(False)))
        assert dialogs.show(root, "Collect Files Plus", "Buka folder hasil?", "askyesno", dark=False) is False
        root.after(100, lambda: when_open(lambda w: w.destroy()))   # ditutup lewat tombol X
        assert dialogs.show(root, "Collect Files Plus", "Selesai.", "showinfo", dark=True) is True
        assert answers == [True, True, True] and dialogs.current is None
    finally:
        _clear(root)


def test_real_tk_flyout_menu(real_root):
    """Menu bertema dengan Tk asli: tampil, submenu, pilih item, Escape."""
    import tkinter as tk
    from collect_files_plus import menus
    root = real_root
    _clear(root)
    try:
        var = tk.StringVar(root, value="a")
        ran = []
        top = menus.FlyoutMenu(root)
        sub = menus.FlyoutMenu(root)
        sub.add_radiobutton(label="A", value="a", variable=var)
        sub.add_radiobutton(label="B", value="b", variable=var, command=lambda: ran.append("B"))
        top.add_command(label="Open", accelerator="Ctrl+O", command=lambda: ran.append("open"))
        top.add_separator()
        top.add_cascade(label="Choose", menu=sub)
        top.tk_popup(40, 40)
        root.update()
        assert top.win.winfo_viewable() and top.win.winfo_reqwidth() > 50
        top._hover(2)
        root.update()
        assert sub.is_open and sub.win.winfo_viewable()
        assert sub.win.winfo_rootx() >= top.win.winfo_rootx() + top.win.winfo_width() - 10
        sub._click(1)
        root.update()
        assert var.get() == "b" and ran == ["B"] and not top.is_open and not sub.is_open
        top.tk_popup(40, 40)
        root.update()
        top._key("<Down>")
        top._key("<Return>")
        root.update()
        assert ran == ["B", "open"] and not top.is_open
        top.tk_popup(40, 40)
        root.update()
        top._key("<Escape>")
        root.update()
        assert not top.is_open
        top.destroy()
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
        monkeypatch.setattr(real_gui.dialogs, "show", lambda *a, **kw: False)
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
        assert app.nb.tab(0, "text") == "Comps & options"
        assert len(app.batch_paths) == 2
        app.change_language("id")
    finally:
        _clear(root)
