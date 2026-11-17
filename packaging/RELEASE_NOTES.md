Collect Files for After Effects **without opening After Effects**: the footage, fonts and plugin files a project actually uses are gathered into one folder.

### What's new in 1.0.1

- Fixed: dropping files onto the app window made the app close.

### Download

| System | File |
|---|---|
| Windows 10/11 64-bit | `CollectFilesPlus-v…-windows-x64.zip` → extract → run `CollectFilesPlus.exe` |
| macOS Apple Silicon (experimental) | `CollectFilesPlus-v…-macos-arm64.zip` → extract → open `CollectFilesPlus.app` |

- **Windows SmartScreen:** the exe is not code-signed yet, so click **More info → Run anyway**.
- **macOS:** if you see *"app is damaged"*, run `xattr -dr com.apple.quarantine CollectFilesPlus.app`.
- **Updates:** the app checks for new versions when it starts. Click **Update now** to install them automatically.

### Features

- Reads the `.aep` directly. After Effects does not need to be open.
- Copies footage and relinks the project to it. Image sequences are copied in full and missing files are reported.
- Collects the fonts used by text layers. Adobe Fonts are reported, not copied.
- Copies **only the plugin files whose effects are actually used**, never whole vendor folders. Renamed effects are still recognized by their match name.
- **Batch:** collect many projects at once into one destination folder. Add them by drag & drop or with the right-click **Send to** menu.
- Writes `_report.txt` and `_effect_list.csv`, which lists every effect on every layer.
- Your original `.aep` is never modified.
- Available in **English and Indonesian**. Switch with "Bahasa / Language" at the top right.
- A JSX script for running inside After Effects is in the `jsx` folder of the zip.

Quick start: `READ_ME_FIRST.txt` inside the zip.

**Important:** copying plugin files does not transfer their licenses. Paid plugins still need their official installer and activation on the target computer.
