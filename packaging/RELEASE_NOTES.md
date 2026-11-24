Collect Files for After Effects **without opening After Effects**: the footage, fonts and plugin files a project actually uses are gathered into one folder.

### What's new in 1.3.0

- **Batch is its own mode.** Switch between **Single project** and **Many projects (batch)** at the top. The batch list no longer sits between the project tabs (Plugins, Fonts, Footage, All effects); in batch mode you see the project list, the collect options and the Log.
- **Choose the comps for each project.** Click the arrow next to a project to see its comps and tick the ones to collect. Ticking the project row ticks or unticks all of its comps, and a project with nothing ticked is skipped. New projects start with their Render Queue comps ticked (otherwise the active comp, otherwise all comps). The **Select comps** buttons (Render Queue, Active comp, All, Clear) change the selected projects, or every project.
- **Cleaner window.** The long explanations above the Comps, Plugins and Batch lists are gone. Tabs have short names without numbers: Comps & options, Plugins, Fonts, Footage, All effects, Batch, Log.
- **Short options with tooltips.** The options are split into **What to collect** (Footage, Fonts, Plugins) and **Options** (Reduce Project, Skip effects that are off, Plugin support files, Animation presets). Hover over an option to see what it does.
- **Plugins tab:** a simple **Sure / Guess** column replaces the technical "Found via" column. Hover over a row for the full path and how the plugin was found. The All effects tab no longer repeats the effect type.
- **Helpful empty lists:** an empty list tells you what to do next, for example "Drag an .aep file here", "Click Analyze", or that an option is turned off.
- **Bottom bar shows only what you can use:** Cancel and the progress bar appear only while something is running, and **Open output folder** appears once there is a result. The Project field is hidden in batch mode, where it is not used.

### What's new in 1.2.0

- **Batch tab: one set of buttons.** While the Batch tab is open, the buttons at the bottom become **Analyze all** and **Collect all** and work on the whole list. The extra "Collect all projects" button inside the tab is gone, so there is only one Collect button.
- **Analyze all (new):** checks every project in the list without copying anything. Each row shows what needs attention (missing footage, fonts or plugins that were not found) and what a collect would copy: footage, fonts, plugin files and the total size.
- **One project in detail:** right-click a project in the Batch list and choose **Show analysis details**, or double-click a project that has not been collected yet. It opens in the Plugins, Fonts and Footage tabs, ready to collect on its own.
- F5 and Ctrl+Enter follow the same rule: on the Batch tab they run Analyze all and Collect all.

### What's new in 1.1.1

- **Dark mode fixed:** the menu bar, the drop-down menus and the message boxes now follow the dark theme. No more white menu bar, white menu borders or white dialogs.
- Menus work with the mouse and the keyboard (Alt+F, Alt+S, Alt+H, arrow keys, Enter, Esc). Clicking outside closes a menu, and clicking another menu while one is open switches to it.
- Changing the theme updates the whole window at once.

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
