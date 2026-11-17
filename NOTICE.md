# Pihak ketiga / Third-party notices

Collect Files Plus memakai atau menyertakan karya berikut. Terima kasih kepada para pembuatnya.

## Pustaka / Libraries

| Komponen | Dipakai untuk | Lisensi |
|---|---|---|
| [py_aep](https://github.com/forticheprod/py-aep) — © Fortiche Production | membaca dan menyimpan file `.aep` | MIT |
| [fontTools](https://github.com/fonttools/fonttools) | membaca nama PostScript font | MIT |
| [attrs](https://github.com/python-attrs/attrs), [PyYAML](https://github.com/yaml/pyyaml) | dependensi py_aep | MIT |
| [uharfbuzz](https://github.com/harfbuzz/uharfbuzz) / [HarfBuzz](https://github.com/harfbuzz/harfbuzz) | dependensi py_aep | Apache-2.0 / Old MIT |
| [Sun Valley ttk theme (sv-ttk)](https://github.com/rdbende/Sun-Valley-ttk-theme) — © rdbende | tema tampilan terang/gelap | MIT |
| [Python](https://www.python.org/) dan Tcl/Tk | runtime di build `.exe` / `.app` | PSF License / Tcl/Tk License |
| [PyInstaller](https://pyinstaller.org/) bootloader | build `.exe` / `.app` | GPL-2.0 dengan pengecualian bootloader (boleh dipakai untuk mendistribusikan aplikasi) |
| [WiX Toolset](https://wixtoolset.org/) v5 | membuat installer `.msi` (termasuk dialog WixUI) | MS-RL (tidak berlaku untuk installer yang dihasilkan) |

## Data

- Daftar match name efek bawaan After Effects (`src/collect_files_plus/firstparty.py`, juga di dalam `jsx/CollectFilesPlus.jsx`) disusun dari halaman *First-Party Effect Match Names* di [After Effects Scripting Guide](https://github.com/docsforadobe/after-effects-scripting-guide) (docsforadobe).
- `tests/data/*.aep` adalah file contoh dari [boltframe/aftereffects-aep-parser](https://github.com/boltframe/aftereffects-aep-parser), © 2020 Boltframe, MIT. Lihat `tests/data/LICENSE-boltframe.txt`.
- Pembuat resource PiPL untuk test (`tests/helpers.py`) mengikuti format dari crate `pipl` di [virtualritz/after-effects](https://github.com/virtualritz/after-effects) (MIT OR Apache-2.0).

## Merek dagang / Trademarks

After Effects adalah merek dagang Adobe Inc. Proyek ini independen dan tidak berafiliasi dengan atau didukung oleh Adobe. Nama plugin dan vendor pihak ketiga yang disebut di dokumentasi adalah merek dagang pemiliknya masing-masing.
