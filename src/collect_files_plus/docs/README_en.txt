COLLECT FILES PLUS for After Effects
====================================
https://github.com/Kibo4aa/AE-collect-files

Collects everything an After Effects project needs into one folder:
footage, fonts, and only the plugin files whose effects are actually used.
It reads the .aep file directly, so After Effects does not need to be open.
Your original .aep is never changed.


QUICK START
-----------
1. Open Collect Files Plus.
2. Drag an .aep file onto the window (or File > Open project...).
3. Tab "1. Comps & options": tick the main comps you render.
   Precomps inside them are included automatically.
4. Click Analyze (F5), then check the Plugins, Fonts and Footage tabs.
   Untick any plugin file you don't want to copy.
5. Choose a destination folder and click Collect (Ctrl+Enter).
6. Open the output folder and read <project>_report.txt first.


MANY PROJECTS AT ONCE (BATCH)
-----------------------------
- Drag several .aep files, or a folder, onto the window. They are added to
  the "Batch (many projects)" tab.
- While the Batch tab is open, the buttons at the bottom work on the whole
  list: "Analyze all" (F5) checks every project without copying anything,
  "Collect all" (Ctrl+Enter) collects them.
- Every project goes into the same destination folder, each one into its
  own <name>_Collected folder. One failing project does not stop the others.
- CollectFilesPlus_batch_<date>.txt in the destination folder lists what
  needs checking first, then every project.
- Right-click a project in the list to see its analysis in detail
  (plugins, fonts, footage), or to open its output folder or report.
- From Windows Explorer: turn on Settings > Right-click "Send to" menu in
  Explorer. Then select .aep files > right-click > Send to >
  Collect Files Plus (Windows 11: click "Show more options" first).


WHAT IS IN THE OUTPUT FOLDER
----------------------------
<project>_report.txt       START HERE: summary, next steps, then details
<project>.aep              the collected project, relinked to (Footage)
<project>_effect_list.csv  every effect on every layer (opens in Excel)
(Footage)                  copied footage, sorted by original folder name
(Fonts)                    font files used by text layers
(Plugins)                  only the plugin files whose effects are used
(PresetEffects)            effect definitions from PresetEffects.xml
(Presets)                  animation presets (.ffx), if that option is on
(Backup)                   untouched copy of your original .aep

In the report and the batch summary:
  [OK] = done    [!] = check this    [i] = information


ON THE OTHER COMPUTER
---------------------
1. Install the fonts in (Fonts). Adobe Fonts: activate them in Creative Cloud.
2. Close After Effects and copy the plugin files from (Plugins) to the
   folders listed in the report. Skip plugins that are already installed.
   Paid plugins still need their official installer and license.
3. Open the .aep. The footage is found automatically.


MENUS AND SHORTCUTS
-------------------
Settings > Bahasa / Language / 言語
    English, Bahasa Indonesia or 日本語. Reports, summaries and the
    effect list are written in the language you choose.
Settings > Theme
    Follow Windows, Light or Dark.
Settings > Check for updates when the app opens
Help > How to use (F1)      opens this file
Help > Check for updates...

Ctrl+O  open project      F5  analyze      Ctrl+Enter  collect
Esc     cancel            F1  help
Double-click a row in the Plugins, Fonts or Footage tab to show the file.


UPDATES
-------
When a new version is available, a bar appears at the top of the window.
Click "Update now": the app downloads it, installs it and opens again.
- Installed with the .msi installer: the new installer runs by itself.
  Windows may ask for permission (UAC).
- Portable .zip: the files are replaced. If anything fails, the old
  version is restored.


INSTALLER (.msi) OR PORTABLE (.zip)
-----------------------------------
CollectFilesPlus-v<version>-windows-x64.msi
    Installs to C:\Program Files\Collect Files Plus, with Start menu and
    desktop shortcuts. Uninstall it from Settings > Apps.
CollectFilesPlus-v<version>-windows-x64.zip
    Extract anywhere and run CollectFilesPlus.exe.
    To remove it, delete the folder.
Settings are kept in %APPDATA%\CollectFilesPlus and the cache in
%LOCALAPPDATA%\CollectFilesPlus (safe to delete).


TROUBLESHOOTING
---------------
- "Windows protected your PC": click More info > Run anyway
  (the app is not code-signed yet).
- The .aep cannot be read: a project saved by a very new version of
  After Effects may not be supported yet. Use the script instead:
  in After Effects, File > Scripts > Run Script File... and choose
  jsx\CollectFilesPlus.jsx (first turn on "Allow Scripts to Write Files and
  Access Network" in Preferences > Scripting & Expressions).
- A plugin is marked [!] or "guess": check the plugin file shown in the
  report before you copy it.
- Command line: collect-files-plus.exe --help


License: MIT (LICENSE). Third-party notices: NOTICE.md.
