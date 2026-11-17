"""Menu drop-down bertema (FlyoutMenu): mouse, keyboard, klik di luar."""

import fake_tkinter


def _event(x, y):
    return type("E", (), {"x_root": x, "y_root": y})()


def test_flyout_menu_mouse_keyboard_and_outside_click(monkeypatch):
    _gui, mods = fake_tkinter.install(monkeypatch)
    from collect_files_plus import menus
    tk = mods["tkinter"]
    root = tk.Tk()
    ran = []
    var = tk.StringVar(value="a")
    flag = tk.BooleanVar(value=False)
    top = menus.FlyoutMenu(root)
    sub = menus.FlyoutMenu(root)
    sub.add_radiobutton(label="A", value="a", variable=var, command=lambda: ran.append("A"))
    sub.add_radiobutton(label="B", value="b", variable=var, command=lambda: ran.append("B"))
    top.add_command(label="Open", command=lambda: ran.append("open"), accelerator="Ctrl+O")
    top.add_command(label="Disabled", state="disabled", command=lambda: ran.append("x"))
    top.add_separator()
    top.add_cascade(label="Choose", menu=sub)
    top.add_checkbutton(label="Flag", variable=flag, command=lambda: ran.append("flag"))
    assert top.labels() == ["Open", "Disabled", "Choose", "Flag"]

    # keyboard: item non-aktif dan pemisah dilewati, panah kanan membuka submenu, Enter memilih
    top.tk_popup(10, 20)
    assert top.is_open and top.popped == (10, 20) and top.win.grabbed
    assert [c.kw["text"] for c in top.rows[0][1]] == ["", "Open", "Ctrl+O", ""]
    assert top.rows[3][1][3].kw["text"] == menus.ARROW
    top._key("<Down>")
    assert top.active == 0
    top._key("<Down>")
    assert top.active == 3
    top._key("<Right>")
    assert sub.is_open and top.child is sub and sub.active == 0
    assert sub.rows[0][1][0].kw["text"] == menus.BULLET            # pilihan sekarang ditandai
    top._key("<Down>")
    assert sub.active == 1
    top._key("<Left>")
    assert not sub.is_open and top.is_open
    top._key("<Right>")
    top._key("<Down>")
    top._key("<Return>")
    assert var.get() == "b" and ran == ["B"] and not top.is_open and not sub.is_open

    # mouse: arahkan ke submenu membukanya, item non-aktif tidak bisa diklik, checkbutton berganti
    top.tk_popup(10, 20)
    top._hover(3)
    assert sub.is_open
    top._hover(0)
    assert not sub.is_open
    assert top.rows[0][1][1].kw["background"] == top.kw["activebackground"]
    top._click(1)
    assert top.is_open and ran == ["B"]
    top._click(4)
    assert flag.get() is True and ran[-1] == "flag" and not top.is_open

    # klik di luar menutup menu (dan memberi tahu pemiliknya); klik di dalam tidak
    outside = []
    top.on_outside = lambda menu, x, y: outside.append((menu, x, y))
    top.tk_popup(10, 20)
    top._press(_event(5, 5))
    assert top.is_open
    top._press(_event(900, 900))
    assert not top.is_open and outside == [(top, 900, 900)]
    top.tk_popup(10, 20)
    top._key("<Escape>")
    assert not top.is_open

    # menu di tepi layar digeser masuk
    top.tk_popup(1900, 1050)
    assert top.win.geom == "+%d+%d" % (1920 - 200, 1080 - 100)
    top.destroy()
    assert not top.is_open and top.destroyed and sub.destroyed


def test_flyout_menu_dark_colors(monkeypatch):
    _gui, mods = fake_tkinter.install(monkeypatch)
    from collect_files_plus import menus, theme
    root = mods["tkinter"].Tk()
    menu = menus.FlyoutMenu(root)
    theme.style_menu(menu, True)
    menu.add_command(label="Open")
    menu.add_separator()
    menu.add_command(label="Exit")
    menu.tk_popup(0, 0)
    outer = menu.win.children_list[0]
    inner = outer.children_list[0]
    assert outer.kw["background"] == "#4a4a4a" and inner.kw["background"] == "#2c2c2c"
    labels = [w for w in inner.children_list if w.kw.get("text")]
    assert all(w.kw["background"] == "#2c2c2c" and w.kw["foreground"] == "#f2f2f2" for w in labels)
    separator = [w for w in inner.children_list if w.kw.get("height") == 1]
    assert len(separator) == 1 and separator[0].kw["background"] == "#4a4a4a"   # garis abu, bukan putih
    assert menus.is_dark("#2c2c2c") and not menus.is_dark("#f9f9f9")
