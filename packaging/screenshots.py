"""Screenshot jendela aplikasi (Windows) untuk mengecek tampilan: tema terang/gelap, tiap bahasa.
Dijalankan oleh workflow "Screenshots" di GitHub Actions; hasilnya ada di Artifacts.

    python packaging/screenshots.py FOLDER_HASIL [SKALA]     (SKALA mis. 1.25 = simulasi layar 125%)
"""

import ctypes
import os
import sys
import tempfile
import threading
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
os.environ["COLLECT_FILES_PLUS_NO_UPDATE_CHECK"] = "1"
os.environ["COLLECT_FILES_PLUS_CACHE_DIR"] = tempfile.mkdtemp(prefix="cfp-cache-")


def window_rect(root):
    """Kotak jendela yang terlihat (termasuk title bar dan menu)."""
    user32, dwm = ctypes.WinDLL("user32"), ctypes.WinDLL("dwmapi")
    user32.GetParent.restype = wintypes.HWND
    user32.GetParent.argtypes = [wintypes.HWND]
    hwnd = user32.GetParent(root.winfo_id())
    rect = wintypes.RECT()
    dwm.DwmGetWindowAttribute(wintypes.HWND(hwnd), 9, ctypes.byref(rect), ctypes.sizeof(rect))  # extended frame
    return rect.left, rect.top, rect.right, rect.bottom


def main() -> int:
    from PIL import ImageGrab

    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass

    import tkinter as tk
    from tkinter import messagebox

    from collect_files_plus import collector, dialogs, gui, updater
    from collect_files_plus.plugins import PluginRoot
    from helpers import env_for, make_fx_project, make_plugin_tree, make_project

    tmp = Path(tempfile.mkdtemp(prefix="cfp-shots-"))
    mc = make_plugin_tree(tmp)
    env = env_for(tmp, plugin_roots=[PluginRoot(mc, "MediaCore", 1)])
    collector.Environment = lambda: env
    fx = make_fx_project(tmp)
    other = make_project(tmp / "Edit AMV")
    gui.settings_path = lambda: tmp / "settings.json"
    gui.open_folder = lambda p: None
    for kind in ("showerror", "showinfo", "showwarning", "askyesno"):
        setattr(messagebox, kind, lambda *a, **kw: False)
    real_show = dialogs.show
    dialogs.show = lambda *a, **kw: False          # alur biasa (batch selesai, dll.) tidak menunggu klik

    scale = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    root = tk.Tk()
    if scale:                                   # simulasi layar dengan skala Windows 125%/150%
        root.tk.call("tk", "scaling", scale * 96 / 72)
    app = gui.App(root)
    prefix = "scale%d-" % round(scale * 100) if scale else ""

    def settle(seconds=0.6):
        end = time.time() + seconds
        while time.time() < end or (app.worker is not None and app.worker.is_alive()):
            root.update()
            app._poll()
            time.sleep(0.03)
        root.update()

    def shot(name):
        settle()
        root.lift()
        root.attributes("-topmost", True)
        settle(0.3)
        ImageGrab.grab(bbox=window_rect(root), all_screens=True).save(out / (prefix + name + ".png"))
        root.attributes("-topmost", False)
        print("saved", name)

    user32 = ctypes.WinDLL("user32")

    def key(vk):
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.25)

    def shot_menu(name, index, submenu=False):
        """Menu drop-down yang sedang terbuka (diambil dari thread lain: tk_popup menunggu sampai menu ditutup)."""
        button, menu = app.menu_buttons[index]

        def worker():
            time.sleep(0.8)
            if submenu:
                key(0x28)                       # panah bawah: item pertama
                key(0x27)                       # panah kanan: buka submenu
            time.sleep(0.6)
            ImageGrab.grab(all_screens=True).save(out / (prefix + name + ".png"))
            print("saved", name)
            for _i in range(3 if submenu else 1):
                key(0x1B)                       # Escape
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()
        settle(0.3)
        t = threading.Thread(target=worker)
        t.start()
        app._post_menu(menu, button)
        t.join()
        root.attributes("-topmost", False)
        settle(0.3)

    def shot_dialog(name, kind, text):
        def capture():
            win = dialogs.current
            if win is None or not win.winfo_viewable():
                root.after(100, capture)
                return
            win.update()
            time.sleep(0.3)
            ImageGrab.grab(bbox=window_rect(win), all_screens=True).save(out / (prefix + name + ".png"))
            print("saved", name)
            win.answer(False)
        root.after(600, capture)
        real_show(root, gui.APP_TITLE, text, kind, dark=app.theme_name == "dark", scale=app.scale)
        settle(0.3)

    settle()
    shot("01-start-en")
    app.var_aep.set(str(fx))
    app.load_project()
    settle()
    app.var_dest.set(str(tmp / "Output"))
    app.start_analyze()
    settle()
    if scale:                                   # layar sempit: cukup cek tombol tetap terlihat
        for tab, label in ((0, "comps"), (1, "plugins")):
            app.nb.select(tab)
            shot("light-en-%d-%s" % (tab + 1, label))
        app.add_batch_paths([str(fx), str(other)])
        shot("light-en-batch")
        app.change_language("ja")
        app.nb.select(0)
        shot("light-ja-1-comps")
        root.destroy()
        return 0
    for theme in ("light", "dark"):
        app.var_theme.set(theme)
        app.change_theme()
        for lang in ("en", "ja", "id"):
            app.change_language(lang)
            for tab, label in ((0, "comps"), (1, "plugins"), (4, "effects")):
                app.nb.select(tab)
                shot("%s-%s-%d-%s" % (theme, lang, tab + 1, label))
        app.change_language("en")
        shot_menu("%s-menu-file" % theme, 0)
        shot_menu("%s-menu-settings" % theme, 1, submenu=True)
        shot_dialog("%s-dialog-question" % theme, "askyesno",
                    "Done.\n\nOutput: D:\\AMV\\Output\\Efek_Collected\n\nOpen the output folder?")
        shot_dialog("%s-dialog-error" % theme, "showerror",
                    "The .aep file could not be read:\nOSError: Short read\n\nDetails are in the Log tab.")
    app.change_language("ja")
    shot_menu("dark-ja-menu-settings", 1, submenu=True)
    app.change_language("en")
    app.var_theme.set("light")
    app.change_theme()
    app.add_batch_paths([str(fx), str(other)])
    app.start_batch()
    settle()
    shot("light-en-batch")
    app.var_theme.set("dark")
    app.change_theme()
    shot("dark-en-batch")
    app.update_info = updater.UpdateInfo("9.9.0", "v9.9.0", "p", asset_url="u")
    app._show_update_bar()
    shot("dark-en-update-bar")
    root.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
