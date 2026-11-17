COLLECT FILES PLUS untuk After Effects
======================================
https://github.com/Kibo4aa/AE-collect-files

Mengumpulkan semua yang dibutuhkan project After Effects ke satu folder:
footage, font, dan hanya file plugin yang efeknya benar-benar dipakai.
File .aep dibaca langsung, jadi After Effects tidak perlu dibuka.
File .aep asli kamu tidak pernah diubah.


MULAI CEPAT
-----------
1. Buka Collect Files Plus.
2. Drag file .aep ke jendela aplikasi (atau File > Buka project...).
3. Tab "1. Comp & opsi": centang comp utama yang kamu render.
   Precomp di dalamnya ikut dibaca otomatis.
4. Klik Analisa (F5), lalu cek tab Plugin, Font, dan Footage.
   Hapus centang file plugin yang tidak ingin dicopy.
5. Pilih folder tujuan, lalu klik Collect (Ctrl+Enter).
6. Buka folder hasil dan baca <project>_report.txt dulu.


BANYAK PROJECT SEKALIGUS (BATCH)
--------------------------------
- Drag beberapa file .aep, atau satu folder, ke jendela aplikasi. Semuanya
  masuk ke tab "Batch (banyak project)". Klik "Collect semua project".
- Semua project masuk ke folder tujuan yang sama, masing-masing ke folder
  <nama>_Collected sendiri. Satu project gagal tidak menghentikan yang lain.
- File CollectFilesPlus_batch_<tanggal>.txt di folder tujuan berisi yang
  perlu dicek dulu, lalu daftar semua project.
- Klik kanan project di daftar untuk membuka folder hasil atau laporannya.
- Dari Windows Explorer: nyalakan Pengaturan > Menu klik kanan "Send to"
  di Explorer. Lalu pilih file .aep > klik kanan > Send to >
  Collect Files Plus (Windows 11: klik "Show more options" dulu).


ISI FOLDER HASIL
----------------
<project>_report.txt       BACA INI DULU: ringkasan, langkah, lalu rincian
<project>.aep              project hasil collect, sudah di-relink ke (Footage)
<project>_daftar_efek.csv  semua efek di semua layer (bisa dibuka di Excel)
(Footage)                  footage yang dicopy, dikelompokkan per folder asal
(Fonts)                    file font yang dipakai text layer
(Plugins)                  hanya file plugin yang efeknya dipakai
(PresetEffects)            definisi efek dari PresetEffects.xml
(Presets)                  animation preset (.ffx), kalau opsinya dinyalakan
(Backup)                   salinan .aep asli yang tidak diubah

Di laporan dan ringkasan batch:
  [OK] = beres    [!] = perlu dicek    [i] = info


DI KOMPUTER LAIN
----------------
1. Install font di (Fonts). Adobe Fonts: aktifkan lewat Creative Cloud.
2. Tutup After Effects, lalu copy file plugin dari (Plugins) ke folder yang
   tertulis di laporan. Lewati plugin yang sudah terinstall.
   Plugin berbayar tetap butuh installer dan lisensi resmi.
3. Buka file .aep-nya. Footage langsung ketemu.


MENU DAN SHORTCUT
-----------------
Pengaturan > Bahasa / Language / 言語
    Bahasa Indonesia, English, atau 日本語. Laporan, ringkasan, dan daftar
    efek ditulis dalam bahasa yang dipilih.
Pengaturan > Tema
    Ikuti Windows, Terang, atau Gelap.
Pengaturan > Cek update saat aplikasi dibuka
Bantuan > Cara pakai (F1)   membuka file ini
Bantuan > Cek update...

Ctrl+O  buka project      F5  analisa      Ctrl+Enter  collect
Esc     batal             F1  bantuan
Klik dua kali baris di tab Plugin, Font, atau Footage untuk melihat file-nya.


UPDATE
------
Kalau ada versi baru, muncul bar di bagian atas jendela.
Klik "Update sekarang": aplikasi mengunduh, memasang, lalu terbuka lagi.
- Dipasang lewat installer .msi: installer baru berjalan sendiri.
  Windows mungkin meminta izin (UAC).
- Versi portable .zip: file-nya diganti. Kalau ada yang gagal, versi lama
  dikembalikan.


INSTALLER (.msi) ATAU PORTABLE (.zip)
-------------------------------------
CollectFilesPlus-v<versi>-windows-x64.msi
    Terpasang di C:\Program Files\Collect Files Plus, lengkap dengan
    shortcut di Start menu dan desktop. Uninstall dari Settings > Apps.
CollectFilesPlus-v<versi>-windows-x64.zip
    Extract di mana saja, lalu jalankan CollectFilesPlus.exe.
    Untuk menghapus, hapus foldernya.
Pengaturan disimpan di %APPDATA%\CollectFilesPlus dan cache di
%LOCALAPPDATA%\CollectFilesPlus (aman dihapus).


KALAU ADA MASALAH
-----------------
- "Windows protected your PC": klik More info > Run anyway
  (aplikasi ini belum punya tanda tangan digital).
- File .aep tidak bisa dibaca: project dari After Effects versi sangat baru
  mungkin belum didukung. Pakai script-nya: di After Effects,
  File > Scripts > Run Script File..., pilih jsx\CollectFilesPlus.jsx
  (nyalakan dulu "Allow Scripts to Write Files and Access Network" di
  Preferences > Scripting & Expressions).
- Plugin bertanda [!] atau "perkiraan": cek file plugin yang tertulis di
  laporan sebelum dicopy.
- Command line: collect-files-plus.exe --help


Lisensi: MIT (LICENSE). Pemberitahuan pihak ketiga: NOTICE.md.
