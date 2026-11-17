# -*- mode: python ; coding: utf-8 -*-
# Build:  pyinstaller --noconfirm --clean packaging/CollectFilesPlus.spec
#
# Windows -> dist/CollectFilesPlus/CollectFilesPlus.exe (GUI) + collect-files-plus.exe (CLI)
# macOS   -> dist/CollectFilesPlus.app

import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

HERE = SPECPATH  # noqa: F821  (disediakan PyInstaller)
SRC = os.path.abspath(os.path.join(HERE, "..", "src"))
sys.path.insert(0, SRC)
from collect_files_plus import __version__ as VERSION  # noqa: E402

datas, binaries, hiddenimports = [], [], []
for pkg in ("py_aep", "uharfbuzz"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
hiddenimports += collect_submodules("fontTools.ttLib")
hiddenimports += collect_submodules("collect_files_plus")
datas += [(os.path.join(SRC, "collect_files_plus", "assets"), "collect_files_plus/assets")]

a = Analysis(  # noqa: F821
    [os.path.join(HERE, "launcher.py")],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["pytest", "_pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821


def win_version(description, filename):
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo)
    nums = tuple(int(x) for x in VERSION.split(".")[:3]) + (0,)
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=nums, prodvers=nums, mask=0x3F, flags=0x0, OS=0x40004,
                          fileType=0x1, subtype=0x0, date=(0, 0)),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("CompanyName", "Kibo4aa"),
                StringStruct("FileDescription", description),
                StringStruct("FileVersion", VERSION),
                StringStruct("InternalName", filename),
                StringStruct("LegalCopyright", "MIT License"),
                StringStruct("OriginalFilename", filename + ".exe"),
                StringStruct("ProductName", "Collect Files Plus"),
                StringStruct("ProductVersion", VERSION),
            ])]),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )


if sys.platform == "win32":
    icon = os.path.join(HERE, "icon.ico")
    gui = EXE(  # noqa: F821
        pyz, a.scripts, [], exclude_binaries=True, name="CollectFilesPlus",
        console=False, icon=icon, version=win_version("Collect Files Plus", "CollectFilesPlus"),
        upx=False)
    cli = EXE(  # noqa: F821
        pyz, a.scripts, [], exclude_binaries=True, name="collect-files-plus",
        console=True, icon=icon, version=win_version("Collect Files Plus (command line)", "collect-files-plus"),
        upx=False)
    coll = COLLECT(gui, cli, a.binaries, a.datas, name="CollectFilesPlus", upx=False)  # noqa: F821
else:
    gui = EXE(  # noqa: F821
        pyz, a.scripts, [], exclude_binaries=True, name="CollectFilesPlus",
        console=False, upx=False)
    coll = COLLECT(gui, a.binaries, a.datas, name="CollectFilesPlus", upx=False)  # noqa: F821
    if sys.platform == "darwin":
        app = BUNDLE(  # noqa: F821
            coll,
            name="CollectFilesPlus.app",
            icon=os.path.join(HERE, "icon.icns"),
            bundle_identifier="io.github.kibo4aa.collectfilesplus",
            version=VERSION,
            info_plist={
                "CFBundleDisplayName": "Collect Files Plus",
                "CFBundleShortVersionString": VERSION,
                "NSHighResolutionCapable": True,
                "CFBundleDocumentTypes": [{
                    "CFBundleTypeName": "After Effects Project",
                    "CFBundleTypeRole": "Viewer",
                    "LSHandlerRank": "Alternate",
                    "CFBundleTypeExtensions": ["aep"],
                }],
            },
        )
