"""Terjemahan English. Kunci = teks Indonesia di kode (lihat i18n.py)."""

EN = {
    # ------------------------------------------------------------------ batch
    "otomatis (Render Queue, kalau kosong comp aktif, kalau tidak ada semua comp)":
        "automatic (Render Queue; if empty, the active comp; if none, all comps)",
    "comp di Render Queue": "comps in the Render Queue",
    "comp aktif saat project disimpan": "comp that was active when the project was saved",
    "semua comp": "all comps",
    "comp dengan nama tertentu": "comps with specific names",
    "menunggu": "waiting",
    "sedang diproses...": "processing...",
    "OK, ada catatan": "OK, with notes",
    "GAGAL": "FAILED",
    "dibatalkan": "cancelled",
    "%d footage hilang": "%d missing footage",
    "%d font tidak ketemu": "%d font(s) not found",
    "%d Adobe Fonts (aktifkan di CC)": "%d Adobe Fonts (activate in CC)",
    "%d efek plugin tidak ketemu": "%d plugin effect(s) not found",
    "%d plugin perkiraan tidak dicopy": "%d guessed plugin(s) not copied",
    "%d error saat copy": "%d copy error(s)",
    "[CATATAN]": "[NOTES]",
    "[GAGAL]": "[FAILED]",
    "[DIBATALKAN]": "[CANCELLED]",
    "Detail tiap project ada di file _report.txt di folder hasilnya masing-masing.":
        "Details for each project are in the _report.txt file in its own output folder.",
    "semua comp (%d)": "all comps (%d)",
    "comp aktif": "active comp",
    "%s (dari %d project)": "%s (of %d projects)",
    "Collect Files Plus %s - ringkasan batch": "Collect Files Plus %s - batch summary",
    "Tanggal : %s": "Date    : %s",
    "Folder  : %s": "Folder  : %s",
    "Comp    : %s": "Comps   : %s",
    "Hasil   : %s": "Result  : %s",
    "Render Queue kosong.": "The Render Queue is empty.",
    "Tidak ada comp aktif yang tersimpan di project ini.": "This project has no saved active comp.",
    "GAGAL: %s": "FAILED: %s",
    "             asal    : %s": "             source  : %s",
    "Comp tidak ditemukan: %s": "Comp not found: %s",
    "%d ada catatan": "%d with notes",
    "%d gagal": "%d failed",
    "%d tidak diproses": "%d not processed",
    "Membaca project...": "Reading project...",
    "project hasil gagal dicek (%s); file sudah dicopy, pakai .aep di (Backup)":
        "the collected project failed verification (%s); files were copied, use the .aep in (Backup)",
    "             comp    : %s": "             comps   : %s",
    "             hasil   : %s": "             output  : %s",
    "             catatan : %s": "             notes   : %s",
    "tidak diketahui": "unknown",

    # -------------------------------------------------------------------- cli
    "CATATAN": "NOTES",
    "DIBATALKAN": "CANCELLED",
    "NAMA": "NAME",
    "comp utama (boleh diulang). Precomp di dalamnya ikut dibaca.":
        "main comp (repeatable). Precomps inside it are read too.",
    "comp yang ada di Render Queue": "comps in the Render Queue",
    "semua comp di project": "all comps in the project",
    "jangan collect footage": "don't collect footage",
    "jangan collect font": "don't collect fonts",
    "jangan collect plugin": "don't collect plugins",
    "ikutkan efek yang ikon fx-nya mati": "include effects whose fx switch is off",
    "ikut copy file pendukung plugin (DLL/data di folder yang sama, tanpa plugin lain)":
        "also copy plugin support files (DLLs/data in the same folder, without other plugins)",
    "buang comp & footage yang tidak dipakai dari project hasil (Reduce Project)":
        "remove unused comps & footage from the collected project (Reduce Project)",
    "ikut copy animation preset (.ffx) yang namanya sama dengan efek yang di-rename":
        "also copy animation presets (.ffx) named like renamed effects",
    "ikut copy plugin yang hanya ditemukan lewat perkiraan": "also copy plugins that were only found by guessing",
    "Kumpulkan footage, font, dan plugin dari project After Effects tanpa membuka AE.":
        "Collect footage, fonts and plugins from After Effects projects without opening AE.",
    "bahasa output: id (Indonesia) atau en (English)": "output language: id (Indonesian) or en (English)",
    "daftar comp di project": "list the comps in a project",
    "analisa saja, tidak menyalin apa pun": "analyze only, copy nothing",
    "collect ke folder tujuan (bisa banyak project sekaligus)":
        "collect into a destination folder (several projects at once is fine)",
    "folder tujuan": "destination folder",
    "buka jendela aplikasi": "open the app window",
    "Selesai: %s": "Done: %s",
    "Tidak ada file .aep yang ditemukan.": "No .aep files found.",
    "Collect %d project ke %s": "Collecting %d project(s) to %s",
    "file .aep, boleh lebih dari satu; folder = semua .aep di dalamnya":
        ".aep file(s), more than one is fine; a folder = every .aep inside it",
    "file .aep": ".aep file",
    "File tidak ditemukan: %s": "File not found: %s",
    "Laporan: %s": "Report: %s",
    "PERHATIAN: %s": "WARNING: %s",
    "Tidak ditemukan: %s": "Not found: %s",
    "Ringkasan: %s": "Summary: %s",
    "aktif": "active",
    "precomp di %d comp": "precomp in %d comp(s)",

    # -------------------------------------------------------------- collector
    "Membaca efek...": "Reading effects...",
    "Menulis laporan...": "Writing report...",
    "Membaca daftar font...": "Reading the font list...",
    "Membaca footage...": "Reading footage...",
    "Mencari animation preset (.ffx)...": "Looking for animation presets (.ffx)...",
    "Menyimpan project hasil collect...": "Saving the collected project...",
    "%d footage tidak menunjuk ke file hasil copy (contoh: %s)":
        "%d footage item(s) do not point to the copied files (e.g. %s)",
    "Pencarian plugin dimatikan.": "Plugin search was turned off.",
    "file tidak ada": "file does not exist",
    "Project hasil tidak bisa dibaca ulang: %s": "The collected project could not be read back: %s",
    "PresetEffects_dari_project.xml": "PresetEffects_from_project.xml",
    "<!-- Collect Files Plus: definisi efek dari PresetEffects.xml yang dipakai project ini.":
        "<!-- Collect Files Plus: effect definitions from PresetEffects.xml used by this project.",
    '     Efek dengan match name berawalan "Pseudo/" sudah tersimpan di dalam project,':
        '     Effects whose match name starts with "Pseudo/" are already stored inside the project,',
    "     jadi biasanya tidak perlu dipasang. Efek lainnya: salin blok <Effect> di bawah":
        "     so they usually don't need installing. Other effects: copy the <Effect> blocks below",
    "     ke PresetEffects.xml di komputer tujuan (sebelum tag </Effects> terakhir),":
        "     into PresetEffects.xml on the target computer (before the last </Effects> tag),",
    "     lalu restart After Effects. -->": "     then restart After Effects. -->",
    "Gagal menyimpan project: %s": "Could not save the project: %s",
    "daftar_efek": "effect_list",
    "Reduce Project gagal: %s": "Reduce Project failed: %s",
    "     Asal: %s": "     Source: %s",

    # ------------------------------------------------------------------ fonts
    "Membaca font %d/%d: %s": "Reading font %d/%d: %s",

    # -------------------------------------------------------------------- gui
    'Hapus dari menu klik kanan "Send to"': 'Remove from the right-click "Send to" menu',
    'Pasang di menu klik kanan "Send to"': 'Add to the right-click "Send to" menu',
    "Pilih file .aep untuk mulai.": "Choose an .aep file to start.",
    "1. Comp & opsi": "1. Comps & options",
    "Keterangan": "Info",
    "Yang dikumpulkan": "What to collect",
    "Footage (copy + relink ke folder (Footage))": "Footage (copy + relink to the (Footage) folder)",
    "Buang comp & footage yang tidak dipakai\n(Reduce Project)": "Remove unused comps & footage\n(Reduce Project)",
    "Font yang dipakai text layer": "Fonts used by text layers",
    "Plugin pihak ketiga\n(hanya file plugin yang efeknya dipakai)":
        "Third-party plugins\n(only plugin files whose effects are used)",
    "Lewati efek yang dimatikan (ikon fx mati)": "Skip effects that are switched off (fx off)",
    "Ikut file pendukung plugin\n(DLL/data di folder yang sama)": "Include plugin support files\n(DLLs/data in the same folder)",
    "Ikut animation preset (.ffx) yang\nnamanya sama dengan efek yang di-rename":
        "Include animation presets (.ffx)\nnamed like renamed effects",
    "2. Plugin": "2. Plugins",
    "File plugin": "Plugin file",
    "Efek yang dipakai": "Effects used",
    "Ukuran": "Size",
    "Cara ketemu": "Found via",
    "3. Font": "3. Fonts",
    "Font (PostScript)": "Font (PostScript)",
    "File": "File",
    "Status": "Status",
    "Item": "Item",
    "5. Semua efek": "5. All effects",
    "Efek": "Effect",
    "Nama di layer": "Name on layer",
    "Match name": "Match name",
    "Jenis": "Type",
    "Dipakai": "Used",
    "Batch (banyak project)": "Batch (many projects)",
    "Project": "Project",
    "Lokasi": "Location",
    "Comp": "Comp",
    "Hasil": "Result",
    "Collect semua project": "Collect all projects",
    "Analisa": "Analyze",
    "Batal": "Cancel",
    "Buka folder hasil": "Open output folder",
    "Pilih project After Effects": "Choose an After Effects project",
    "Pilih folder tujuan": "Choose the destination folder",
    "File .aep tidak ditemukan.": "The .aep file was not found.",
    "Buka file .aep dulu.": "Open an .aep file first.",
    'Centang minimal satu comp di tab "1. Comp & opsi".': 'Tick at least one comp in the "1. Comps & options" tab.',
    "Pilih folder tujuan dulu.": "Choose a destination folder first.",
    "Tunggu proses yang sedang berjalan selesai dulu.": "Wait for the running task to finish first.",
    "Bahasa diganti ke %s.": "Language changed to %s.",
    "Yang di-drop bukan file .aep atau folder.": "What you dropped is not an .aep file or a folder.",
    "Pilih project After Effects (boleh banyak)": "Choose After Effects projects (several is fine)",
    "Pilih folder berisi project .aep": "Choose a folder containing .aep projects",
    'Daftar batch masih kosong. Klik "Tambah file .aep..." atau drag file .aep ke jendela ini.':
        'The batch list is empty. Click "Add .aep files..." or drag .aep files onto this window.',
    "Membaca %s ...": "Reading %s ...",
    "akan dicopy": "will be copied",
    "HILANG": "MISSING",
    "Render Queue di project ini kosong.": "The Render Queue in this project is empty.",
    "Tip: drag file .aep ke jendela ini. Banyak file atau folder sekaligus masuk ke tab Batch.":
        "Tip: drag .aep files onto this window. Several files or a folder go to the Batch tab.",
    "%d project ditambahkan ke daftar batch (total %d).": "%d project(s) added to the batch list (total %d).",
    "Collect Files Plus sudah dihapus dari menu Send to.": "Collect Files Plus was removed from the Send to menu.",
    "Terpasang.\n\nCara pakai: di Explorer pilih satu atau banyak file .aep (atau folder), klik kanan > Send to > "
    "Collect Files Plus.\nWindows 11: klik \"Show more options\" dulu untuk melihat Send to.\n\nKalau folder aplikasi "
    "ini dipindah, pasang ulang dari sini.":
        "Added.\n\nHow to use: in Explorer select one or more .aep files (or folders), right-click > Send to > "
        "Collect Files Plus.\nWindows 11: click \"Show more options\" first to see Send to.\n\nIf you move this "
        "app's folder, add it again from here.",
    "Proses masih berjalan. Hentikan dan tutup?": "A task is still running. Stop it and close?",
    "Project terbaca: %d comp. Centang comp utama, lalu klik Analisa.":
        "Project loaded: %d comps. Tick the main comps, then click Analyze.",
    "Membuka %s": "Opening %s",
    "Analisa selesai. Cek tab Plugin/Font/Footage, lalu klik Collect.":
        "Analysis done. Check the Plugins/Fonts/Footage tabs, then click Collect.",
    "Pilihan awal: %s.": "Initial selection: %s.",
    "  (+%d efek lain di file ini)": "  (+%d other effect(s) in this file)",
    "(perkiraan) ": "(guess) ",
    "TIDAK KETEMU: ": "NOT FOUND: ",
    "Adobe Fonts (aktifkan di CC)": "Adobe Fonts (activate in CC)",
    "tidak terinstall di sini": "not installed here",
    " (sequence %d frame)": " (sequence, %d frames)",
    "dimatikan (dilewati)": "switched off (skipped)",
    "Analisa: %d efek (%d plugin pihak ketiga), %d file plugin, %d font, %d footage.":
        "Analysis: %d effects (%d third-party plugin), %d plugin files, %d fonts, %d footage.",
    "%d dari %d file plugin dicentang, total %s": "%d of %d plugin files ticked, total %s",
    "Pilih...": "Browse...",
    "Folder tujuan": "Destination folder",
    "Centang comp utama yang dipakai. Precomp di dalamnya ikut dibaca otomatis.":
        "Tick the main comps you use. Precomps inside them are read automatically.",
    "Comp aktif": "Active comp",
    "Semua": "All",
    "Kosongkan": "Clear",
    'File plugin yang akan dicopy. Klik kotak centang untuk memilih. "(perkiraan)" = tidak dicentang otomatis.':
        'Plugin files that will be copied. Click a checkbox to choose. "(guess)" = not ticked automatically.',
    "Centang semua": "Tick all",
    "Hapus semua centang": "Untick all",
    'Collect banyak project sekaligus. Semua hasil masuk ke "Folder tujuan" di atas, tiap project ke folder '
    '<nama>_Collected sendiri.\nOpsi yang dicentang di tab "1. Comp & opsi" dipakai untuk semua project. File .aep '
    'atau folder juga bisa di-drag ke jendela ini.':
        'Collect many projects at once. Everything goes into the "Destination folder" above, each project into its '
        'own <name>_Collected folder.\nThe options ticked in the "1. Comps & options" tab apply to every project. '
        'You can also drag .aep files or folders onto this window.',
    "Tambah file .aep...": "Add .aep files...",
    "Tambah folder...": "Add folder...",
    "Hapus yang dipilih": "Remove selected",
    "Comp yang dibaca:": "Comps to read:",
    "Otomatis (Render Queue, kalau kosong comp aktif, kalau tidak ada semua comp)":
        "Automatic (Render Queue; if empty, the active comp; if none, all comps)",
    "Semua comp": "All comps",
    "Project After Effects": "After Effects project",
    "Semua file": "All files",
    "%d project": "%d project(s)",
    "Gagal: %s": "Failed: %s",
    "Batch selesai: %s\n\nFolder tujuan: %s": "Batch finished: %s\n\nDestination folder: %s",
    "\nRingkasan: %s": "\nSummary: %s",
    "Batch selesai: %s": "Batch finished: %s",
    "\n\nBuka folder tujuan?": "\n\nOpen the destination folder?",
    "Selesai.\n\nHasil: %s": "Done.\n\nOutput: %s",
    "\n\nPERHATIAN: %s\nPakai project di folder (Backup).": "\n\nWARNING: %s\nUse the project in the (Backup) folder.",
    "\n\n%d error, lihat laporan.": "\n\n%d error(s), see the report.",
    "\n\nBuka folder hasil?": "\n\nOpen the output folder?",
    "Dibatalkan.": "Cancelled.",
    "GAGAL %s: %s": "FAILED %s: %s",
    "File .aep tidak bisa dibaca:\n%s\n\nKalau project dibuat dengan versi After Effects yang sangat baru, coba "
    "pakai script JSX (folder jsx) dari dalam After Effects.":
        "The .aep file could not be read:\n%s\n\nIf the project was made with a very new version of After Effects, "
        "try the JSX script (jsx folder) from inside After Effects.",
    "Terjadi error:\n%s\n\nDetail ada di tab Log.": "An error occurred:\n%s\n\nDetails are in the Log tab.",

    # ---------------------------------------------------------------- plugins
    "data PiPL": "PiPL data",
    "data PiPL (nama efek sama dengan match name)": "PiPL data (effect name equals the match name)",
    "data PiPL (nama efek mirip, bukan persis)": "PiPL data (similar effect name, not exact)",
    "isi file (data PiPL tidak terbaca, plugin mungkin dikompres)":
        "file contents (PiPL data unreadable, plugin may be packed)",
    "teks di isi file (cocok lemah)": "text inside the file (weak match)",
    "nama file sama dengan nama efek": "file name equals the effect name",
    "nama file mirip nama efek": "file name similar to the effect name",
    "Mendata plugin di %s": "Listing plugins in %s",
    "Lainnya": "Other",
    "Membaca plugin %d/%d: %s": "Reading plugin %d/%d: %s",
    "Pencarian cadangan: %s": "Fallback search: %s",

    # ----------------------------------------------------------------- report
    "Plugin pihak ketiga": "Third-party plugin",
    "Bawaan After Effects": "Built into After Effects",
    "Pseudo effect": "Pseudo effect",
    "PresetEffects.xml": "PresetEffects.xml",
    "bawaan AE": "built into AE",
    "tersimpan di project": "stored in the project",
    "definisi XML diekspor": "XML definition exported",
    "[GAGAL COPY]": "[COPY FAILED]",
    "gagal copy": "copy failed",
    "[DIPILIH]": "[SELECTED]",
    "dicopy": "copied",
    "[OK, CEK MANUAL]": "[OK, CHECK MANUALLY]",
    "dicopy (cek manual)": "copied (check manually)",
    "[TIDAK DICOPY]": "[NOT COPIED]",
    "tidak dicopy (centang dihapus)": "not copied (unticked)",
    "[PERKIRAAN, TIDAK DICOPY]": "[GUESS, NOT COPIED]",
    "perkiraan, tidak dicopy": "guess, not copied",
    "[TIDAK KETEMU]": "[NOT FOUND]",
    "file plugin tidak ketemu": "plugin file not found",
    "Collect Files Plus - laporan": "Collect Files Plus - report",
    "=== EFEK & PLUGIN ===": "=== EFFECTS & PLUGINS ===",
    "Yang dicopy hanya FILE plugin yang berisi efek di atas, bukan seluruh folder plugin.":
        "Only the plugin FILES containing the effects above are copied, not whole plugin folders.",
    "Daftar lengkap per comp & layer ada di file *_daftar_efek.csv.":
        "The full list per comp & layer is in the *_effect_list.csv file.",
    "--- PLUGIN PIHAK KETIGA ---": "--- THIRD-PARTY PLUGINS ---",
    "--- FILE PLUGIN YANG DICOPY ---": "--- PLUGIN FILES COPIED ---",
    "--- EFEK BAWAAN AFTER EFFECTS (tidak perlu dicopy) ---": "--- BUILT-IN AFTER EFFECTS EFFECTS (no copy needed) ---",
    "=== CARA PAKAI DI KOMPUTER LAIN ===": "=== HOW TO USE ON ANOTHER COMPUTER ===",
    "1. Font: install semua file di (Fonts) sebelum membuka project.":
        "1. Fonts: install every file in (Fonts) before opening the project.",
    "   Windows: pilih semua > klik kanan > Install for all users.  Mac: buka dengan Font Book.":
        "   Windows: select all > right-click > Install for all users.  Mac: open with Font Book.",
    "   Font [ADOBE FONTS] cukup diaktifkan dari aplikasi Creative Cloud.":
        "   [ADOBE FONTS] fonts only need activating in the Creative Cloud app.",
    "2. Plugin: tutup After Effects dulu, lalu copy isi:": "2. Plugins: close After Effects first, then copy the contents of:",
    "   (Plugins)/AE Plug-ins  ->  Windows: C:\\Program Files\\Adobe\\Adobe After Effects <versi>\\Support Files\\Plug-ins":
        "   (Plugins)/AE Plug-ins  ->  Windows: C:\\Program Files\\Adobe\\Adobe After Effects <version>\\Support Files\\Plug-ins",
    "                              Mac: /Applications/Adobe After Effects <versi>/Plug-ins":
        "                              Mac: /Applications/Adobe After Effects <version>/Plug-ins",
    '   (Plugins)/Lainnya      ->  lokasi aslinya tercatat di laporan (baris "file plugin").':
        '   (Plugins)/Other        ->  the original location is in the report ("plugin file" lines).',
    "   Lewati plugin yang sudah terinstall supaya tidak dobel.": "   Skip plugins that are already installed to avoid duplicates.",
    "   .aex hanya jalan di Windows, .plugin hanya jalan di Mac.": "   .aex only works on Windows, .plugin only works on Mac.",
    "   Plugin berbayar (Boris FX, Red Giant/Maxon, Video Copilot, dll.) tetap butuh installer +":
        "   Paid plugins (Boris FX, Red Giant/Maxon, Video Copilot, etc.) still need the official installer +",
    "   lisensi resmi di komputer tujuan; file .aex-nya saja biasanya tidak cukup.":
        "   license on the target computer; the .aex file alone is usually not enough.",
    "3. (PresetEffects): ikuti petunjuk di dalam file XML-nya.": "3. (PresetEffects): follow the instructions inside the XML file.",
    "4. (Presets): copy file .ffx ke Documents\\Adobe\\After Effects <versi>\\User Presets.":
        "4. (Presets): copy the .ffx files to Documents\\Adobe\\After Effects <version>\\User Presets.",
    "5. Buka file .aep di folder ini. Path footage sudah diarahkan ke folder (Footage);":
        "5. Open the .aep file in this folder. Footage paths already point to the (Footage) folder;",
    "   kalau folder hasil dipindah, AE tetap bisa menemukannya lewat path relatif.":
        "   if you move this folder, AE still finds the footage through relative paths.",
    "ya": "yes",
    "tidak": "no",
    "semua comp di project (%d comp)": "all comps in the project (%d in total)",
    "Project asal : %s": "Project      : %s",
    "Comp dibaca  : %s": "Comps read   : %s",
    "Tanggal      : %s": "Date         : %s",
    "Versi        : Collect Files Plus %s (py_aep %s)": "Version      : Collect Files Plus %s (py_aep %s)",
    "Terbaca          : %d pemakaian efek, %d jenis efek%s.": "Read             : %d effect uses, %d effect types%s.",
    "Efek plugin pihak ketiga: %d  |  Bawaan AE: %d  |  Pseudo effect: %d  |  PresetEffects.xml: %d":
        "Third-party plugin effects: %d  |  Built-in AE: %d  |  Pseudo effects: %d  |  PresetEffects.xml: %d",
    "Tidak ada.": "None.",
    "--- EFEK DARI PresetEffects.xml ---": "--- EFFECTS FROM PresetEffects.xml ---",
    "Definisinya diekspor ke (PresetEffects)/PresetEffects_dari_project.xml.":
        "Their definitions were exported to (PresetEffects)/PresetEffects_from_project.xml.",
    "--- PSEUDO EFFECT (sudah tersimpan di dalam project, tidak perlu dicopy) ---":
        "--- PSEUDO EFFECTS (already stored inside the project, no copy needed) ---",
    "--- EFEK YANG DIMATIKAN (ikon fx mati, tidak dikumpulkan) ---":
        "--- SWITCHED-OFF EFFECTS (fx off, not collected) ---",
    "Kalau plugin efek ini tidak ada di komputer tujuan, AE tetap memberi peringatan":
        "If these plugins are missing on the target computer, AE still shows a",
    '"missing" saat project dibuka, tapi hasil render tidak berubah.':
        '"missing" warning when the project opens, but the render does not change.',
    "--- ANIMATION PRESET (.ffx) YANG NAMANYA COCOK ---": "--- ANIMATION PRESETS (.ffx) WITH MATCHING NAMES ---",
    "Total: %d efek plugin pihak ketiga dipakai -> %d file plugin dicopy%s, %d tidak ketemu.":
        "Total: %d third-party plugin effects used -> %d plugin files copied%s, %d not found.",
    "Layer": "Layer",
    "Nama efek di layer": "Effect name on layer",
    "Nama efek asli": "Original effect name",
    "Efek aktif": "Effect on",
    "  (+%d precomp di dalamnya)": "  (+%d precomps inside)",
    "Folder hasil : %s": "Output folder: %s",
    "!!! Pakai project di folder (Backup) lalu relink footage ke folder (Footage).":
        "!!! Use the project in the (Backup) folder and relink the footage to the (Footage) folder.",
    "Tidak ada footage file.": "No file footage.",
    "Total: %d file/sequence (%s), %d hilang, %d gagal.": "Total: %d files/sequences (%s), %d missing, %d failed.",
    "Tidak ada font yang dipakai.": "No fonts are used.",
    "Total: %d font dipakai, %d ada file-nya.": "Total: %d font(s) used, %d with font files.",
    "     nama di layer : %s": "     name on layer : %s",
    "     dipakai %dx    : %s": "     used %dx       : %s",
    "     catatan       : plugin ini tidak ada di komputer ini, atau file-nya di luar folder plugin yang dimuat AE":
        "     note          : this plugin is not on this computer, or its file is outside the plug-in folders AE loads",
    "     efek dipakai  : %s": "     effects used  : %s",
    "- %s  %dx  | nama di layer: %s": "- %s  %dx  | name on layer: %s",
    "Tidak ada preset yang namanya cocok dengan efek yang di-rename.":
        "No presets have names matching the renamed effects.",
    "!!! PERHATIAN: %s": "!!! WARNING: %s",
    "Reduce Project: %d item yang tidak dipakai dibuang dari project hasil.":
        "Reduce Project: %d unused items removed from the collected project.",
    "  (sequence, %d frame)": "  (sequence, %d frames)",
    "  (+%d file pendukung model 3D)": "  (+%d 3D model support files)",
    "     kategori      : %s": "     category      : %s",
    "     file plugin   : %s": "     plugin file   : %s",
    "     catatan       : file ini ada di folder plugin After Effects sendiri":
        "     note          : this file is in After Effects' own plug-ins folder",
    "     catatan       : file ini juga berisi %d efek lain yang tidak dipakai (satu file, tidak bisa dipisah)":
        "     note          : this file also contains %d other unused effect(s) (one file, cannot be split)",
    "     file pendukung: %d file/folder ikut dicopy": "     support files : %d file(s)/folder(s) copied too",
    "[DIMATIKAN] %s  (%s)": "[SWITCHED OFF] %s  (%s)",
    "     di            : %s": "     in            : %s",
    '- %s  (cocok dengan efek "%s")': '- %s  (matches effect "%s")',
    "dimatikan, tidak dikumpulkan": "switched off, not collected",
    "Project hasil collect: %s (sudah di-relink ke folder (Footage)).":
        "Collected project: %s (relinked to the (Footage) folder).",
    "Cadangan project asli (belum diubah): (Backup)/%s": "Backup of the original project (unchanged): (Backup)/%s",
    "[HILANG]  %s  ->  %s": "[MISSING] %s  ->  %s",
    "[GAGAL]  ": "[FAILED] ",
    "  (%d pemakaian efek yang dimatikan dilewati)": "  (%d switched-off effect uses skipped)",
    "     cara ketemu   : %s -> pastikan file ini memang plugin-nya":
        "     found via     : %s -> make sure this file really is the plugin",
    "     dicopy ke     : (Plugins)/%s": "     copied to     : (Plugins)/%s",
    ", %d tidak dicentang": ", %d unticked",
    "[GAGAL]   %s  ->  %s  (%s)": "[FAILED]  %s  ->  %s  (%s)",
    "[ADOBE FONTS] %s  -> aktifkan lewat Creative Cloud di komputer tujuan":
        "[ADOBE FONTS] %s  -> activate it through Creative Cloud on the target computer",
    "[TIDAK KETEMU] %s  -> tidak terinstall di komputer ini (atau dari Adobe Fonts)":
        "[NOT FOUND] %s  -> not installed on this computer (or it is from Adobe Fonts)",
    "     catatan       : %s": "     note          : %s",
    "  (definisi ikut diekspor)": "  (definition exported too)",
    "tidak dicopy karena centangnya dihapus": "not copied because it was unticked",
    "tidak dicopy otomatis karena hanya perkiraan; centang di daftar kalau memang benar":
        "not copied automatically because it is only a guess; tick it in the list if it is right",

    # ----------------------------------------------------------------- sendto
    "Folder SendTo tidak ditemukan (APPDATA kosong).": "SendTo folder not found (APPDATA is empty).",
    "Gagal membuat shortcut Send to. %s": "Could not create the Send to shortcut. %s",
}
