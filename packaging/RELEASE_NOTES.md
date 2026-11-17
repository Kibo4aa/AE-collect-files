Collect Files for After Effects **without opening After Effects**: the footage, fonts and plugin files a project actually uses are gathered into one folder.

### What's new in 1.1.0

- **New look:** a modern light/dark theme that follows Windows, a menu bar (File, Settings, Help), colored statuses, item counts on the tabs, tooltips for long paths, a right-click menu in the Batch list and keyboard shortcuts (Ctrl+O, F5, Ctrl+Enter, Esc, F1). The window remembers its size.
- **日本語 (Japanese):** the app, the reports and the command line are now available in Japanese, as well as English and Indonesian. Switch in **Settings > Bahasa / Language / 言語**.
- **Easier reports:** `_report.txt` starts with a short summary of what is done and what needs checking (`[OK]` / `[!]` / `[i]`), then the steps for the other computer, then the details. The batch summary lists the projects that need attention first. Reports are written in the language you choose.
- **Windows installer (.msi):** installs to Program Files with Start menu and desktop shortcuts, and uninstalls from Settings > Apps. In-app updates run the new installer automatically.
- **Faster:** plugin scan results are cached between runs, image sequences are copied in parallel, and the project is no longer reloaded after every collect.
- **Help > How to use** opens a short guide in your language.

### Download

| System | File |
|---|---|
| Windows 10/11 64-bit, installer | `CollectFilesPlus-v…-windows-x64.msi` → run it, then open Collect Files Plus from the Start menu |
| Windows 10/11 64-bit, portable | `CollectFilesPlus-v…-windows-x64.zip` → extract → run `CollectFilesPlus.exe` |
| macOS Apple Silicon (experimental) | `CollectFilesPlus-v…-macos-arm64.zip` → extract → open `CollectFilesPlus.app` |

- **Already using the portable version?** Click **Update now** in the app and it updates itself as before. To switch to the installer, install the `.msi` and delete the old folder.
- **Windows SmartScreen:** the app is not code-signed yet, so click **More info → Run anyway**.
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
- Available in **English, Indonesian and Japanese**.
- A JSX script for running inside After Effects is in the `jsx` folder.

Quick start: `README_EN.txt` (Indonesian: `README_ID.txt`, Japanese: `README_JA.txt`), or **Help > How to use** in the app.

**Important:** copying plugin files does not transfer their licenses. Paid plugins still need their official installer and activation on the target computer.
