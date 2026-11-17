"""Screenshot jendela aplikasi (Windows) untuk mengecek tampilan: tema terang/gelap, tiap bahasa.
Dijalankan oleh workflow "Screenshots" di GitHub Actions; hasilnya ada di Artifacts.

    python packaging/screenshots.py FOLDER_HASIL
"""

import ctypes
import os
import sys
import tempfile
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

    from collect_files_plus import collector, gui, updater
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

    root = tk.Tk()
    app = gui.App(root)
    root.geometry("+0+0")

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
        ImageGrab.grab(bbox=window_rect(root), all_screens=True).save(out / (name + ".png"))
        root.attributes("-topmost", False)
        print("saved", name)

    settle()
    shot("01-start-en")
    app.var_aep.set(str(fx))
    app.load_project()
    settle()
    app.var_dest.set(str(tmp / "Output"))
    app.start_analyze()
    settle()
    for theme in ("light", "dark"):
        app.var_theme.set(theme)
        app._on_theme_menu()
        for lang in ("en", "ja", "id"):
            app.change_language(lang)
            for tab, label in ((0, "comps"), (1, "plugins"), (4, "effects")):
                app.nb.select(tab)
                shot("%s-%s-%d-%s" % (theme, lang, tab + 1, label))
    app.change_language("en")
    app.var_theme.set("light")
    app._on_theme_menu()
    app.add_batch_paths([str(fx), str(other)])
    app.start_batch()
    settle()
    shot("light-en-batch")
    app.var_theme.set("dark")
    app._on_theme_menu()
    shot("dark-en-batch")
    app.update_info = updater.UpdateInfo("9.9.0", "v9.9.0", "p", asset_url="u")
    app._show_update_bar()
    shot("dark-en-update-bar")
    root.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
