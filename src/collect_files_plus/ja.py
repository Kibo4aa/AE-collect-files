"""日本語訳。キー = コード内のインドネシア語の文 (i18n.py 参照)。

用語は日本語版 After Effects に合わせています: コンポ (コンポジション)、フッテージ、
レイヤー、エフェクト、レンダーキュー、マッチネーム、プロジェクトを整理 (Reduce Project)。
ファイル名・フォルダー名 (effect_list.csv、(Plugins)/Other など) は英語のままです。
"""

JA = {
    # ------------------------------------------------------------------ batch
    "otomatis (Render Queue, kalau kosong comp aktif, kalau tidak ada semua comp)":
        "自動 (レンダーキュー、空ならアクティブなコンポ、それもなければすべてのコンポ)",
    "comp di Render Queue": "レンダーキューのコンポ",
    "comp aktif saat project disimpan": "プロジェクト保存時のアクティブなコンポ",
    "semua comp": "すべてのコンポ",
    "comp dengan nama tertentu": "指定した名前のコンポ",
    "menunggu": "待機中",
    "sedang diproses...": "処理中...",
    "OK, ada catatan": "OK (注意あり)",
    "GAGAL": "失敗",
    "dibatalkan": "キャンセル",
    "%d footage hilang": "フッテージ %d 件が見つかりません",
    "%d font tidak ketemu": "フォント %d 件が見つかりません",
    "%d Adobe Fonts (aktifkan di CC)": "Adobe Fonts %d 件 (CC でアクティベート)",
    "%d efek plugin tidak ketemu": "プラグインエフェクト %d 件が見つかりません",
    "%d plugin perkiraan tidak dicopy": "推定プラグイン %d 件は未コピー",
    "%d plugin perkiraan perlu dicek": "要確認の推定プラグイン %d 件",
    "%d error saat copy": "コピーエラー %d 件",
    "[CATATAN]": "[注意]",
    "[GAGAL]": "[失敗]",
    "[DIBATALKAN]": "[キャンセル]",
    "Detail tiap project ada di file _report.txt di folder hasilnya masing-masing.":
        "各プロジェクトの詳細は、それぞれの出力フォルダーにある _report.txt を見てください。",
    "semua comp (%d)": "すべてのコンポ (%d)",
    "comp aktif": "アクティブなコンポ",
    "%s (dari %d project)": "%s (全 %d プロジェクト)",
    "Collect Files Plus %s - ringkasan batch": "Collect Files Plus %s - バッチの概要",
    "Tanggal : %s": "日付    : %s",
    "Folder  : %s": "出力先  : %s",
    "Comp    : %s": "コンポ  : %s",
    "Hasil   : %s": "結果    : %s",
    "Render Queue kosong.": "レンダーキューが空です。",
    "Tidak ada comp aktif yang tersimpan di project ini.": "このプロジェクトにはアクティブなコンポが保存されていません。",
    "GAGAL: %s": "失敗: %s",
    "             asal    : %s": "             元の場所: %s",
    "Comp tidak ditemukan: %s": "コンポが見つかりません: %s",
    "%d ada catatan": "注意あり %d",
    "%d gagal": "失敗 %d",
    "%d tidak diproses": "未処理 %d",
    "Membaca project...": "プロジェクトを読み込み中...",
    "project hasil gagal dicek (%s); file sudah dicopy, pakai .aep di (Backup)":
        "収集したプロジェクトの検証に失敗しました (%s)。ファイルはコピー済みです。(Backup) の .aep を使ってください",
    "             comp    : %s": "             コンポ  : %s",
    "             hasil   : %s": "             出力先  : %s",
    "             catatan : %s": "             注意    : %s",
    "tidak diketahui": "不明",
    "=== PERLU DICEK ===": "=== 要確認 ===",
    "=== SEMUA PROJECT ===": "=== すべてのプロジェクト ===",
    "Semua project berhasil di-collect tanpa catatan.": "すべてのプロジェクトを問題なく収集しました。",
    "comp": "コンポ",
    "Render Queue": "レンダーキュー",

    # -------------------------------------------------------------------- cli
    "CATATAN": "注意",
    "DIBATALKAN": "キャンセル",
    "NAMA": "名前",
    "comp utama (boleh diulang). Precomp di dalamnya ikut dibaca.":
        "メインのコンポ (複数指定可)。中のプリコンポも読み込みます。",
    "comp yang ada di Render Queue": "レンダーキューにあるコンポ",
    "semua comp di project": "プロジェクト内のすべてのコンポ",
    "jangan collect footage": "フッテージを収集しない",
    "jangan collect font": "フォントを収集しない",
    "jangan collect plugin": "プラグインを収集しない",
    "ikutkan efek yang ikon fx-nya mati": "fx スイッチがオフのエフェクトも含める",
    "ikut copy file pendukung plugin (DLL/data di folder yang sama, tanpa plugin lain)":
        "プラグインの付属ファイルもコピー (同じフォルダーの DLL/データ。ほかのプラグインは除く)",
    "buang comp & footage yang tidak dipakai dari project hasil (Reduce Project)":
        "収集したプロジェクトから未使用のコンポとフッテージを削除 (プロジェクトを整理)",
    "ikut copy animation preset (.ffx) yang namanya sama dengan efek yang di-rename":
        "名前を変更したエフェクトと同じ名前のアニメーションプリセット (.ffx) もコピー",
    "ikut copy plugin yang hanya ditemukan lewat perkiraan": "推定でしか見つからなかったプラグインもコピー",
    "Kumpulkan footage, font, dan plugin dari project After Effects tanpa membuka AE.":
        "AE を開かずに、After Effects プロジェクトのフッテージ・フォント・プラグインを収集します。",
    "bahasa output: id (Indonesia), en (English), atau ja (Jepang)":
        "出力の言語: id (インドネシア語)、en (英語)、ja (日本語)",
    "daftar comp di project": "プロジェクト内のコンポ一覧",
    "analisa saja, tidak menyalin apa pun": "分析のみ (何もコピーしない)",
    "collect ke folder tujuan (bisa banyak project sekaligus)": "保存先フォルダーに収集 (複数プロジェクトも可)",
    "folder tujuan": "保存先フォルダー",
    "buka jendela aplikasi": "アプリのウィンドウを開く",
    "Selesai: %s": "完了: %s",
    "Tidak ada file .aep yang ditemukan.": ".aep ファイルが見つかりません。",
    "Collect %d project ke %s": "%d 個のプロジェクトを %s に収集します",
    "file .aep, boleh lebih dari satu; folder = semua .aep di dalamnya":
        ".aep ファイル (複数可)。フォルダーを指定すると中のすべての .aep",
    "file .aep": ".aep ファイル",
    "File tidak ditemukan: %s": "ファイルが見つかりません: %s",
    "Laporan: %s": "レポート: %s",
    "PERHATIAN: %s": "警告: %s",
    "Tidak ditemukan: %s": "見つかりません: %s",
    "Ringkasan: %s": "概要: %s",
    "aktif": "アクティブ",
    "precomp di %d comp": "%d 個のコンポ内のプリコンポ",

    # -------------------------------------------------------------- collector
    "Membaca efek...": "エフェクトを読み込み中...",
    "Menulis laporan...": "レポートを書き込み中...",
    "Membaca daftar font...": "フォント一覧を読み込み中...",
    "Membaca footage...": "フッテージを読み込み中...",
    "Mencari animation preset (.ffx)...": "アニメーションプリセット (.ffx) を検索中...",
    "Menyimpan project hasil collect...": "収集したプロジェクトを保存中...",
    "%d footage tidak menunjuk ke file hasil copy (contoh: %s)":
        "フッテージ %d 件がコピーしたファイルを参照していません (例: %s)",
    "Pencarian plugin dimatikan.": "プラグインの検索はオフです。",
    "file tidak ada": "ファイルがありません",
    "Project hasil tidak bisa dibaca ulang: %s": "収集したプロジェクトを読み直せません: %s",
    "PresetEffects_dari_project.xml": "PresetEffects_from_project.xml",
    "<!-- Collect Files Plus: definisi efek dari PresetEffects.xml yang dipakai project ini.":
        "<!-- Collect Files Plus: このプロジェクトで使われている PresetEffects.xml のエフェクト定義です。",
    '     Efek dengan match name berawalan "Pseudo/" sudah tersimpan di dalam project,':
        '     マッチネームが "Pseudo/" で始まるエフェクトはプロジェクト内に保存されているので、',
    "     jadi biasanya tidak perlu dipasang. Efek lainnya: salin blok <Effect> di bawah":
        "     通常はインストール不要です。それ以外のエフェクトは、下の <Effect> ブロックを",
    "     ke PresetEffects.xml di komputer tujuan (sebelum tag </Effects> terakhir),":
        "     移行先のパソコンの PresetEffects.xml (最後の </Effects> タグの前) にコピーして、",
    "     lalu restart After Effects. -->": "     After Effects を再起動してください。 -->",
    "Gagal menyimpan project: %s": "プロジェクトを保存できませんでした: %s",
    "daftar_efek": "effect_list",
    "Reduce Project gagal: %s": "プロジェクトを整理できませんでした: %s",
    "     Asal: %s": "     元: %s",
    "Reduce Project...": "プロジェクトを整理中...",
    "Footage %d/%d: %s": "フッテージ %d/%d: %s",
    "Footage %d/%d: %s (frame %d/%d)": "フッテージ %d/%d: %s (フレーム %d/%d)",
    "Font: %s": "フォント: %s",
    "Plugin: %s": "プラグイン: %s",

    # ------------------------------------------------------------------ fonts
    "Membaca font %d/%d: %s": "フォントを読み込み中 %d/%d: %s",

    # -------------------------------------------------------------------- gui
    "Pilih file .aep untuk mulai.": ".aep ファイルを選んで始めましょう。",
    "Keterangan": "情報",
    "Yang dikumpulkan": "収集する項目",
    "File plugin": "プラグインファイル",
    "Efek yang dipakai": "使われているエフェクト",
    "Ukuran": "サイズ",
    "Cara ketemu": "検出方法",
    "File": "ファイル",
    "Status": "状態",
    "Item": "アイテム",
    "Efek": "エフェクト",
    "Nama di layer": "レイヤー上の名前",
    "Match name": "マッチネーム",
    "Jenis": "種類",
    "Dipakai": "使用数",
    "Project": "プロジェクト",
    "Lokasi": "場所",
    "Comp": "コンポ",
    "Hasil": "結果",
    "Analisa semua": "すべて分析",
    "Collect semua": "すべて収集",
    "Tambahkan project ke daftar, lalu klik Analisa semua atau Collect semua.":
        "プロジェクトをリストに追加して、「すべて分析」または「すべて収集」をクリックします。",
    "Lihat detail analisa": "分析の詳細を表示",
    "Analisa batch selesai: %s": "バッチ分析完了: %s",
    "Analisa selesai: %s. Klik kanan sebuah project untuk melihat detailnya.":
        "分析完了: %s。プロジェクトを右クリックすると詳細を確認できます。",
    "%d footage, %d font, %d plugin (%s)": "フッテージ %d、フォント %d、プラグイン %d (%s)",
    "Analisa": "分析",
    "Batal": "キャンセル",
    "Buka folder hasil": "出力フォルダーを開く",
    "Pilih project After Effects": "After Effects プロジェクトを選択",
    "Pilih folder tujuan": "保存先フォルダーを選択",
    "File .aep tidak ditemukan.": ".aep ファイルが見つかりません。",
    "Buka file .aep dulu.": "先に .aep ファイルを開いてください。",
    'Centang minimal satu comp di tab "1. Comp & opsi".': "「1. コンポとオプション」タブでコンポを 1 つ以上チェックしてください。",
    "Pilih folder tujuan dulu.": "先に保存先フォルダーを選んでください。",
    "Tunggu proses yang sedang berjalan selesai dulu.": "実行中の処理が終わるまでお待ちください。",
    "Bahasa diganti ke %s.": "言語を %s に変更しました。",
    "Yang di-drop bukan file .aep atau folder.": "ドロップされたのは .aep ファイルでもフォルダーでもありません。",
    "Pilih project After Effects (boleh banyak)": "After Effects プロジェクトを選択 (複数可)",
    "Pilih folder berisi project .aep": ".aep プロジェクトがあるフォルダーを選択",
    'Daftar batch masih kosong. Klik "Tambah file .aep..." atau drag file .aep ke jendela ini.':
        "バッチリストが空です。「.aep ファイルを追加...」をクリックするか、.aep ファイルをこのウィンドウにドラッグしてください。",
    "Membaca %s ...": "%s を読み込み中...",
    "akan dicopy": "コピー予定",
    "HILANG": "ファイルなし",
    "Render Queue di project ini kosong.": "このプロジェクトのレンダーキューは空です。",
    "%d project ditambahkan ke daftar batch (total %d).": "%d 個のプロジェクトをバッチリストに追加しました (合計 %d)。",
    "Collect Files Plus sudah dihapus dari menu Send to.": "「送る」メニューから Collect Files Plus を削除しました。",
    "Terpasang.\n\nCara pakai: di Explorer pilih satu atau banyak file .aep (atau folder), klik kanan > Send to > "
    "Collect Files Plus.\nWindows 11: klik \"Show more options\" dulu untuk melihat Send to.\n\nKalau folder aplikasi "
    "ini dipindah, pasang ulang dari sini.":
        "追加しました。\n\n使い方: エクスプローラーで .aep ファイル (またはフォルダー) を選び、右クリック > 送る > "
        "Collect Files Plus。\nWindows 11 では先に「その他のオプションを確認」をクリックすると「送る」が表示されます。"
        "\n\nこのアプリのフォルダーを移動したときは、ここからもう一度追加してください。",
    "Proses masih berjalan. Hentikan dan tutup?": "処理を実行中です。中止して閉じますか?",
    "Project terbaca: %d comp. Centang comp utama, lalu klik Analisa.":
        "プロジェクトを読み込みました: コンポ %d 個。メインのコンポにチェックを入れて「分析」をクリックしてください。",
    "Membuka %s": "%s を開いています",
    "Analisa selesai. Cek tab Plugin/Font/Footage, lalu klik Collect.":
        "分析が完了しました。プラグイン/フォント/フッテージのタブを確認して「収集」をクリックしてください。",
    "Pilihan awal: %s.": "最初の選択: %s。",
    "  (+%d efek lain di file ini)": "  (このファイルにはほかに %d 個のエフェクト)",
    "TIDAK KETEMU: ": "見つからない: ",
    "Adobe Fonts (aktifkan di CC)": "Adobe Fonts (CC でアクティベート)",
    "tidak terinstall di sini": "このパソコンにありません",
    " (sequence %d frame)": " (シーケンス %d フレーム)",
    "dimatikan (dilewati)": "オフ (スキップ)",
    "Analisa: %d efek (%d plugin pihak ketiga), %d file plugin, %d font, %d footage.":
        "分析: エフェクト %d (サードパーティ製プラグイン %d)、プラグインファイル %d、フォント %d、フッテージ %d。",
    "Pilih...": "参照...",
    "Folder tujuan": "保存先フォルダー",
    "Comp aktif": "アクティブなコンポ",
    "Semua": "すべて",
    "Kosongkan": "クリア",
    "Centang semua": "すべてチェック",
    "Hapus semua centang": "すべてのチェックを外す",
    "Tambah file .aep...": ".aep ファイルを追加...",
    "Tambah folder...": "フォルダーを追加...",
    "Hapus yang dipilih": "選択した項目を削除",
    "Comp yang dibaca:": "読み込むコンポ:",
    "Semua comp": "すべてのコンポ",
    "Project After Effects": "After Effects プロジェクト",
    "Semua file": "すべてのファイル",
    "%d project": "%d プロジェクト",
    "Gagal: %s": "失敗しました: %s",
    "Batch selesai: %s\n\nFolder tujuan: %s": "バッチ完了: %s\n\n保存先フォルダー: %s",
    "\nRingkasan: %s": "\n概要: %s",
    "Batch selesai: %s": "バッチ完了: %s",
    "\n\nBuka folder tujuan?": "\n\n保存先フォルダーを開きますか?",
    "Selesai.\n\nHasil: %s": "完了しました。\n\n出力: %s",
    "\n\nPERHATIAN: %s\nPakai project di folder (Backup).": "\n\n警告: %s\n(Backup) フォルダーのプロジェクトを使ってください。",
    "\n\n%d error, lihat laporan.": "\n\nエラー %d 件。レポートを確認してください。",
    "\n\nBuka folder hasil?": "\n\n出力フォルダーを開きますか?",
    "Dibatalkan.": "キャンセルしました。",
    "GAGAL %s: %s": "失敗 %s: %s",
    "File .aep tidak bisa dibaca:\n%s\n\nKalau project dibuat dengan versi After Effects yang sangat baru, coba "
    "pakai script JSX (folder jsx) dari dalam After Effects.":
        ".aep ファイルを読み込めません:\n%s\n\nとても新しいバージョンの After Effects で作ったプロジェクトなら、"
        "After Effects の中から JSX スクリプト (jsx フォルダー) を使ってみてください。",
    "Terjadi error:\n%s\n\nDetail ada di tab Log.": "エラーが発生しました:\n%s\n\n詳しくは「ログ」タブを見てください。",
    "Log": "ログ",
    "Collect": "収集",
    "Error.": "エラー。",
    "Buka project...": "プロジェクトを開く...",
    "Tambah project ke Batch...": "バッチにプロジェクトを追加...",
    "Tambah folder ke Batch...": "バッチにフォルダーを追加...",
    "Buka laporan terakhir": "最後のレポートを開く",
    "Keluar": "終了",
    "Pengaturan": "設定",
    "Tema": "テーマ",
    "Ikuti Windows": "Windows の設定に合わせる",
    "Ikuti sistem": "システムの設定に合わせる",
    "Terang": "ライト",
    "Gelap": "ダーク",
    "Cek update saat aplikasi dibuka": "起動時にアップデートを確認",
    'Menu klik kanan "Send to" di Explorer': "エクスプローラーの右クリック「送る」メニュー",
    "Bantuan": "ヘルプ",
    "Cara pakai": "使い方",
    "Cek update...": "アップデートを確認...",
    "Halaman GitHub": "GitHub ページ",
    "Tentang Collect Files Plus": "Collect Files Plus について",
    "Belum ada laporan. Jalankan Collect dulu.": "レポートはまだありません。先に「収集」を実行してください。",
    "Collect Files Plus %s\n\nKumpulkan footage, font, dan plugin yang dipakai project After Effects tanpa membuka "
    "After Effects.\n\nLisensi MIT\n%s":
        "Collect Files Plus %s\n\nAfter Effects を開かずに、プロジェクトで使われているフッテージ・フォント・"
        "プラグインを収集します。\n\nMIT ライセンス\n%s",
    "Buka laporan": "レポートを開く",
    "Hapus dari daftar": "リストから削除",

    # ---------------------------------------------------------------- dialogs
    "Ya": "はい",
    "Tidak": "いいえ",

    # ---------------------------------------------------------------- plugins
    "data PiPL": "PiPL データ",
    "data PiPL (nama efek sama dengan match name)": "PiPL データ (エフェクト名がマッチネームと同じ)",
    "data PiPL (nama efek mirip, bukan persis)": "PiPL データ (エフェクト名が似ている、完全一致ではない)",
    "isi file (data PiPL tidak terbaca, plugin mungkin dikompres)":
        "ファイルの中身 (PiPL データを読めない。プラグインが圧縮されている可能性あり)",
    "teks di isi file (cocok lemah)": "ファイル内のテキスト (弱い一致)",
    "nama file sama dengan nama efek": "ファイル名がエフェクト名と同じ",
    "nama file mirip nama efek": "ファイル名がエフェクト名に似ている",
    "Mendata plugin di %s": "%s のプラグインを調べています",
    "Lainnya": "Other",
    "Membaca plugin %d/%d: %s": "プラグインを読み込み中 %d/%d: %s",
    "Pencarian cadangan: %s": "予備の検索: %s",

    # ----------------------------------------------------------------- report
    "Plugin pihak ketiga": "サードパーティ製プラグイン",
    "Bawaan After Effects": "After Effects 標準",
    "Pseudo effect": "疑似エフェクト",
    "PresetEffects.xml": "PresetEffects.xml",
    "bawaan AE": "AE 標準",
    "tersimpan di project": "プロジェクト内に保存済み",
    "definisi XML diekspor": "XML 定義を書き出し済み",
    "[GAGAL COPY]": "[コピー失敗]",
    "gagal copy": "コピー失敗",
    "[DIPILIH]": "[選択済み]",
    "dicopy": "コピー済み",
    "[OK, CEK MANUAL]": "[OK・要確認]",
    "dicopy (cek manual)": "コピー済み (要確認)",
    "[TIDAK DICOPY]": "[コピーしない]",
    "tidak dicopy (centang dihapus)": "コピーしない (チェックを外した)",
    "[PERKIRAAN, TIDAK DICOPY]": "[推定・コピーしない]",
    "perkiraan, tidak dicopy": "推定・コピーしない",
    "[TIDAK KETEMU]": "[見つからない]",
    "file plugin tidak ketemu": "プラグインファイルが見つからない",
    "Collect Files Plus - laporan": "Collect Files Plus - レポート",
    "=== EFEK & PLUGIN ===": "=== エフェクトとプラグイン ===",
    "Yang dicopy hanya FILE plugin yang berisi efek di atas, bukan seluruh folder plugin.":
        "コピーするのは上のエフェクトを含むプラグインの「ファイル」だけで、プラグインのフォルダー全体ではありません。",
    "Daftar lengkap per comp & layer ada di file *_daftar_efek.csv.":
        "コンポ・レイヤーごとの全一覧は *_effect_list.csv にあります。",
    "--- PLUGIN PIHAK KETIGA ---": "--- サードパーティ製プラグイン ---",
    "--- FILE PLUGIN YANG DICOPY ---": "--- コピーしたプラグインファイル ---",
    "--- EFEK BAWAAN AFTER EFFECTS (tidak perlu dicopy) ---": "--- After Effects 標準のエフェクト (コピー不要) ---",
    "=== CARA PAKAI DI KOMPUTER LAIN ===": "=== 別のパソコンで使う方法 ===",
    "1. Font: install semua file di (Fonts) sebelum membuka project.":
        "1. フォント: プロジェクトを開く前に (Fonts) のファイルをすべてインストールします。",
    "   Windows: pilih semua > klik kanan > Install for all users.  Mac: buka dengan Font Book.":
        "   Windows: すべて選択 > 右クリック > すべてのユーザーに対してインストール。  Mac: Font Book で開きます。",
    "   Font [ADOBE FONTS] cukup diaktifkan dari aplikasi Creative Cloud.":
        "   [ADOBE FONTS] のフォントは Creative Cloud アプリでアクティベートするだけです。",
    "2. Plugin: tutup After Effects dulu, lalu copy isi:": "2. プラグイン: After Effects を閉じてから、次の中身をコピーします:",
    "   (Plugins)/AE Plug-ins  ->  Windows: C:\\Program Files\\Adobe\\Adobe After Effects <versi>\\Support Files\\Plug-ins":
        "   (Plugins)/AE Plug-ins  ->  Windows: C:\\Program Files\\Adobe\\Adobe After Effects <バージョン>\\Support Files\\Plug-ins",
    "                              Mac: /Applications/Adobe After Effects <versi>/Plug-ins":
        "                              Mac: /Applications/Adobe After Effects <バージョン>/Plug-ins",
    '   (Plugins)/Lainnya      ->  lokasi aslinya tercatat di laporan (baris "file plugin").':
        "   (Plugins)/Other        ->  元の場所はレポートの「ファイル」行に書いてあります。",
    "   Lewati plugin yang sudah terinstall supaya tidak dobel.":
        "   重複しないように、インストール済みのプラグインはスキップしてください。",
    "   .aex hanya jalan di Windows, .plugin hanya jalan di Mac.": "   .aex は Windows 専用、.plugin は Mac 専用です。",
    "   Plugin berbayar (Boris FX, Red Giant/Maxon, Video Copilot, dll.) tetap butuh installer +":
        "   有料プラグイン (Boris FX、Red Giant/Maxon、Video Copilot など) は、移行先のパソコンでも",
    "   lisensi resmi di komputer tujuan; file .aex-nya saja biasanya tidak cukup.":
        "   公式のインストーラーとライセンスが必要です。.aex ファイルだけでは普通は動きません。",
    "3. (PresetEffects): ikuti petunjuk di dalam file XML-nya.": "3. (PresetEffects): XML ファイルの中の説明に従ってください。",
    "4. (Presets): copy file .ffx ke Documents\\Adobe\\After Effects <versi>\\User Presets.":
        "4. (Presets): .ffx ファイルを Documents\\Adobe\\After Effects <バージョン>\\User Presets にコピーします。",
    "5. Buka file .aep di folder ini. Path footage sudah diarahkan ke folder (Footage);":
        "5. このフォルダーの .aep ファイルを開きます。フッテージのパスは (Footage) フォルダーを指しています。",
    "   kalau folder hasil dipindah, AE tetap bisa menemukannya lewat path relatif.":
        "   このフォルダーを移動しても、AE は相対パスでフッテージを見つけられます。",
    "ya": "はい",
    "tidak": "いいえ",
    "semua comp di project (%d comp)": "プロジェクト内のすべてのコンポ (%d 個)",
    "Project asal : %s": "プロジェクト : %s",
    "Comp dibaca  : %s": "対象コンポ   : %s",
    "Tanggal      : %s": "日付         : %s",
    "Versi        : Collect Files Plus %s (py_aep %s)": "バージョン   : Collect Files Plus %s (py_aep %s)",
    "Terbaca          : %d pemakaian efek, %d jenis efek%s.": "読み込み結果     : エフェクトの使用 %d 件、エフェクト %d 種類%s。",
    "Efek plugin pihak ketiga: %d  |  Bawaan AE: %d  |  Pseudo effect: %d  |  PresetEffects.xml: %d":
        "サードパーティ製プラグイン: %d  |  AE 標準: %d  |  疑似エフェクト: %d  |  PresetEffects.xml: %d",
    "Tidak ada.": "なし。",
    "--- EFEK DARI PresetEffects.xml ---": "--- PresetEffects.xml のエフェクト ---",
    "Definisinya diekspor ke (PresetEffects)/PresetEffects_dari_project.xml.":
        "定義は (PresetEffects)/PresetEffects_from_project.xml に書き出しました。",
    "--- PSEUDO EFFECT (sudah tersimpan di dalam project, tidak perlu dicopy) ---":
        "--- 疑似エフェクト (プロジェクト内に保存済み、コピー不要) ---",
    "--- EFEK YANG DIMATIKAN (ikon fx mati, tidak dikumpulkan) ---":
        "--- オフのエフェクト (fx スイッチがオフ、収集しない) ---",
    "Kalau plugin efek ini tidak ada di komputer tujuan, AE tetap memberi peringatan":
        "これらのプラグインが移行先のパソコンにないと、プロジェクトを開いたときに AE は",
    '"missing" saat project dibuka, tapi hasil render tidak berubah.':
        "「見つからない」と警告を出しますが、レンダリング結果は変わりません。",
    "--- ANIMATION PRESET (.ffx) YANG NAMANYA COCOK ---": "--- 名前が一致するアニメーションプリセット (.ffx) ---",
    "Total: %d efek plugin pihak ketiga dipakai -> %d file plugin dicopy%s, %d tidak ketemu.":
        "合計: サードパーティ製プラグインのエフェクト %d 個 -> プラグインファイル %d 個をコピー%s、見つからない %d 個。",
    "Layer": "レイヤー",
    "Nama efek di layer": "レイヤー上のエフェクト名",
    "Nama efek asli": "元のエフェクト名",
    "Efek aktif": "エフェクト有効",
    "  (+%d precomp di dalamnya)": "  (中のプリコンポ +%d)",
    "Folder hasil : %s": "出力先       : %s",
    "!!! Pakai project di folder (Backup) lalu relink footage ke folder (Footage).":
        "!!! (Backup) フォルダーのプロジェクトを使い、フッテージを (Footage) フォルダーに再リンクしてください。",
    "Tidak ada footage file.": "ファイルのフッテージはありません。",
    "Total: %d file/sequence (%s), %d hilang, %d gagal.": "合計: ファイル/シーケンス %d 個 (%s)、見つからない %d、失敗 %d。",
    "Tidak ada font yang dipakai.": "使われているフォントはありません。",
    "Total: %d font dipakai, %d ada file-nya.": "合計: 使用フォント %d 個、ファイルあり %d 個。",
    "     nama di layer : %s": "     レイヤー名    : %s",
    "     dipakai %dx    : %s": "     使用 %d 回     : %s",
    "     catatan       : plugin ini tidak ada di komputer ini, atau file-nya di luar folder plugin yang dimuat AE":
        "     注意          : このプラグインはこのパソコンにないか、AE が読み込むプラグインフォルダーの外にあります",
    "     efek dipakai  : %s": "     使用エフェクト: %s",
    "- %s  %dx  | nama di layer: %s": "- %s  %d 回  | レイヤー上の名前: %s",
    "Tidak ada preset yang namanya cocok dengan efek yang di-rename.":
        "名前を変更したエフェクトと同じ名前のプリセットはありません。",
    "!!! PERHATIAN: %s": "!!! 警告: %s",
    "Reduce Project: %d item yang tidak dipakai dibuang dari project hasil.":
        "プロジェクトを整理: 未使用のアイテム %d 個を収集したプロジェクトから削除しました。",
    "  (sequence, %d frame)": "  (シーケンス、%d フレーム)",
    "  (+%d file pendukung model 3D)": "  (3D モデルの付属ファイル +%d)",
    "     kategori      : %s": "     カテゴリ      : %s",
    "     file plugin   : %s": "     ファイル      : %s",
    "     catatan       : file ini ada di folder plugin After Effects sendiri":
        "     注意          : このファイルは After Effects 本体のプラグインフォルダーにあります",
    "     catatan       : file ini juga berisi %d efek lain yang tidak dipakai (satu file, tidak bisa dipisah)":
        "     注意          : このファイルには未使用のエフェクトがほかに %d 個入っています (1 つのファイルなので分けられません)",
    "     file pendukung: %d file/folder ikut dicopy": "     付属ファイル  : %d 個のファイル/フォルダーも一緒にコピー",
    "[DIMATIKAN] %s  (%s)": "[オフ] %s  (%s)",
    "     di            : %s": "     場所          : %s",
    '- %s  (cocok dengan efek "%s")': "- %s  (エフェクト「%s」と一致)",
    "dimatikan, tidak dikumpulkan": "オフ、収集しない",
    "Project hasil collect: %s (sudah di-relink ke folder (Footage)).":
        "収集したプロジェクト: %s ((Footage) フォルダーに再リンク済み)。",
    "Cadangan project asli (belum diubah): (Backup)/%s": "元のプロジェクトのバックアップ (未変更): (Backup)/%s",
    "[HILANG]  %s  ->  %s": "[ファイルなし] %s  ->  %s",
    "[GAGAL]  ": "[失敗]   ",
    "  (%d pemakaian efek yang dimatikan dilewati)": "  (オフのエフェクトの使用 %d 件はスキップ)",
    "     cara ketemu   : %s -> pastikan file ini memang plugin-nya":
        "     検出方法      : %s -> このファイルが本当にそのプラグインか確認してください",
    "     dicopy ke     : (Plugins)/%s": "     コピー先      : (Plugins)/%s",
    ", %d tidak dicentang": "、チェックなし %d",
    "[GAGAL]   %s  ->  %s  (%s)": "[失敗]    %s  ->  %s  (%s)",
    "[ADOBE FONTS] %s  -> aktifkan lewat Creative Cloud di komputer tujuan":
        "[ADOBE FONTS] %s  -> 移行先のパソコンで Creative Cloud からアクティベートしてください",
    "[TIDAK KETEMU] %s  -> tidak terinstall di komputer ini (atau dari Adobe Fonts)":
        "[見つからない] %s  -> このパソコンにインストールされていません (または Adobe Fonts のフォント)",
    "     catatan       : %s": "     注意          : %s",
    "  (definisi ikut diekspor)": "  (定義も書き出し済み)",
    "tidak dicopy karena centangnya dihapus": "チェックを外したのでコピーしていません",
    "tidak dicopy otomatis karena hanya perkiraan; centang di daftar kalau memang benar":
        "推定なので自動ではコピーしていません。正しければリストでチェックしてください",
    "RINCIAN": "詳細",
    "=== RINGKASAN ===": "=== 概要 ===",
    "[OK] = beres   [!] = perlu dicek   [i] = info": "[OK] = 完了   [!] = 要確認   [i] = 情報",
    "=== FOOTAGE ===": "=== フッテージ ===",
    "=== FONT ===": "=== フォント ===",
    "Tidak ada yang perlu dicek.": "確認が必要な項目はありません。",
    "%d error saat collect, lihat [ERROR] di bagian RINCIAN.": "収集中のエラー %d 件。「詳細」の [ERROR] を見てください。",
    "Project: %s (salinan project asli, tidak ada yang perlu diubah).":
        "プロジェクト: %s (元のプロジェクトのコピー。変更は不要でした)。",
    "Footage: tidak ada file footage.": "フッテージ: ファイルのフッテージはありません。",
    "Footage: %d file/sequence dicopy ke (Footage), total %s.":
        "フッテージ: %d 個のファイル/シーケンスを (Footage) にコピー (合計 %s)。",
    "Footage: %d file/sequence akan dicopy, total %s.": "フッテージ: %d 個のファイル/シーケンスをコピー予定 (合計 %s)。",
    "Footage: %d file hilang (tidak ada di komputer ini).": "フッテージ: %d 個のファイルが見つかりません (このパソコンにありません)。",
    "Cari file aslinya, lalu relink di After Effects. Daftarnya: [HILANG] di bagian FOOTAGE.":
        "元のファイルを探して After Effects で再リンクしてください。一覧: 「フッテージ」の [ファイルなし]。",
    "Footage: %d file gagal dicopy.": "フッテージ: %d 個のファイルをコピーできませんでした。",
    "Lihat [GAGAL] di bagian FOOTAGE.": "「フッテージ」の [失敗] を見てください。",
    "Font: tidak ada font yang dipakai.": "フォント: 使われているフォントはありません。",
    "Font: %d font dicopy ke (Fonts).": "フォント: %d 個を (Fonts) にコピー。",
    "Font: %d font akan dicopy.": "フォント: %d 個をコピー予定。",
    "Font: %d font tidak ketemu di komputer ini.": "フォント: %d 個がこのパソコンで見つかりません。",
    "Install font itu di komputer tujuan. Daftarnya: [TIDAK KETEMU] di bagian FONT.":
        "そのフォントを移行先のパソコンにインストールしてください。一覧: 「フォント」の [見つからない]。",
    "Font: %d Adobe Fonts tidak dicopy.": "フォント: Adobe Fonts の %d 個はコピーしていません。",
    "Aktifkan lewat aplikasi Creative Cloud di komputer tujuan.":
        "移行先のパソコンの Creative Cloud アプリでアクティベートしてください。",
    "Font: %d font gagal dicopy.": "フォント: %d 個をコピーできませんでした。",
    "Plugin: tidak ada efek plugin pihak ketiga yang dipakai.":
        "プラグイン: サードパーティ製プラグインのエフェクトは使われていません。",
    "Plugin: %d file plugin dicopy ke (Plugins), untuk %d efek.":
        "プラグイン: %d 個のプラグインファイルを (Plugins) にコピー (エフェクト %d 個分)。",
    "Plugin: %d file plugin akan dicopy, untuk %d efek.":
        "プラグイン: %d 個のプラグインファイルをコピー予定 (エフェクト %d 個分)。",
    "Plugin: %d efek plugin tidak ketemu di komputer ini.":
        "プラグイン: %d 個のプラグインエフェクトがこのパソコンで見つかりません。",
    "Install plugin itu di komputer tujuan. Daftarnya: [TIDAK KETEMU] di bagian EFEK & PLUGIN.":
        "そのプラグインを移行先のパソコンにインストールしてください。一覧: 「エフェクトとプラグイン」の [見つからない]。",
    "Plugin: %d file plugin perkiraan tidak dicopy.": "プラグイン: 推定の %d 個のプラグインファイルはコピーしていません。",
    "Cek [PERKIRAAN, TIDAK DICOPY] di bagian EFEK & PLUGIN; centang di aplikasi kalau memang benar.":
        "「エフェクトとプラグイン」の [推定・コピーしない] を確認し、正しければアプリでチェックしてください。",
    "Plugin: %d efek perlu dicek manual.": "プラグイン: %d 個のエフェクトは手動で確認してください。",
    "Lihat [OK, CEK MANUAL] di bagian EFEK & PLUGIN.": "「エフェクトとプラグイン」の [OK・要確認] を見てください。",
    "Plugin: %d file plugin tidak dicopy karena centangnya dihapus.":
        "プラグイン: チェックを外した %d 個のプラグインファイルはコピーしていません。",
    "Plugin: %d file plugin gagal dicopy.": "プラグイン: %d 個のプラグインファイルをコピーできませんでした。",
    "Plugin berbayar tetap butuh installer + lisensi resmi di komputer tujuan.":
        "有料プラグインは、移行先のパソコンでも公式のインストーラーとライセンスが必要です。",

    # ----------------------------------------------------------------- sendto
    "Folder SendTo tidak ditemukan (APPDATA kosong).": "SendTo フォルダーが見つかりません (APPDATA が空です)。",
    "Gagal membuat shortcut Send to. %s": "「送る」のショートカットを作れませんでした。%s",

    # ---------------------------------------------------------------- updater
    "cek versi terbaru di GitHub": "GitHub で最新バージョンを確認",
    "Versi ini     : %s": "このバージョン: %s",
    "Belum ada rilis di GitHub.": "GitHub にはまだリリースがありません。",
    "Versi terbaru : %s": "最新バージョン: %s",
    'Di aplikasi (jendela), klik "Update sekarang" untuk memasang otomatis.':
        "アプリのウィンドウで「今すぐアップデート」をクリックすると、自動でインストールされます。",
    "Download      : %s": "ダウンロード  : %s",
    "Kamu sudah memakai versi terbaru (%s).": "最新バージョン (%s) を使っています。",
    "Tidak bisa mengecek update:\n%s": "アップデートを確認できません:\n%s",
    "Menyiapkan update...": "アップデートを準備中...",
    "Update sekarang": "今すぐアップデート",
    "Mengecek update...": "アップデートを確認中...",
    "Versi baru %s tersedia (kamu memakai %s).": "新しいバージョン %s があります (現在は %s)。",
    "Download": "ダウンロード",
    "Download dan pasang versi %s sekarang?\n\nAplikasi akan ditutup lalu dibuka lagi otomatis.":
        "バージョン %s をダウンロードしてインストールしますか?\n\nアプリはいったん閉じて、自動でまた開きます。",
    "Download dan pasang versi %s sekarang?\n\nInstaller akan berjalan dan Windows mungkin meminta izin (UAC). "
    "Aplikasi dibuka lagi setelah selesai.":
        "バージョン %s をダウンロードしてインストールしますか?\n\nインストーラーが起動し、Windows から許可 (UAC) を"
        "求められることがあります。終わるとアプリがまた開きます。",
    "Update berhasil. Sekarang memakai versi %s.": "アップデートが完了しました。現在のバージョンは %s です。",
    "Update gagal, versi lama tetap dipakai.\nCatatan: %s": "アップデートに失敗したので、前のバージョンのままです。\nログ: %s",
    "Lihat perubahan": "変更点を見る",
    "Tutup": "閉じる",
    "Mengunduh update: %s dari %s": "アップデートをダウンロード中: %s / %s",
    "Gagal memulai update: %s": "アップデートを開始できません: %s",
    "Isi update tidak lengkap (CollectFilesPlus.exe tidak ada).": "アップデートの中身が足りません (CollectFilesPlus.exe がありません)。",
    "Rilis ini tidak punya file untuk sistem ini.": "このリリースには、このシステム用のファイルがありません。",
    "File update rusak (checksum tidak cocok). Coba lagi.": "アップデートファイルが壊れています (チェックサム不一致)。もう一度試してください。",
    "Isi file update tidak valid.": "アップデートファイルの中身が正しくありません。",
    # --- 1.3.0: tampilan ringkas
    "Comp & opsi": "コンポとオプション",
    "Plugin": "プラグイン",
    "Font": "フォント",
    "Footage": "フッテージ",
    "Semua efek": "すべてのエフェクト",
    "Batch": "バッチ",
    "Opsi": "オプション",
    "Pilih:": "選択:",
    "Kecocokan": "一致",
    "Pasti": "確実",
    "Perkiraan": "推定",
    "Otomatis": "自動",
    "Reduce Project": "プロジェクトを整理",
    "Lewati efek yang dimatikan": "オフのエフェクトはスキップ",
    "File pendukung plugin": "プラグインの付属ファイル",
    "Preset animasi (.ffx)": "アニメーションプリセット (.ffx)",
    "Belum ada hasil. Klik Analisa.": "まだ結果はありません。「分析」をクリックしてください。",
    "Tidak ada plugin pihak ketiga.": "サードパーティ製プラグインはありません。",
    "Tidak ada font.": "フォントはありません。",
    "Tidak ada footage.": "フッテージはありません。",
    "Tidak ada efek.": "エフェクトはありません。",
    'Tidak dicek: opsi "%s" dimatikan.': "確認していません:「%s」オプションがオフです。",
    "%d/%d dicentang · %s": "%d/%d チェック · %s",
    "Project ini tidak punya comp.": "このプロジェクトにはコンポがありません。",
    'Drag file .aep ke sini\natau klik "Pilih..." di atas': ".aep ファイルをここにドラッグ\nまたは上の「参照...」をクリック",
    'Drag file .aep atau folder ke sini\natau klik "Tambah file .aep..."':
        ".aep ファイルやフォルダーをここにドラッグ\nまたは「.aep ファイルを追加...」をクリック",
    "Copy footage yang dipakai, lalu relink project ke folder (Footage).":
        "使われているフッテージをコピーし、プロジェクトを (Footage) フォルダーに再リンクします。",
    "Copy file font yang dipakai text layer. Adobe Fonts tidak dicopy: aktifkan di Creative Cloud.":
        "テキストレイヤーで使われているフォントファイルをコピーします。Adobe Fonts はコピーされません (Creative Cloud で有効にしてください)。",
    "Copy file plugin pihak ketiga, hanya yang efeknya dipakai project.":
        "サードパーティ製プラグインのファイルを、プロジェクトで使われているエフェクトのものだけコピーします。",
    "Buang comp dan footage yang tidak dipakai comp yang dicentang (seperti File > Reduce Project di After Effects).":
        "チェックしたコンポで使われていないコンポとフッテージを削除します (After Effects の「プロジェクトを整理」と同じ)。",
    "Efek dengan ikon fx mati tidak dihitung, jadi pluginnya tidak ikut dicopy.":
        "fx スイッチがオフのエフェクトは数えないため、そのプラグインはコピーされません。",
    "Ikut copy DLL dan file data di folder yang sama dengan file plugin.":
        "プラグインファイルと同じフォルダーにある DLL やデータファイルもコピーします。",
    "Ikut copy animation preset (.ffx) yang namanya sama dengan efek yang di-rename.":
        "名前を変更したエフェクトと同じ名前のアニメーションプリセット (.ffx) もコピーします。",
    "Comp di Render Queue. Kalau kosong, comp yang aktif saat project disimpan. Kalau tidak ada, semua comp.":
        "レンダーキューのコンポ。空の場合はプロジェクト保存時のアクティブなコンポ、それもない場合はすべてのコンポ。",
}
