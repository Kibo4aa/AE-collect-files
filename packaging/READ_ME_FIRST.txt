COLLECT FILES PLUS - for After Effects
======================================
https://github.com/Kibo4aa/AE-collect-files

Collects the footage, fonts and plugin files an After Effects project
actually uses into one folder, straight from the .aep file
(After Effects does not need to be open).

The app follows your system language (Indonesian or English).
Change it any time with "Bahasa / Language" at the top right.

HOW TO USE
1. Run CollectFilesPlus.exe (Mac: CollectFilesPlus.app).
2. Choose an .aep file, or drag an .aep file onto the app window
   (or onto the CollectFilesPlus.exe icon).
3. "1. Comps & options" tab: tick the main comps you render.
   Precomps inside them are read automatically.
4. Click Analyze, then check the Plugins / Fonts / Footage tabs.
   Untick any plugin file you don't want copied.
5. Choose a destination folder and click Collect.
   The output folder contains a report (_report.txt) that explains
   how to use the result on another computer.

MANY PROJECTS AT ONCE (BATCH)
- Drag several .aep files (or a folder with .aep files) onto the app
  window or onto CollectFilesPlus.exe. They go to the
  "Batch (many projects)" tab. Click "Collect all projects".
- Straight from Explorer: in the Batch tab click
  "Add to the right-click Send to menu". Then select .aep files,
  right-click > Send to > Collect Files Plus
  (Windows 11: click "Show more options" first).
- Everything goes into the same destination folder; each project into
  its own <name>_Collected folder. A summary is written to
  CollectFilesPlus_batch_....txt in the destination folder.
- One failing project does not stop the others.
- Command line: collect-files-plus.exe --lang en collect a.aep b.aep -o D:\Output

UPDATES
- On start the app checks GitHub for a newer version. If there is one,
  a "New version ... available" bar appears: click "Update now". The app
  downloads it, replaces its own files and reopens. If anything fails,
  the old version is restored. Manual check: "Check for updates" button
  at the top right.

NOTES
- Windows SmartScreen: click "More info", then "Run anyway"
  (the exe is not code-signed yet).
- Your original .aep is never modified. If the collected project is
  re-saved, a copy of the original is kept in the (Backup) folder.
- Copying plugin files does not transfer their licenses. Paid plugins
  still need their official installer and activation on the target
  computer.
- Adobe Fonts are not copied; activate them again in Creative Cloud.
- The After Effects script version (JSX) is in the jsx folder:
  File > Scripts > Run Script File... (first enable "Allow Scripts to
  Write Files and Access Network" in Preferences > Scripting & Expressions).

License: MIT (LICENSE). Third-party notices: NOTICE.md.
