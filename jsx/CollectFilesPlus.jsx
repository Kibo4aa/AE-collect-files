/*
    Collect Files Plus  v4  -  script After Effects
    ===============================================
    Mengumpulkan semua kebutuhan project ke satu folder:

      (Footage)         footage, proxy, image sequence, PSD/AI berlayer, model 3D.
                        Project di-relink ke file hasil copy dan disimpan sebagai
                        project baru di folder hasil. Project asli tidak diubah.
                        Opsional: Reduce Project (buang comp & footage tidak dipakai).
      (Fonts)           file font yang dipakai text layer.
      (Plugins)         HANYA file plugin (.aex / .plugin) yang berisi efek yang
                        benar-benar dipakai, bukan seluruh folder plugin/vendor.
                        Sebelum dicopy muncul daftar yang bisa dicentang.
      (PresetEffects)   definisi efek dari PresetEffects.xml yang dipakai project.
      (Presets)         animation preset .ffx yang namanya sama dengan efek yang
                        di-rename di project (opsional).
      <project>_report.txt        laporan lengkap + cara pasang di komputer lain.
      <project>_daftar_efek.csv   SEMUA efek di project, per comp & layer
                                  (bisa dibuka di Excel).

    Cara pakai : File > Scripts > Run Script File...  lalu pilih file ini.
    Wajib aktif: Preferences > Scripting & Expressions >
                 "Allow Scripts to Write Files and Access Network".

    Cara script mencari plugin:
      - Efek dibaca dari comp yang dipilih di panel Project (atau Render Queue /
        semua comp) beserta semua precomp di dalamnya, termasuk efek yang
        di-rename. Efek yang ikon fx-nya mati bisa dilewati.
      - Efek bawaan dikenali dari daftar resmi match name efek After Effects,
        bukan dari awalan nama, jadi plugin pihak ketiga tidak ikut terlewat.
      - Untuk tiap file plugin (.aex / .plugin) di semua folder yang dimuat AE,
        script membaca data PiPL di dalam file untuk tahu efek apa saja yang
        ada di file itu, lalu mencocokkannya dengan match name efek di project.
*/
(function collectFilesPlus() {

    var SCRIPT_NAME = "Collect Files Plus";
    var SETTINGS_SECTION = "CollectFilesPlus";
    var PICKER_VERSION = "3";

    var SCAN_CHUNK = 4 * 1024 * 1024;           // file dibaca per 4 MB
    var SCAN_OVERLAP = 600;                     // tumpang-tindih antar potongan baca
    var RSRC_MAX = 256 * 1024 * 1024;           // batas baca resource section plugin
    var FALLBACK_BUDGET = 2048 * 1024 * 1024;   // batas baca untuk pencarian cadangan
    var PLUGIN_DEPTH = 10;                      // AE turun 10 level folder plugin
    var FFX_LIMIT = 20000;

    var IMAGE_EXT = {
        "jpg": 1, "jpeg": 1, "png": 1, "tif": 1, "tiff": 1, "tga": 1, "exr": 1,
        "dpx": 1, "cin": 1, "bmp": 1, "psd": 1, "psb": 1, "sgi": 1, "rgb": 1,
        "iff": 1, "hdr": 1, "pic": 1, "pct": 1, "ai": 1, "eps": 1, "pdf": 1,
        "dng": 1, "crw": 1, "cr2": 1, "cr3": 1, "nef": 1, "arw": 1, "jp2": 1,
        "webp": 1, "heic": 1, "avif": 1
    };
    var LAYERED_EXT = { "psd": 1, "psb": 1, "ai": 1, "eps": 1, "pdf": 1 };
    var MODEL_EXT = { "gltf": 1, "obj": 1 };
    var MODEL_SIDE_EXT = {
        "bin": 1, "mtl": 1, "png": 1, "jpg": 1, "jpeg": 1, "tga": 1, "tif": 1,
        "tiff": 1, "bmp": 1, "webp": 1, "ktx2": 1, "exr": 1, "hdr": 1
    };
    var MODEL_TEX_DIR = /^(tex|texture|textures|map|maps|image|images|material|materials)$/i;

    // Daftar resmi match name efek bawaan After Effects (sampai AE 26.5),
    // sumber: After Effects Scripting Guide > First-Party Effect Match Names.
    var FIRST_PARTY_LIST =
        "ADBE AUX CHANNEL EXTRACT|ADBE DEPTH MATTE|ADBE DEPTH FIELD|EXtractoR|ADBE FOG_3D|ADBE ID MATTE|" +
        "IDentifier|ADBE Aud Reverse|ADBE Aud BT|ADBE Aud Delay|ADBE Aud_Flange|ADBE Aud HiLo|" +
        "ADBE Aud Modulator|ADBE Param EQ|ADBE Aud Reverb|ADBE Aud Stereo Mixer|ADBE Aud Tone|" +
        "ADBE Bilateral|ADBE Camera Lens Blur|ADBE CameraShakeDeblur|CS CrossBlur|CC Radial Blur|" +
        "CC Radial Fast Blur|CC Vector Blur|ADBE Channel Blur|ADBE Compound Blur|ADBE Motion Blur|" +
        "ADBE Box Blur2|ADBE Gaussian Blur 2|ADBE Radial Blur|ADBE Sharpen|ADBE Smart Blur|" +
        "ADBE Unsharp Mask2|ADBE Arithmetic|ADBE Blend|ADBE Calculations|CC Composite|" +
        "ADBE Channel Combiner|ADBE Compound Arithmetic|ADBE Invert|ADBE Minimax|" +
        "ADBE Remove Color Matting|ADBE Set Channels|ADBE Set Matte3|ADBE Shift Channels|" +
        "ADBE Solid Composite|CINEMA 4D Effect|ADBE AutoColor|ADBE AutoContrast|ADBE AutoLevels|" +
        "ADBE Black&White|ADBE Brightness & Contrast 2|ADBE Broadcast Colors|CS Color Neutralizer|" +
        "CC Color Offset|CS Kernel|CC Toner|ADBE Change Color|ADBE Change To Color|ADBE CHANNEL MIXER|" +
        "ADBE Color Balance 2|ADBE Color Balance (HLS)|ADBE Color Link|ADBE Deflicker|APC Colorama|" +
        "ADBE CurvesCustom|ADBE Equalize|ADBE Exposure2|ADBE Gamma/Pedestal/Gain2|ADBE HUE SATURATION|" +
        "ADBE Leave Color|ADBE Easy Levels2|ADBE Pro Levels2|ADBE Lumetri|ADBE PhotoFilterPS|" +
        "ADBE PS Arbitrary Map|ADBE SelectiveColor|ADBE ShadowHighlight|ADBE Tint|ADBE Tritone|" +
        "ADBE Vibrance|ADBE BEZMESH|ADBE Bulge|CC Bend It|CC Bender|CC Blobbylize|CC Flo Motion|" +
        "CC Griddler|CC Lens|CC Page Turn|CC Power Pin|CC Ripple Pulse|CC Slant|CC Smear|CC Split|" +
        "CC Split 2|CC Tiler|ADBE Corner Pin|ADBE Upscale|ADBE Displacement Map|ADBE LIQUIFY|" +
        "ADBE Magnify|ADBE MESH WARP|ADBE Mirror|ADBE Offset|ADBE Optics Compensation|" +
        "ADBE Polar Coordinates|ADBE RESHAPE|ADBE Ripple|ADBE Rolling Shutter|ADBE SCHMEAR|ADBE Spherize|" +
        "ADBE Geometry2|ADBE Turbulent Displace|ADBE Twirl|ADBE WRPMESH|ADBE SubspaceStabilizer|" +
        "ADBE Wave Warp|ADBE Point3D Control|ADBE Angle Control|ADBE Checkbox Control|ADBE Color Control|" +
        "ADBE Dropdown Control|ADBE Layer Control|ADBE Point Control|ADBE Slider Control|" +
        "ADBE 4ColorGradient|ADBE Lightning 2|ADBE AudSpect|ADBE AudWave|ADBE Laser|CC Glue Gun|" +
        "CC Light Burst 2.5|CC Light Rays|CC Light Sweep|CS Threads|ADBE Cell Pattern|ADBE Checkerboard|" +
        "ADBE Circle|ADBE ELLIPSE|ADBE Eyedropper Fill|ADBE Fill|ADBE Fractal|ADBE Ramp|ADBE Grid|" +
        "ADBE Lens Flare|ADBE Paint Bucket|APC Radio Waves|ADBE Scribble Fill|ADBE Stroke|APC Vegas|" +
        "ADBE Write-on|ADBE Spill2|CC Simple Wire Removal|ADBE Color Difference Key|ADBE Color Range|" +
        "ADBE Difference Matte2|ADBE Extract|ADBE ATG Extract|ADBE KeyCleaner|Keylight 906|" +
        "ADBE Linear Color Key2|ADBE Matte Choker|ISL MochaShapeImporter|ADBE RefineRBMatte|" +
        "ADBE RefineMatte2|ADBE Simple Choker|VISINF Grain Implant|ADBE Dust & Scratches|" +
        "ADBE Fractal Noise|VISINF Grain Duplication|ADBE Median|ADBE Noise|ADBE Noise Alpha2|" +
        "ADBE Noise HLS2|ADBE Noise HLS Auto2|VISINF Grain Removal|ADBE AIF Perlin Noise 3D|" +
        "ADBE Basic 3D|ADBE Basic Text2|ADBE Color Key|ADBE Fast Blur|ADBE Gaussian Blur|ADBE Lightning|" +
        "ADBE Luma Key|ADBE Path Text|ADBE Reduce Interlace Flicker|ADBE Spill Suppressor|" +
        "ADBE 3D Tracker|ADBE 3D Glasses2|ADBE Bevel Alpha|ADBE Bevel Edges|CC Cylinder|CC Environment|" +
        "CC Sphere|CC Spotlight|ADBE Drop Shadow|ADBE Radial Shadow|APC CardDanceCam|APC Caustics|" +
        "CC Ball Action|CC Bubbles|CC Drizzle|CC Hair|CC Mr. Mercury|CC Particle Systems II|" +
        "CC Particle World|CC Pixel Polly|CSRainfall|CC Scatterize|CSSnowfall|CC Star Burst|APC Foam|" +
        "ADBE Playgnd|APC Shatter|APC Wave World|ADBE Brush Strokes|ADBE Cartoonify|CS BlockLoad|" +
        "CC Burn Film|CC Glass|CS HexTile|CC Kaleida|CC Mr. Smoothie|CC Plastic|CC RepeTile|CC Threshold|" +
        "CC Threshold RGB|CS Vignette|ADBE Color Emboss|ADBE Emboss|ADBE Find Edges|ADBE Glo2|" +
        "ADBE Mosaic|ADBE Tile|ADBE Posterize|ADBE Roughen Edges|ADBE Scatter|ADBE Strobe|ADBE Texturize|" +
        "ADBE Threshold2|SYNTHAP CF Color Finesse 2|ADBE Numbers2|ADBE Timecode|CC Force Motion Blur|" +
        "CC Wide Time|ADBE Echo|ADBE OFMotionBlur|ADBE Posterize Time|ADBE Difference|" +
        "ADBE Time Displacement|ADBE Timewarp|ADBE Block Dissolve|APC CardWipeCam|CC Glass Wipe|" +
        "CC Grid Wipe|CC Image Wipe|CC Jaws|CC Light Wipe|CS LineSweep|CC Radial ScaleWipe|CC Scale Wipe|" +
        "CC Twister|CC WarpoMatic|ADBE Gradient Wipe|ADBE IRIS_WIPE|ADBE Linear Wipe|ADBE Radial Wipe|" +
        "ADBE Venetian Blinds|ADBE Apply Color LUT2|CC Overbrights|ADBE Cineon Converter2|" +
        "ADBE ProfileToProfile|ADBE GROW BOUNDS|ADBE Compander|ADBE HDR ToneMap|ADBE Paint|ADBE Samurai|" +
        "ADBE FreePin3|ADBE RefineMatte|ADBE 3D Glasses|ADBE Alpha Levels2|ADBE Alpha Levels3|" +
        "ADBE Apply Color LUT|ADBE Brightness & Contrast|ADBE Box Blur|ADBE Cineon Converter|" +
        "ADBE Color Balance|CC PS Classic|CC PS LE Classic|CC Rain|CC Snow|CC Time Blend|" +
        "CC Time Blend FX|ADBE Exposure|ADBE Easy Levels|ADBE Pro Levels|ADBE Noise Alpha|ADBE Noise HLS|" +
        "ADBE Noise HLS Auto|ADBE PSL Bevel Emboss|ADBE PSL Drop Shadow|ADBE PSL Inner Glow|" +
        "ADBE PSL Inner Shadow|ADBE PSL Outer Glow|ADBE PSL Solid Fill|ADBE Photo Filter|ADBE Set Matte2|" +
        "ADBE Three-Way Color Corrector|ADBE Threshold|ADBE Geometry|ADBE Unsharp Mask|ADBE Vector Paint";

    var FIRST_PARTY = {};
    (function () {
        var a = FIRST_PARTY_LIST.split("|");
        for (var i = 0; i < a.length; i++) { FIRST_PARTY["#" + a[i]] = 1; }
    })();

    // Folder "struktural" (bukan folder milik satu plugin).
    var STRUCTURAL_DIRS = {
        "effects": 1, "effect": 1, "format": 1, "formats": 1, "keyframe": 1,
        "extensions": 1, "aegp": 1, "standard": 1, "plug-ins": 1, "plugins": 1,
        "plugin": 1, "mediacore": 1, "common": 1
    };
    var SKIP_DIR_EXT = { "app": 1, "bundle": 1, "framework": 1 };
    var GENERIC_TOKENS = {
        "adbe": 1, "effect": 1, "effects": 1, "plugin": 1, "plugins": 1,
        "the": 1, "and": 1, "pseudo": 1
    };

    // Penanda properti PiPL. Windows menyimpan kode 4 huruf terbalik
    // (little-endian), Mac apa adanya (big-endian).
    var PIPL_MARKERS = ["MIB8ANMe", "8BIMeMNA", "MIB8eman", "8BIMname", "MIB8gtac", "8BIMcatg"];
    var PIPL_KEYS = ["mn", "mn", "name", "name", "cat", "cat"];

    var INTERP_PROPS = ["alphaMode", "premulColor", "invertAlpha", "conformFrameRate",
        "fieldSeparationType", "highQualityFieldSeparation", "removePulldown", "loop"];

    // ================================================================ util

    function isWin() {
        return $.os.indexOf("Windows") !== -1;
    }

    function str(v) {
        return (v === undefined || v === null) ? "" : String(v);
    }

    function trim(s) {
        return str(s).replace(/^\s+|\s+$/g, "");
    }

    function dname(fsObj) {
        try {
            return File.decode(fsObj.name);
        } catch (e) {
            return str(fsObj.name);
        }
    }

    function getExt(name) {
        var i = name.lastIndexOf(".");
        return (i === -1) ? "" : name.substring(i + 1).toLowerCase();
    }

    function stripExt(name) {
        var i = name.lastIndexOf(".");
        return (i <= 0) ? name : name.substring(0, i);
    }

    function startsWith(s, p) {
        return s.substring(0, p.length) === p;
    }

    function endsWith(s, p) {
        return s.length >= p.length && s.substring(s.length - p.length) === p;
    }

    function pathKey(fsObj) {
        var p = str(fsObj.fsName);
        return isWin() ? p.toLowerCase() : p;
    }

    function pathSep() {
        return isWin() ? "\\" : "/";
    }

    function isAscii(s) {
        return /^[\x20-\x7E]*$/.test(str(s));
    }

    function normKey(s) {
        return str(s).toLowerCase().replace(/[^a-z0-9]+/g, "");
    }

    function hasKeys(obj) {
        for (var k in obj) {
            if (obj.hasOwnProperty(k)) { return true; }
        }
        return false;
    }

    function formatBytes(n) {
        if (n >= 1073741824) { return (Math.round(n / 107374182.4) / 10) + " GB"; }
        if (n >= 1048576) { return (Math.round(n / 104857.6) / 10) + " MB"; }
        if (n >= 1024) { return Math.round(n / 1024) + " KB"; }
        return n + " B";
    }

    function makeFolder(folder) {
        if (folder.exists) { return true; }
        if (folder.parent && !folder.parent.exists) { makeFolder(folder.parent); }
        return folder.create();
    }

    // subFolder(parent, "a/b/c") membuat (kalau perlu) dan mengembalikan parent/a/b/c
    function subFolder(parent, rel) {
        var parts = str(rel).split("/"), f = parent;
        for (var i = 0; i < parts.length; i++) {
            if (parts[i]) { f = new Folder(f.absoluteURI + "/" + File.encode(parts[i])); }
        }
        makeFolder(f);
        return f;
    }

    function folderAt(parent, parts) {
        var f = parent;
        for (var i = 0; i < parts.length; i++) {
            f = new Folder(f.absoluteURI + "/" + File.encode(parts[i]));
        }
        return f;
    }

    function childFile(parent, name) {
        return new File(parent.absoluteURI + "/" + File.encode(name));
    }

    function shellQuote(s) {
        return "'" + str(s).replace(/'/g, "'\\''") + "'";
    }

    function readText(file, enc) {
        var s = "";
        try {
            file.encoding = enc || "UTF-8";
            if (file.open("r")) {
                s = file.read();
                file.close();
            }
        } catch (e) {
            try { file.close(); } catch (e2) {}
        }
        return str(s).replace(/^\uFEFF/, "");
    }

    function writeText(file, text, bom, lineFeed) {
        try {
            file.encoding = "UTF-8";
            if (lineFeed) { file.lineFeed = lineFeed; }
            if (!file.open("w")) { return false; }
            file.write((bom ? "\uFEFF" : "") + text);
            file.close();
            return true;
        } catch (e) {
            try { file.close(); } catch (e2) {}
            return false;
        }
    }

    function readBytes(file, start, n) {
        var s = "";
        try {
            file.encoding = "BINARY";
            if (!file.open("r")) { return ""; }
            if (start > 0) { file.seek(start, 0); }
            s = file.read(n);
            file.close();
        } catch (e) {
            try { file.close(); } catch (e2) {}
        }
        return str(s);
    }

    function u16le(s, o) {
        return (s.charCodeAt(o) | (s.charCodeAt(o + 1) << 8)) >>> 0;
    }

    function u32le(s, o) {
        return (s.charCodeAt(o) | (s.charCodeAt(o + 1) << 8) |
            (s.charCodeAt(o + 2) << 16) | (s.charCodeAt(o + 3) << 24)) >>> 0;
    }

    function u32be(s, o) {
        return ((s.charCodeAt(o) << 24) | (s.charCodeAt(o + 1) << 16) |
            (s.charCodeAt(o + 2) << 8) | s.charCodeAt(o + 3)) >>> 0;
    }

    var copyStats = { bytes: 0 };

    // Copy file ke folder. File yang sudah ada dengan ukuran sama dilewati.
    // renameIfDifferent: kalau nama sama tapi isi beda, beri akhiran " (2)".
    function copyFile(src, destFolder, renameIfDifferent) {
        var name = dname(src);
        var target = childFile(destFolder, name);
        if (target.exists && target.length === src.length) { return target; }
        if (target.exists && renameIfDifferent) {
            var base = stripExt(name), ext = getExt(name), n = 2;
            do {
                target = childFile(destFolder, base + " (" + n + ")" + (ext ? "." + ext : ""));
                n++;
            } while (target.exists && target.length !== src.length);
            if (target.exists) { return target; }
        }
        if (src.copy(target)) {
            copyStats.bytes += Math.max(0, src.length);
            return target;
        }
        return null;
    }

    function copyFolder(src, destParent) {
        makeFolder(destParent);
        var dst = new Folder(destParent.absoluteURI + "/" + src.name);
        if (!isWin()) {
            // ditto menjaga symlink & signature bundle .plugin di Mac
            try {
                system.callSystem("/usr/bin/ditto " + shellQuote(src.fsName) + " " + shellQuote(dst.fsName));
                if (dst.exists) { return true; }
            } catch (e) {}
        }
        makeFolder(dst);
        var ok = true, entries = src.getFiles() || [];
        for (var i = 0; i < entries.length; i++) {
            if (entries[i] instanceof Folder) {
                if (!copyFolder(entries[i], dst)) { ok = false; }
            } else if (entries[i] instanceof File) {
                if (!copyFile(entries[i], dst, false)) { ok = false; }
            }
        }
        return ok;
    }

    function measure(fsObj) {
        if (fsObj instanceof File) { return Math.max(0, fsObj.length); }
        var total = 0, entries = null;
        try { entries = fsObj.getFiles(); } catch (e) { entries = null; }
        if (!entries) { return 0; }
        for (var i = 0; i < entries.length; i++) { total += measure(entries[i]); }
        return total;
    }

    // ============================================================ progress

    var progWin = null, progText = null;

    function progress(msg) {
        try {
            if (!progWin) {
                progWin = new Window("palette", SCRIPT_NAME);
                progText = progWin.add("statictext", undefined, "");
                progText.preferredSize = [560, 20];
                progWin.show();
            }
            progText.text = msg;
            progWin.update();
        } catch (e) {}
    }

    function progressClose() {
        try { if (progWin) { progWin.close(); } } catch (e) {}
        progWin = null;
    }

    // ========================================================= preferences

    function canWriteFiles() {
        // AE baru memakai "Main Pref Section v2", AE lama "Main Pref Section".
        var sections = ["Main Pref Section v2", "Main Pref Section"];
        for (var i = 0; i < sections.length; i++) {
            try {
                if (app.preferences.getPrefAsLong(sections[i], "Pref_SCRIPTING_FILE_NETWORK_SECURITY") === 1) {
                    return true;
                }
            } catch (e) {}
        }
        try {   // cadangan: coba tulis file kecil di folder temp
            var t = new File(Folder.temp.absoluteURI + "/cfp_write_test.txt");
            if (t.open("w")) {
                t.write("ok");
                t.close();
                t.remove();
                return true;
            }
        } catch (e2) {}
        return false;
    }

    function openScriptingPrefs() {
        try { app.executeCommand(parseFloat(app.version) >= 16.1 ? 3131 : 2359); } catch (e) {}
    }

    function getSetting(key, def) {
        try {
            if (app.settings.haveSetting(SETTINGS_SECTION, key)) {
                return app.settings.getSetting(SETTINGS_SECTION, key);
            }
        } catch (e) {}
        return def;
    }

    function saveSetting(key, value) {
        try { app.settings.saveSetting(SETTINGS_SECTION, key, String(value)); } catch (e) {}
    }

    // ========================================================= pilih folder
    // Windows: dialog Explorer modern (IFileOpenDialog mode pilih folder) lewat
    // PowerShell, karena Folder.selectDialog di Windows masih memakai dialog
    // "Browse For Folder" model lama. Mac: Folder.selectDialog sudah native.

    function pickerCSharp() {
        return [
            "using System;",
            "using System.Diagnostics;",
            "using System.Drawing;",
            "using System.IO;",
            "using System.Runtime.InteropServices;",
            "using System.Windows.Forms;",
            "",
            "namespace CFP",
            "{",
            "    public static class FolderPicker",
            "    {",
            "        [ComImport, Guid(\"DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7\")]",
            "        private class FileOpenDialogCom",
            "        {",
            "        }",
            "",
            "        [ComImport, Guid(\"42f85136-db7e-439c-85f1-e4075d135fc8\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]",
            "        private interface IFileDialog",
            "        {",
            "            [PreserveSig] int Show(IntPtr parent);",
            "            void SetFileTypes(uint cFileTypes, IntPtr rgFilterSpec);",
            "            void SetFileTypeIndex(uint iFileType);",
            "            void GetFileTypeIndex(out uint piFileType);",
            "            void Advise(IntPtr pfde, out uint pdwCookie);",
            "            void Unadvise(uint dwCookie);",
            "            void SetOptions(uint fos);",
            "            void GetOptions(out uint pfos);",
            "            void SetDefaultFolder(IShellItem psi);",
            "            void SetFolder(IShellItem psi);",
            "            void GetFolder(out IShellItem ppsi);",
            "            void GetCurrentSelection(out IShellItem ppsi);",
            "            void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string pszName);",
            "            void GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string pszName);",
            "            void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string pszTitle);",
            "            void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string pszText);",
            "            void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string pszLabel);",
            "            void GetResult(out IShellItem ppsi);",
            "            void AddPlace(IShellItem psi, int fdap);",
            "            void SetDefaultExtension([MarshalAs(UnmanagedType.LPWStr)] string pszDefaultExtension);",
            "            void Close(int hr);",
            "            void SetClientGuid([In] ref Guid guid);",
            "            void ClearClientData();",
            "            void SetFilter(IntPtr pFilter);",
            "        }",
            "",
            "        [ComImport, Guid(\"43826D1E-E718-42EE-BC55-A1E261C37BFE\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]",
            "        private interface IShellItem",
            "        {",
            "            void BindToHandler(IntPtr pbc, [In] ref Guid bhid, [In] ref Guid riid, out IntPtr ppv);",
            "            void GetParent(out IShellItem ppsi);",
            "            void GetDisplayName(uint sigdnName, [MarshalAs(UnmanagedType.LPWStr)] out string ppszName);",
            "            void GetAttributes(uint sfgaoMask, out uint psfgaoAttribs);",
            "            void Compare(IShellItem psi, uint hint, out int piOrder);",
            "        }",
            "",
            "        [StructLayout(LayoutKind.Sequential)]",
            "        private struct RECT",
            "        {",
            "            public int Left;",
            "            public int Top;",
            "            public int Right;",
            "            public int Bottom;",
            "        }",
            "",
            "        [DllImport(\"shell32.dll\", CharSet = CharSet.Unicode, PreserveSig = false)]",
            "        private static extern void SHCreateItemFromParsingName([MarshalAs(UnmanagedType.LPWStr)] string pszPath, IntPtr pbc, [In] ref Guid riid, [MarshalAs(UnmanagedType.Interface)] out IShellItem ppv);",
            "",
            "        [DllImport(\"user32.dll\")]",
            "        private static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);",
            "",
            "        [DllImport(\"user32.dll\")]",
            "        private static extern bool SetForegroundWindow(IntPtr hWnd);",
            "",
            "        [DllImport(\"user32.dll\")]",
            "        private static extern bool SetProcessDPIAware();",
            "",
            "        private static Rectangle HostArea()",
            "        {",
            "            try",
            "            {",
            "                foreach (Process p in Process.GetProcessesByName(\"AfterFX\"))",
            "                {",
            "                    IntPtr h = p.MainWindowHandle;",
            "                    RECT r;",
            "                    if (h != IntPtr.Zero && GetWindowRect(h, out r) && r.Right - r.Left > 100 && r.Bottom - r.Top > 100)",
            "                    {",
            "                        return Rectangle.FromLTRB(r.Left, r.Top, r.Right, r.Bottom);",
            "                    }",
            "                }",
            "            }",
            "            catch (Exception)",
            "            {",
            "            }",
            "            return Screen.PrimaryScreen.WorkingArea;",
            "        }",
            "",
            "        public static string Pick(string title, string initial)",
            "        {",
            "            try",
            "            {",
            "                SetProcessDPIAware();",
            "            }",
            "            catch (Exception)",
            "            {",
            "            }",
            "            Rectangle area = HostArea();",
            "            Form owner = new Form();",
            "            owner.FormBorderStyle = FormBorderStyle.None;",
            "            owner.ShowInTaskbar = false;",
            "            owner.TopMost = true;",
            "            owner.Opacity = 0;",
            "            owner.StartPosition = FormStartPosition.Manual;",
            "            owner.Size = new Size(1, 1);",
            "            owner.Location = new Point(area.Left + area.Width / 2, area.Top + area.Height / 2);",
            "            IFileDialog dlg = null;",
            "            try",
            "            {",
            "                owner.Show();",
            "                owner.Activate();",
            "                SetForegroundWindow(owner.Handle);",
            "                dlg = (IFileDialog)new FileOpenDialogCom();",
            "                uint opts;",
            "                dlg.GetOptions(out opts);",
            "                dlg.SetOptions(opts | 0x20u | 0x40u | 0x800u | 0x8u);",
            "                if (!String.IsNullOrEmpty(title))",
            "                {",
            "                    dlg.SetTitle(title);",
            "                }",
            "                if (!String.IsNullOrEmpty(initial) && Directory.Exists(initial))",
            "                {",
            "                    try",
            "                    {",
            "                        Guid iid = typeof(IShellItem).GUID;",
            "                        IShellItem folder;",
            "                        SHCreateItemFromParsingName(initial, IntPtr.Zero, ref iid, out folder);",
            "                        dlg.SetFolder(folder);",
            "                    }",
            "                    catch (Exception)",
            "                    {",
            "                    }",
            "                }",
            "                int hr = dlg.Show(owner.Handle);",
            "                if (hr != 0)",
            "                {",
            "                    return null;",
            "                }",
            "                IShellItem result;",
            "                dlg.GetResult(out result);",
            "                string path;",
            "                result.GetDisplayName(0x80058000u, out path);",
            "                return path;",
            "            }",
            "            finally",
            "            {",
            "                if (dlg != null)",
            "                {",
            "                    Marshal.ReleaseComObject(dlg);",
            "                }",
            "                owner.Close();",
            "                owner.Dispose();",
            "            }",
            "        }",
            "    }",
            "}"
        ];
    }

    function pickerPowerShell() {
        var head = [
            "param([string]$InFile, [string]$OutFile, [string]$DllFile)",
            "$ErrorActionPreference = 'Stop'",
            "function Write-Result([string]$Text) {",
            "    [System.IO.File]::WriteAllText($OutFile, $Text, (New-Object System.Text.UTF8Encoding($false)))",
            "}",
            "try {",
            "    $lines = [System.IO.File]::ReadAllLines($InFile, [System.Text.Encoding]::UTF8)",
            "    $title = 'Pilih folder'",
            "    $init = ''",
            "    if ($lines.Length -gt 0) { $title = $lines[0] }",
            "    if ($lines.Length -gt 1) { $init = $lines[1] }",
            "    Add-Type -AssemblyName System.Windows.Forms",
            "    Add-Type -AssemblyName System.Drawing",
            "    if (-not ('CFP.FolderPicker' -as [type])) {",
            "        $loaded = $false",
            "        if (Test-Path -LiteralPath $DllFile) {",
            "            try { Add-Type -Path $DllFile; $loaded = $true } catch { $loaded = $false }",
            "        }",
            "        if (-not $loaded) {",
            "            $src = @'"
        ];
        var tail = [
            "'@",
            "            $refs = @([System.Windows.Forms.Form].Assembly.Location, [System.Drawing.Size].Assembly.Location)",
            "            try {",
            "                Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -OutputAssembly $DllFile -OutputType Library",
            "            } catch {",
            "            }",
            "            if (-not ('CFP.FolderPicker' -as [type])) {",
            "                if (Test-Path -LiteralPath $DllFile) {",
            "                    try { Add-Type -Path $DllFile } catch { }",
            "                }",
            "            }",
            "            if (-not ('CFP.FolderPicker' -as [type])) {",
            "                Add-Type -TypeDefinition $src -ReferencedAssemblies $refs",
            "            }",
            "        }",
            "    }",
            "    $picked = [CFP.FolderPicker]::Pick($title, $init)",
            "    if ($picked) { Write-Result ('OK|' + $picked) } else { Write-Result 'CANCEL' }",
            "} catch {",
            "    Write-Result ('ERROR|' + $_.Exception.Message)",
            "}",
            ""
        ];
        return head.concat(pickerCSharp()).concat(tail).join("\n");
    }

    // Folder kerja sementara dengan path ASCII (aman untuk command line).
    function scratchFolder() {
        var cands = [];
        try { cands.push(Folder.temp); } catch (e) {}
        if (isWin()) {
            var pub = $.getenv("PUBLIC");
            if (pub) { cands.push(new Folder(pub + "\\Documents")); }
            var pd = $.getenv("ProgramData");
            if (pd) { cands.push(new Folder(pd)); }
        }
        for (var i = 0; i < cands.length; i++) {
            var c = cands[i];
            if (!c || !c.exists || !isAscii(c.fsName)) { continue; }
            var f = new Folder(c.absoluteURI + "/CollectFilesPlus");
            makeFolder(f);
            if (f.exists) { return f; }
        }
        return null;
    }

    function pickFolderWindows(title, startPath) {
        var dir = scratchFolder();
        if (!dir) { return { status: "error", message: "tidak ada folder sementara yang bisa dipakai" }; }

        var ps1 = new File(dir.absoluteURI + "/pick_folder_v" + PICKER_VERSION + ".ps1");
        var inF = new File(dir.absoluteURI + "/pick_in.txt");
        var outF = new File(dir.absoluteURI + "/pick_out.txt");
        var dll = new File(dir.absoluteURI + "/FolderPicker_v" + PICKER_VERSION + ".dll");

        if (!writeText(ps1, pickerPowerShell(), false, "Unix")) {
            return { status: "error", message: "tidak bisa menulis " + ps1.fsName };
        }
        writeText(inF, title + "\n" + str(startPath) + "\n", false, "Unix");
        try { if (outF.exists) { outF.remove(); } } catch (e0) {}

        var exe = "powershell.exe";
        var sysRoot = $.getenv("SystemRoot") || $.getenv("windir");
        if (sysRoot) {
            var full = new File(sysRoot + "\\System32\\WindowsPowerShell\\v1.0\\powershell.exe");
            if (full.exists && full.fsName.indexOf(" ") === -1) { exe = full.fsName; }
        }
        var cmd = exe + " -NoProfile -NonInteractive -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File \"" +
            ps1.fsName + "\" \"" + inF.fsName + "\" \"" + outF.fsName + "\" \"" + dll.fsName + "\"";

        var out = "";
        try {
            out = str(system.callSystem(cmd));
        } catch (e1) {
            return { status: "error", message: e1.toString() };
        }

        var txt = trim(readText(outF, "UTF-8"));
        if (startsWith(txt, "OK|")) {
            var f = new Folder(txt.substring(3));
            if (f.exists) { return { status: "ok", folder: f }; }
            return { status: "error", message: "folder tidak ditemukan: " + txt.substring(3) };
        }
        if (txt === "CANCEL") { return { status: "cancel" }; }
        if (startsWith(txt, "ERROR|")) { return { status: "error", message: txt.substring(6) }; }
        return { status: "error", message: "PowerShell tidak memberi hasil" + (trim(out) ? " (" + trim(out).substring(0, 200) + ")" : "") };
    }

    var pickerWarned = false;

    function pickFolder(title, startPath) {
        if (isWin()) {
            var r = pickFolderWindows(title, startPath);
            if (r.status === "ok") { return r.folder; }
            if (r.status === "cancel") { return null; }
            if (!pickerWarned) {
                pickerWarned = true;
                alert("Dialog Explorer tidak bisa dibuka:\n" + r.message +
                    "\n\nMemakai dialog pilih folder standar.", SCRIPT_NAME);
            }
        }
        var start = startPath ? new Folder(startPath) : null;
        try {
            if (start && start.exists) { return start.selectDlg(title); }
        } catch (e) {}
        return Folder.selectDialog(title);
    }

    // ================================================== interpretasi footage

    function snapInterp(item) {
        var s = { props: {}, pixelAspect: null };
        for (var i = 0; i < INTERP_PROPS.length; i++) {
            try { s.props[INTERP_PROPS[i]] = item.mainSource[INTERP_PROPS[i]]; } catch (e) {}
        }
        try { s.pixelAspect = item.pixelAspect; } catch (e2) {}
        return s;
    }

    function applyInterp(item, s) {
        for (var i = 0; i < INTERP_PROPS.length; i++) {
            var p = INTERP_PROPS[i];
            if (!s.props.hasOwnProperty(p) || s.props[p] === undefined) { continue; }
            try {
                if (item.mainSource[p] !== s.props[p]) { item.mainSource[p] = s.props[p]; }
            } catch (e) {}
        }
        try {
            if (s.pixelAspect !== null && item.pixelAspect !== s.pixelAspect) { item.pixelAspect = s.pixelAspect; }
        } catch (e2) {}
    }

    // ============================================================= footage

    function sequenceFiles(firstFile) {
        var m = dname(firstFile).match(/^(.*?)(\d+)(\.[^.]+)$/);
        if (!m) { return [firstFile]; }
        var prefix = m[1], suffix = m[3].toLowerCase();
        var all = firstFile.parent.getFiles() || [], out = [];
        for (var i = 0; i < all.length; i++) {
            if (!(all[i] instanceof File)) { continue; }
            var mm = dname(all[i]).match(/^(.*?)(\d+)(\.[^.]+)$/);
            if (mm && mm[1] === prefix && mm[3].toLowerCase() === suffix) { out.push(all[i]); }
        }
        return out.length ? out : [firstFile];
    }

    function copySequence(first, dest, label) {
        var files = sequenceFiles(first), ok = true;
        for (var i = 0; i < files.length; i++) {
            if (i % 25 === 0) { progress(label + "  (frame " + (i + 1) + "/" + files.length + ")"); }
            if (!copyFile(files[i], dest, false)) { ok = false; }
        }
        var nf = new File(dest.absoluteURI + "/" + first.name);
        return (ok && nf.exists) ? { file: nf, count: files.length } : null;
    }

    // File .gltf / .obj biasanya butuh .bin / .mtl / tekstur di sebelahnya.
    function copyModelExtras(src, dest) {
        var n = 0, all = src.parent.getFiles() || [];
        for (var i = 0; i < all.length; i++) {
            var en = all[i];
            if (en instanceof File) {
                if (pathKey(en) === pathKey(src)) { continue; }
                if (MODEL_SIDE_EXT[getExt(dname(en))] === 1 && copyFile(en, dest, false)) { n++; }
            } else if (en instanceof Folder && MODEL_TEX_DIR.test(dname(en))) {
                if (copyFolder(en, dest)) { n++; }
            }
        }
        return n;
    }

    function collectFromComp(comp, outItems, outComps, seen) {
        if (seen["c" + comp.id]) { return; }
        seen["c" + comp.id] = true;
        outComps.push(comp);
        for (var l = 1; l <= comp.numLayers; l++) {
            var s = null;
            try { s = comp.layer(l).source; } catch (e) { s = null; }
            if (!s) { continue; }
            if (s instanceof CompItem) {
                collectFromComp(s, outItems, outComps, seen);
            } else if (s instanceof FootageItem && !seen["f" + s.id]) {
                seen["f" + s.id] = true;
                outItems.push(s);
            }
        }
    }

    function folderIds(proj) {
        var ids = {};
        for (var i = 1; i <= proj.numItems; i++) {
            if (proj.item(i) instanceof FolderItem) { ids[proj.item(i).id] = true; }
        }
        return ids;
    }

    // Pindahkan semua pemakaian oldItem ke newItem, lalu hapus oldItem.
    function swapItem(oldItem, newItem) {
        applyInterp(newItem, snapInterp(oldItem));
        var comps = oldItem.usedIn;
        for (var c = 0; c < comps.length; c++) {
            var comp = comps[c];
            for (var l = 1; l <= comp.numLayers; l++) {
                var lay = comp.layer(l), s = null;
                try { s = lay.source; } catch (e) { s = null; }
                if (s && s.id === oldItem.id) {
                    try { lay.replaceSource(newItem, false); } catch (e2) {}
                }
            }
        }
        try { newItem.parentFolder = oldItem.parentFolder; } catch (e3) {}
        try { newItem.label = oldItem.label; } catch (e4) {}
        try { newItem.comment = oldItem.comment; } catch (e5) {}
        var name = oldItem.name;
        try { if (oldItem.usedIn.length === 0) { oldItem.remove(); } } catch (e6) {}
        try { newItem.name = name; } catch (e7) {}
    }

    // replace() mengubah item layer PSD/AI menjadi file utuh (merged).
    // Jadi file hasil copy di-import ulang sebagai composition, layer yang
    // cocok (nama + ukuran sama) dipasang menggantikan item lama.
    function relinkLayered(proj, oldItems, newFile) {
        var out = { ok: [], manual: [] };
        var pending = oldItems.slice();
        var modes = [ImportAsType.COMP_CROPPED_LAYERS, ImportAsType.COMP];
        var oldFolders = folderIds(proj);
        var tmpComps = [], tmpItems = [], kept = {};
        var i, k;

        for (var m = 0; m < modes.length && pending.length > 0; m++) {
            var io = null, imported = null;
            try {
                io = new ImportOptions(newFile);
                if (io.canImportAs(modes[m])) { io.importAs = modes[m]; } else { io = null; }
            } catch (e) { io = null; }
            if (!io) { continue; }

            try { app.beginSuppressDialogs(); } catch (e1) {}
            try { imported = proj.importFile(io); } catch (e2) { imported = null; }
            try { app.endSuppressDialogs(false); } catch (e3) {}

            if (!imported) { continue; }
            if (!(imported instanceof CompItem)) {
                tmpItems.push(imported);
                continue;
            }

            var newItems = [];
            collectFromComp(imported, newItems, tmpComps, {});
            for (k = 0; k < newItems.length; k++) { tmpItems.push(newItems[k]); }

            var used = {}, still = [];
            for (var p = 0; p < pending.length; p++) {
                var old = pending[p], match = null;
                for (k = 0; k < newItems.length; k++) {
                    var cand = newItems[k];
                    if (used[cand.id]) { continue; }
                    if (cand.name === old.name && cand.width === old.width && cand.height === old.height) {
                        match = cand;
                        break;
                    }
                }
                if (match) {
                    used[match.id] = true;
                    kept[match.id] = true;
                    var label = old.name;
                    swapItem(old, match);
                    out.ok.push(label);
                } else {
                    still.push(old);
                }
            }
            pending = still;
        }

        // Bersihkan comp, item, dan folder sementara hasil import.
        for (i = tmpComps.length - 1; i >= 0; i--) {
            try { tmpComps[i].remove(); } catch (e4) {}
        }
        for (i = 0; i < tmpItems.length; i++) {
            try { if (!kept[tmpItems[i].id]) { tmpItems[i].remove(); } } catch (e5) {}
        }
        for (var pass = 0; pass < 3; pass++) {
            for (i = proj.numItems; i >= 1; i--) {
                var f = proj.item(i);
                if (f instanceof FolderItem && !oldFolders[f.id] && f.numItems === 0) {
                    try { f.remove(); } catch (e6) {}
                }
            }
        }

        for (i = 0; i < pending.length; i++) { out.manual.push(pending[i].name); }
        return out;
    }

    function collectFootage(proj, destRoot, report) {
        var footRoot = subFolder(destRoot, "(Footage)");
        var folderMap = {}, usedNames = {};
        var st = { copied: 0, proxies: 0, missing: 0, failed: 0, manual: 0 };
        var i, it, src;

        function destFor(srcFolder) {
            var key = "#" + pathKey(srcFolder);
            if (folderMap[key]) { return folderMap[key]; }
            var base = dname(srcFolder).replace(/[:\\\/]/g, "") || "root";
            var name = base, n = 2;
            while (usedNames["#" + name.toLowerCase()]) {
                name = base + "_" + n;
                n++;
            }
            usedNames["#" + name.toLowerCase()] = true;
            folderMap[key] = subFolder(footRoot, name);
            return folderMap[key];
        }

        // Ambil daftar item dulu: selama proses, isi project bisa berubah.
        var all = [];
        for (i = 1; i <= proj.numItems; i++) { all.push(proj.item(i)); }

        report.push("=== FOOTAGE ===");

        // --- 1. Proxy
        for (i = 0; i < all.length; i++) {
            it = all[i];
            var ps = null;
            try { ps = it.proxySource; } catch (e0) { ps = null; }
            if (!(ps instanceof FileSource)) { continue; }
            var pf = ps.file;
            if (!pf || !pf.exists) {
                st.missing++;
                report.push("[PROXY HILANG] " + it.name + "  ->  " + (pf ? pf.fsName : "?"));
                continue;
            }
            progress("Proxy: " + it.name);
            try {
                var wasUsing = it.useProxy;
                var pdest = destFor(pf.parent);
                if (!ps.isStill && IMAGE_EXT[getExt(dname(pf))] === 1) {
                    var pseq = copySequence(pf, pdest, "Proxy: " + it.name);
                    if (!pseq) { throw new Error("copy sequence gagal"); }
                    it.setProxyWithSequence(pseq.file, false);
                } else {
                    var npf = copyFile(pf, pdest, false);
                    if (!npf) { throw new Error("copy gagal"); }
                    it.setProxy(npf);
                }
                it.useProxy = wasUsing;
                st.proxies++;
                report.push("[OK PROXY] " + it.name);
            } catch (e1) {
                st.failed++;
                report.push("[GAGAL PROXY] " + it.name + "  (" + e1.toString() + ")");
            }
        }

        // --- 2. Footage utama
        var refCount = {};
        for (i = 0; i < all.length; i++) {
            it = all[i];
            if (it instanceof FootageItem && it.mainSource instanceof FileSource && it.mainSource.file) {
                var rk = "#" + pathKey(it.mainSource.file);
                refCount[rk] = (refCount[rk] || 0) + 1;
            }
        }

        var layered = {}, layeredKeys = [];

        for (i = 0; i < all.length; i++) {
            it = all[i];
            if (!(it instanceof FootageItem) || !(it.mainSource instanceof FileSource)) { continue; }

            src = it.mainSource.file;
            if (it.footageMissing || !src || !src.exists) {
                st.missing++;
                report.push("[HILANG]  " + it.name + "  ->  " + (src ? src.fsName : "?"));
                continue;
            }

            var fname = dname(src), ext = getExt(fname), key = "#" + pathKey(src);
            var still = it.mainSource.isStill;

            // Item layer dari PSD/AI: diproses terpisah (lihat relinkLayered).
            if (LAYERED_EXT[ext] === 1 && still && it.name !== fname &&
                    (endsWith(it.name, "/" + fname) || refCount[key] > 1)) {
                if (!layered[key]) {
                    layered[key] = { file: src, items: [] };
                    layeredKeys.push(key);
                }
                layered[key].items.push(it);
                continue;
            }

            progress("Footage: " + it.name);
            try {
                var dest = destFor(src.parent);
                var snap = snapInterp(it);
                if (!still && IMAGE_EXT[ext] === 1) {
                    var seq = copySequence(src, dest, "Footage: " + it.name);
                    if (!seq) { throw new Error("copy sequence gagal"); }
                    it.replaceWithSequence(seq.file, false);
                    applyInterp(it, snap);
                    report.push("[OK]      " + it.name + "  (sequence, " + seq.count + " file)");
                } else {
                    var nf = copyFile(src, dest, false);
                    if (!nf) { throw new Error("copy gagal"); }
                    var extra = (MODEL_EXT[ext] === 1) ? copyModelExtras(src, dest) : 0;
                    it.replace(nf);
                    applyInterp(it, snap);
                    report.push("[OK]      " + it.name +
                        (extra ? "  (+" + extra + " file/folder pendukung model 3D)" : ""));
                }
                st.copied++;
            } catch (e2) {
                st.failed++;
                report.push("[GAGAL]   " + it.name + "  ->  " + src.fsName + "  (" + e2.toString() + ")");
            }
        }

        // --- 3. PSD / AI berlayer
        for (var g = 0; g < layeredKeys.length; g++) {
            var grp = layered[layeredKeys[g]];
            progress("File berlayer: " + dname(grp.file) + "  (" + grp.items.length + " layer)");
            var copied = copyFile(grp.file, destFor(grp.file.parent), false);
            if (!copied) {
                st.failed += grp.items.length;
                report.push("[GAGAL]   " + dname(grp.file) + "  (copy gagal, " + grp.items.length +
                    " item tetap menunjuk ke file asli)");
                continue;
            }
            var res;
            try {
                res = relinkLayered(proj, grp.items, copied);
            } catch (e3) {
                res = { ok: [], manual: [] };
                for (var q = 0; q < grp.items.length; q++) {
                    try { res.manual.push(grp.items[q].name); } catch (e4) {}
                }
            }
            for (var r = 0; r < res.ok.length; r++) {
                st.copied++;
                report.push("[OK LAYER] " + res.ok[r]);
            }
            for (r = 0; r < res.manual.length; r++) {
                st.manual++;
                report.push("[RELINK MANUAL] " + res.manual[r] +
                    "  (file sudah dicopy, tapi item ini masih menunjuk ke file asli)");
            }
        }

        report.push("Total: " + st.copied + " footage tercopy & di-relink, " + st.proxies + " proxy, " +
            st.missing + " hilang, " + st.failed + " gagal, " + st.manual + " perlu relink manual.");
        report.push("");
        return st;
    }

    // =============================================================== fonts

    function tryGet(obj, prop) {
        try { return obj[prop]; } catch (e) { return undefined; }
    }

    function fontFromObject(f) {
        return {
            ps: str(tryGet(f, "postScriptName")),
            family: str(tryGet(f, "familyName")),
            style: str(tryGet(f, "styleName")),
            location: str(tryGet(f, "location")),
            adobe: tryGet(f, "isFromAdobeFonts") === true,
            substitute: tryGet(f, "isSubstitute") === true
        };
    }

    // ID semua layer di comp yang dibaca (null = semua comp, tidak perlu disaring).
    function scopeLayerIds(scope) {
        if (!scope || scope.mode === "all") { return null; }
        var ids = {}, any = false;
        for (var i = 0; i < scope.comps.length; i++) {
            var c = scope.comps[i];
            for (var l = 1; l <= c.numLayers; l++) {
                try {
                    ids["#" + c.layer(l).id] = true;
                    any = true;
                } catch (e) {}
            }
        }
        return any ? ids : null;
    }

    function gatherFonts(proj, scope) {
        var list = [], seen = {}, methods = [];
        var ids = scopeLayerIds(scope);

        function add(o) {
            var key = o.ps || (o.family + "-" + o.style);
            if (!key || key === "-" || seen["#" + key]) { return; }
            seen["#" + key] = true;
            if (!o.adobe && /coresync|livetype/i.test(o.location)) { o.adobe = true; }
            list.push(o);
        }

        // AE 24.5+: semua font, termasuk yang campur dalam satu layer.
        // Disaring ke layer yang ada di comp yang dibaca.
        var used = null;
        try { used = proj.usedFonts; } catch (e) { used = null; }
        if (used && typeof used.length === "number") {
            for (var u = 0; u < used.length; u++) {
                var entry = used[u], keep = true;
                if (ids) {
                    var at = null;
                    try { at = entry.usedAt; } catch (e0) { at = null; }
                    if (at && at.length) {
                        keep = false;
                        for (var a = 0; a < at.length; a++) {
                            try {
                                if (ids["#" + at[a].layerID]) {
                                    keep = true;
                                    break;
                                }
                            } catch (e00) {}
                        }
                    }
                }
                if (!keep) { continue; }
                try { add(fontFromObject(entry.font)); } catch (e1) {}
            }
            methods.push("app.project.usedFonts");
        }

        // Semua versi: baca text layer (font karakter pertama, termasuk keyframe).
        var comps = scope ? scope.comps : [];
        for (var i = 0; i < comps.length; i++) {
            var comp = comps[i];
            for (var l = 1; l <= comp.numLayers; l++) {
                var layer = comp.layer(l);
                if (!(layer instanceof TextLayer)) { continue; }
                try {
                    var prop = layer.property("ADBE Text Properties").property("ADBE Text Document");
                    var docs = [prop.value];
                    for (var k = 1; k <= prop.numKeys; k++) { docs.push(prop.keyValue(k)); }
                    for (var d = 0; d < docs.length; d++) {
                        var td = docs[d], o = null;
                        var fo = tryGet(td, "fontObject");
                        if (fo) {
                            try { o = fontFromObject(fo); } catch (e2) { o = null; }
                        }
                        if (!o || !o.ps) {
                            o = {
                                ps: str(tryGet(td, "font")),
                                family: str(tryGet(td, "fontFamily")),
                                style: str(tryGet(td, "fontStyle")),
                                location: str(tryGet(td, "fontLocation")),
                                adobe: false,
                                substitute: false
                            };
                        }
                        add(o);
                    }
                } catch (e3) {}
            }
        }
        methods.push("scan text layer");
        return { list: list, method: methods.join(" + ") };
    }

    function collectFonts(proj, destRoot, report, scope) {
        var res = gatherFonts(proj, scope), fonts = res.list;
        var st = { total: fonts.length, copied: 0, skipped: 0 };
        var fontDir = null;

        report.push("=== FONT ===  (sumber data: " + res.method + ")");

        for (var i = 0; i < fonts.length; i++) {
            var f = fonts[i];
            var label = (f.ps || "?") + "  [" + f.family + (f.style ? " " + f.style : "") + "]";
            progress("Font: " + label);

            if (f.adobe) {
                st.skipped++;
                report.push("[ADOBE FONTS] " + label + "  -> aktifkan lewat Creative Cloud di komputer tujuan");
                continue;
            }
            if (f.substitute) {
                st.skipped++;
                report.push("[TIDAK TERINSTALL] " + label + "  -> font ini sudah hilang di komputer ini");
                continue;
            }
            if (!f.location) {
                st.skipped++;
                report.push("[LOKASI TIDAK DIKETAHUI] " + label + "  -> cari & copy manual");
                continue;
            }
            var src = new File(f.location);
            if (!src.exists) {
                st.skipped++;
                report.push("[FILE TIDAK ADA] " + label + "  ->  " + f.location);
                continue;
            }
            if (!fontDir) { fontDir = subFolder(destRoot, "(Fonts)"); }
            if (copyFile(src, fontDir, true)) {
                st.copied++;
                report.push("[OK]      " + label + "  <-  " + src.fsName);
            } else {
                st.skipped++;
                report.push("[GAGAL]   " + label + "  <-  " + src.fsName);
            }
        }

        if (!fonts.length) { report.push("Tidak ada font yang dipakai."); }
        report.push("Total: " + st.total + " font dipakai, " + st.copied + " tercopy, " +
            st.skipped + " tidak tercopy.");
        report.push("");
        return st;
    }

    // ===================================================== efek: inventaris

    // ------------------------------------------------ comp yang dibaca

    // Comp "akar" sesuai pilihan: yang dipilih di panel Project, yang ada di
    // Render Queue, atau semua comp di project.
    function scopeRoots(proj, mode) {
        var roots = [], seen = {}, i;

        function add(c) {
            if (c instanceof CompItem && !seen["#" + c.id]) {
                seen["#" + c.id] = true;
                roots.push(c);
            }
        }

        if (mode === "selected") {
            var sel = [];
            try { sel = proj.selection || []; } catch (e) { sel = []; }
            for (i = 0; i < sel.length; i++) { add(sel[i]); }
        } else if (mode === "rq") {
            try {
                var rq = proj.renderQueue;
                for (i = 1; i <= rq.numItems; i++) {
                    try { add(rq.item(i).comp); } catch (e1) {}
                }
            } catch (e2) {}
        } else {
            for (i = 1; i <= proj.numItems; i++) { add(proj.item(i)); }
        }
        return roots;
    }

    // Comp akar + semua precomp di dalamnya (berapa pun tingkatnya).
    function expandComps(roots) {
        var out = [], seen = {};

        function visit(c) {
            if (seen["#" + c.id]) { return; }
            seen["#" + c.id] = true;
            out.push(c);
            for (var l = 1; l <= c.numLayers; l++) {
                var s = null;
                try { s = c.layer(l).source; } catch (e) { s = null; }
                if (s instanceof CompItem) { visit(s); }
            }
        }

        for (var i = 0; i < roots.length; i++) { visit(roots[i]); }
        return out;
    }

    function makeScope(proj, mode, roots) {
        if (!roots) { roots = scopeRoots(proj, mode); }
        return { mode: mode, roots: roots, comps: (mode === "all") ? roots : expandComps(roots) };
    }

    function namesText(items, max) {
        var parts = [];
        for (var i = 0; i < items.length && i < max; i++) { parts.push(items[i].name); }
        if (items.length > max) { parts.push("... (+" + (items.length - max) + ")"); }
        return parts.join(", ");
    }

    // ------------------------------------------------ efek: inventaris

    function addUse(map, list, mn, use, comp) {
        var ef = map["#" + mn];
        if (!ef) {
            ef = {
                matchName: mn, count: 0, names: [], nameSeen: {},
                comps: [], compSeen: {}, uses: []
            };
            map["#" + mn] = ef;
            list.push(ef);
        }
        ef.count++;
        if (!ef.nameSeen["#" + use.instance]) {
            ef.nameSeen["#" + use.instance] = true;
            ef.names.push(use.instance);
        }
        if (!ef.compSeen["#" + comp.id]) {
            ef.compSeen["#" + comp.id] = true;
            ef.comps.push(comp.name);
        }
        ef.uses.push(use);
    }

    // Baca efek di comp yang dipilih saja. Efek yang ikon fx-nya mati bisa
    // dipisahkan (tidak ikut dikumpulkan).
    function gatherEffects(comps, skipDisabled) {
        var map = {}, list = [], dmap = {}, disabled = [];
        for (var i = 0; i < comps.length; i++) {
            var comp = comps[i];
            for (var l = 1; l <= comp.numLayers; l++) {
                var layer = comp.layer(l), fx = null, n = 0;
                try {
                    fx = layer.property("ADBE Effect Parade");
                    n = fx ? fx.numProperties : 0;
                } catch (e) {
                    fx = null;
                    n = 0;
                }
                for (var k = 1; k <= n; k++) {
                    var p = null, mn = "", inst = "", on = true;
                    try {
                        p = fx.property(k);
                        mn = str(p.matchName);
                        inst = str(p.name);
                    } catch (e1) {
                        mn = "";
                    }
                    if (!mn) { continue; }
                    try { on = p.enabled !== false; } catch (e2) { on = true; }
                    var use = { comp: comp.name, layer: "#" + l + " " + layer.name, instance: inst, enabled: on };
                    if (!on && skipDisabled) {
                        addUse(dmap, disabled, mn, use, comp);
                    } else {
                        addUse(map, list, mn, use, comp);
                    }
                }
            }
        }
        return { list: list, disabled: disabled };
    }

    function installedEffects() {
        try {
            var ae = app.effects;
            if (!ae || !ae.length) { return null; }
            var map = {};
            for (var i = 0; i < ae.length; i++) {
                map["#" + ae[i].matchName] = {
                    displayName: str(ae[i].displayName),
                    category: str(ae[i].category),
                    version: str(ae[i].version)
                };
            }
            return map;
        } catch (e) {
            return null;
        }
    }

    function isRenamed(instance, original) {
        if (!instance || !original) { return false; }
        return normKey(instance.replace(/\s+\d+$/, "")) !== normKey(original);
    }

    // ================================================= PresetEffects.xml

    function xmlEscape(s) {
        return str(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function loadPresetEffectsXml() {
        var cands = [];
        try { cands.push(new File(Folder.appPackage.absoluteURI + "/PresetEffects.xml")); } catch (e) {}
        try { cands.push(new File(Folder.appPackage.absoluteURI + "/Contents/Resources/PresetEffects.xml")); } catch (e1) {}
        try { cands.push(new File(Folder.startup.absoluteURI + "/PresetEffects.xml")); } catch (e2) {}
        try { cands.push(new File(Folder.startup.parent.absoluteURI + "/Resources/PresetEffects.xml")); } catch (e3) {}
        for (var i = 0; i < cands.length; i++) {
            if (cands[i].exists) {
                var t = readText(cands[i], "UTF-8");
                if (t) { return { file: cands[i], text: t }; }
            }
        }
        return null;
    }

    function findPresetEffectBlock(xmlText, mn) {
        var variants = [mn, xmlEscape(mn)], quotes = ["\"", "'"];
        for (var v = 0; v < variants.length; v++) {
            for (var q = 0; q < quotes.length; q++) {
                var idx = xmlText.indexOf("matchname=" + quotes[q] + variants[v] + quotes[q]);
                if (idx === -1) { continue; }
                var s = xmlText.lastIndexOf("<Effect", idx);
                var e = xmlText.indexOf("</Effect>", idx);
                if (s !== -1 && e !== -1) { return xmlText.substring(s, e + 9); }
            }
        }
        return null;
    }

    // ================================================= efek: lokasi plugin

    function isStructural(name) {
        return STRUCTURAL_DIRS[str(name).toLowerCase()] === 1;
    }

    function relParts(fsObj, rootFolder) {
        var a = str(fsObj.fsName).replace(/\\/g, "/");
        var b = str(rootFolder.fsName).replace(/\\/g, "/");
        var inside = isWin() ? startsWith(a.toLowerCase(), b.toLowerCase() + "/") : startsWith(a, b + "/");
        var rel = inside ? a.substring(b.length + 1) : dname(fsObj);
        var raw = rel.split("/"), parts = [];
        for (var i = 0; i < raw.length; i++) { if (raw[i]) { parts.push(raw[i]); } }
        return parts;
    }

    function pluginRoots() {
        var roots = [], seen = {};

        function add(folder, label, priority, isApp) {
            if (!folder || !folder.exists) { return; }
            var k = "#" + pathKey(folder);
            if (seen[k]) { return; }
            seen[k] = true;
            roots.push({ folder: folder, label: label, priority: priority, isApp: isApp });
        }

        if (isWin()) {
            var envs = ["ProgramW6432", "ProgramFiles"];
            for (var i = 0; i < envs.length; i++) {
                var pf = $.getenv(envs[i]);
                if (pf) { add(new Folder(pf + "\\Adobe\\Common\\Plug-ins\\7.0\\MediaCore"), "MediaCore", 1, false); }
            }
            add(new Folder("C:\\Program Files\\Adobe\\Common\\Plug-ins\\7.0\\MediaCore"), "MediaCore", 1, false);
        } else {
            add(new Folder("/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore"), "MediaCore", 1, false);
            add(new Folder("~/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore"), "MediaCore (user)", 1, false);
        }

        var bases = [];
        try { bases.push(Folder.appPackage); } catch (e) {}
        try { bases.push(Folder.appPackage.parent); } catch (e1) {}
        try { bases.push(Folder.startup); } catch (e2) {}
        for (var b = 0; b < bases.length; b++) {
            if (bases[b]) { add(new Folder(bases[b].absoluteURI + "/Plug-ins"), "AE Plug-ins", 2, true); }
        }

        roots.addRoot = add;
        return roots;
    }

    // "Plugin Loading.log" mencatat semua plugin yang benar-benar dimuat AE,
    // termasuk dari lokasi di luar folder standar.
    function pluginLogFiles() {
        var bases = [], cur = [], other = [];
        try { bases.push(new Folder(Folder.userData.absoluteURI + "/Adobe/After Effects")); } catch (e) {}
        if (!isWin()) { bases.push(new Folder("~/Library/Preferences/Adobe/After Effects")); }
        var major = parseInt(app.version, 10);
        for (var i = 0; i < bases.length; i++) {
            if (!bases[i].exists) { continue; }
            var vers = bases[i].getFiles() || [];
            for (var v = 0; v < vers.length; v++) {
                if (!(vers[v] instanceof Folder)) { continue; }
                var cands = [
                    new File(vers[v].absoluteURI + "/logs/Plugin Loading.log"),
                    new File(vers[v].absoluteURI + "/Plugin Loading.log")
                ];
                for (var c = 0; c < cands.length; c++) {
                    if (cands[c].exists) {
                        if (parseInt(dname(vers[v]), 10) === major) { cur.push(cands[c]); } else { other.push(cands[c]); }
                    }
                }
            }
        }
        return cur.concat(other);
    }

    function parsePluginLogs(files) {
        var out = { roots: [], files: [] }, seen = {};
        for (var i = 0; i < files.length; i++) {
            var lines = readText(files[i]).split(/\r\n|\r|\n/);
            for (var l = 0; l < lines.length; l++) {
                var line = lines[l], m;
                m = line.match(/Loading from root path:\s*"?(.+?)"?\s*$/i);
                if (m) {
                    if (!seen["r" + m[1]]) {
                        seen["r" + m[1]] = true;
                        out.roots.push(m[1]);
                    }
                    continue;
                }
                m = line.match(/Loading\s+"?(.+?\.(?:aex|plugin))(?=["\s\/\\]|$)/i);
                if (m && !seen["f" + m[1]]) {
                    seen["f" + m[1]] = true;
                    out.files.push(m[1]);
                }
            }
        }
        return out;
    }

    function makePlugin(target, root, isBundle) {
        var parts = relParts(target, root.folder);
        var rsrc = [], bins = [], size = 0, r;
        if (isBundle) {
            var res = new Folder(target.absoluteURI + "/Contents/Resources");
            if (res.exists) {
                var rs = res.getFiles("*.rsrc") || [];
                for (r = 0; r < rs.length; r++) { if (rs[r] instanceof File) { rsrc.push(rs[r]); } }
            }
            var bin = new Folder(target.absoluteURI + "/Contents/MacOS");
            if (bin.exists) {
                var bs = bin.getFiles() || [];
                for (r = 0; r < bs.length; r++) { if (bs[r] instanceof File) { bins.push(bs[r]); } }
            }
            for (r = 0; r < rsrc.length; r++) { size += Math.max(0, rsrc[r].length); }
            for (r = 0; r < bins.length; r++) { size += Math.max(0, bins[r].length); }
        } else {
            size = Math.max(0, target.length);
        }
        return {
            target: target, isBundle: isBundle, root: root, parts: parts,
            rsrc: rsrc, bins: bins, size: size,
            hay: parts.join(" ").toLowerCase(), score: 0,
            entries: null, hasPiPL: false
        };
    }

    function addPlugin(out, seen, target, root, isBundle) {
        var k = "#" + pathKey(target);
        if (seen[k]) { return; }
        seen[k] = true;
        out.push(makePlugin(target, root, isBundle));
    }

    function listPlugins(folder, root, out, depth, seen, seenDirs) {
        if (depth > PLUGIN_DEPTH) { return; }
        var dk = "#" + pathKey(folder);
        if (seenDirs[dk]) { return; }
        seenDirs[dk] = true;
        var entries = null;
        try { entries = folder.getFiles(); } catch (e) { entries = null; }
        if (!entries) { return; }
        for (var i = 0; i < entries.length; i++) {
            var en = entries[i];
            if (!isWin() && en instanceof File && en.alias) {
                // AE mengikuti alias di Mac (shortcut Windows tidak diikuti AE).
                var t = null;
                try { t = en.resolve(); } catch (e1) { t = null; }
                if (!t) { continue; }
                en = t;
            }
            var name = dname(en), ext = getExt(name);
            if (en instanceof Folder) {
                if (/^\(.*\)$/.test(name)) { continue; }   // folder (dalam kurung) tidak dimuat AE
                if (ext === "plugin") {
                    addPlugin(out, seen, en, root, true);
                } else if (SKIP_DIR_EXT[ext] !== 1) {
                    listPlugins(en, root, out, depth + 1, seen, seenDirs);
                }
            } else if (en instanceof File && ext === "aex") {
                addPlugin(out, seen, en, root, false);
            } else if (en instanceof File && ext === "plugin") {
                var bundle = new Folder(en.fsName);
                if (bundle.exists) { addPlugin(out, seen, bundle, root, true); }
            }
        }
    }

    function addTokens(map, s) {
        var parts = str(s).toLowerCase().split(/[^a-z0-9]+/);
        for (var i = 0; i < parts.length; i++) {
            if (parts[i].length >= 3 && GENERIC_TOKENS[parts[i]] !== 1) { map["#" + parts[i]] = parts[i]; }
        }
    }

    function buildPluginList(wanted) {
        var roots = pluginRoots(), plugins = [], seen = {}, seenDirs = {};
        var i;

        progress("Membaca Plugin Loading.log...");
        var log = parsePluginLogs(pluginLogFiles());
        for (i = 0; i < log.roots.length; i++) {
            var lr = new Folder(log.roots[i]);
            roots.addRoot(lr, "Lainnya/" + dname(lr), 3, false);
        }

        for (i = 0; i < roots.length; i++) {
            progress("Mendata plugin di " + roots[i].folder.fsName);
            listPlugins(roots[i].folder, roots[i], plugins, 0, seen, seenDirs);
        }
        for (i = 0; i < log.files.length; i++) {
            var p = log.files[i], isBundle = /\.plugin$/i.test(p);
            var fo = isBundle ? new Folder(p) : new File(p);
            if (!fo.exists) { continue; }
            var root = { folder: fo.parent, label: "Lainnya/" + dname(fo.parent), priority: 4, isApp: false };
            addPlugin(plugins, seen, fo, root, isBundle);
        }

        // Plugin yang path-nya mirip nama efek dicek duluan (lebih cepat ketemu).
        var toks = {};
        for (i = 0; i < wanted.length; i++) {
            addTokens(toks, wanted[i].matchName);
            addTokens(toks, wanted[i].displayName);
            for (var n = 0; n < wanted[i].names.length; n++) { addTokens(toks, wanted[i].names[n]); }
        }
        for (i = 0; i < plugins.length; i++) {
            var sc = 0;
            for (var t in toks) {
                if (toks.hasOwnProperty(t) && plugins[i].hay.indexOf(toks[t]) !== -1) { sc++; }
            }
            plugins[i].score = sc;
        }
        plugins.sort(function (a, b) {
            if (a.score !== b.score) { return b.score - a.score; }
            if (a.root.priority !== b.root.priority) { return a.root.priority - b.root.priority; }
            return a.size - b.size;
        });
        return plugins;
    }

    // ---------------------------------------------------------------- PiPL

    // Lokasi resource section (.rsrc) di file PE (.aex Windows).
    // null = bukan file PE; size 0 = tidak ada resource di file.
    function peResourceRange(file) {
        var h = readBytes(file, 0, 4096);
        if (h.length < 64 || h.substring(0, 2) !== "MZ") { return null; }
        var pe = u32le(h, 60);
        if (pe < 64 || pe > 1048576) { return null; }
        if (pe + 264 > h.length) { h = readBytes(file, 0, pe + 4096); }
        if (h.length < pe + 24 || h.substr(pe, 4) !== "PE\u0000\u0000") { return null; }
        var nsec = u16le(h, pe + 6), optSize = u16le(h, pe + 20), opt = pe + 24;
        var magic = u16le(h, opt);
        var dd = (magic === 0x20b) ? opt + 112 : opt + 96;
        if (dd + 24 > opt + optSize || u32le(h, dd - 4) < 3) { return { start: 0, size: 0 }; }
        var rva = u32le(h, dd + 16);
        if (!rva) { return { start: 0, size: 0 }; }
        var sec = opt + optSize;
        if (sec + nsec * 40 > h.length) { h = readBytes(file, 0, sec + nsec * 40 + 64); }
        for (var i = 0; i < nsec; i++) {
            var s = sec + i * 40;
            if (s + 40 > h.length) { break; }
            var vsize = u32le(h, s + 8), va = u32le(h, s + 12);
            var rawSize = u32le(h, s + 16), rawPtr = u32le(h, s + 20);
            if (rva >= va && rva < va + Math.max(vsize, rawSize)) {
                var avail = rawSize - (rva - va);
                if (avail <= 0) { return { start: 0, size: 0 }; }
                return { start: rawPtr + (rva - va), size: avail };
            }
        }
        return { start: 0, size: 0 };
    }

    function parsePiPLProp(data, k, m, state) {
        if (k + 17 > data.length) { return; }
        var len = (m % 2 === 0) ? u32le(data, k + 12) : u32be(data, k + 12);
        var L = data.charCodeAt(k + 16);
        if (L < 1 || len < L + 1 || len > 1024 || k + 17 + L > data.length) { return; }
        var s = data.substr(k + 17, L);
        for (var i = 0; i < s.length; i++) {
            var c = s.charCodeAt(i);
            if (c < 32 || c === 127) { return; }
        }
        var key = PIPL_KEYS[m];
        if (key === "name") {
            state.curName = s;
            state.curCat = "";
        } else if (key === "cat") {
            state.curCat = s;
        } else {
            state.entries.push({ mn: s, name: state.curName, cat: state.curCat });
        }
    }

    // Baca rentang file per potongan dan ambil semua properti PiPL di dalamnya.
    function scanPiPLRange(file, start, size, state) {
        if (size <= 0) { return; }
        try {
            file.encoding = "BINARY";
            if (!file.open("r")) { return; }
            if (start > 0) { file.seek(start, 0); }
            var left = size, carry = "";
            while (true) {
                var n = Math.min(SCAN_CHUNK, left);
                var buf = (n > 0) ? str(file.read(n)) : "";
                left = (buf.length < n) ? 0 : left - n;
                var data = carry + buf;
                var more = left > 0;
                var limit = more ? data.length - SCAN_OVERLAP : data.length;
                if (limit < 0) { limit = 0; }
                var hits = [];
                for (var m = 0; m < PIPL_MARKERS.length; m++) {
                    var k = data.indexOf(PIPL_MARKERS[m]);
                    while (k !== -1 && k < limit) {
                        hits.push({ k: k, m: m });
                        k = data.indexOf(PIPL_MARKERS[m], k + 1);
                    }
                }
                hits.sort(function (a, b) { return a.k - b.k; });
                for (var h = 0; h < hits.length; h++) { parsePiPLProp(data, hits[h].k, hits[h].m, state); }
                if (!more) { break; }
                carry = data.substring(limit);
            }
        } catch (e) {}
        try { file.close(); } catch (e2) {}
    }

    function readPiPL(pl) {
        if (pl.entries) { return pl.entries; }
        var state = { entries: [], curName: "", curCat: "" }, i;
        if (pl.isBundle) {
            for (i = 0; i < pl.rsrc.length; i++) {
                state.curName = "";
                state.curCat = "";
                scanPiPLRange(pl.rsrc[i], 0, Math.min(pl.rsrc[i].length, RSRC_MAX), state);
            }
        } else {
            var rg = peResourceRange(pl.target);
            if (rg === null) {
                scanPiPLRange(pl.target, 0, Math.min(pl.target.length, RSRC_MAX), state);
            } else if (rg.size > 0) {
                scanPiPLRange(pl.target, rg.start, Math.min(rg.size, RSRC_MAX), state);
            }
        }
        pl.entries = state.entries;
        pl.hasPiPL = state.entries.length > 0;
        return pl.entries;
    }

    // Cocokkan match name efek dengan isi PiPL semua plugin.
    function matchByPiPL(plugins, needList) {
        var need = {}, needLoose = {}, left = 0, found = {}, nameIdx = {}, looseIdx = {};
        var i, e;
        for (i = 0; i < needList.length; i++) {
            need["#" + needList[i]] = true;
            needLoose["#" + normKey(needList[i])] = needList[i];
            left++;
        }
        for (i = 0; i < plugins.length && left > 0; i++) {
            var pl = plugins[i];
            progress("Membaca plugin " + (i + 1) + "/" + plugins.length + ": " + pl.parts.join(" / "));
            var entries = readPiPL(pl);
            for (e = 0; e < entries.length; e++) {
                var en = entries[e], k = "#" + en.mn;
                if (need[k] && !found[k]) {
                    found[k] = { plugin: pl, how: "pipl", effectName: en.name, category: en.cat };
                    left--;
                    continue;
                }
                var lk = "#" + normKey(en.mn);
                if (lk !== "#" && needLoose[lk] && !looseIdx[lk]) { looseIdx[lk] = { plugin: pl, en: en }; }
                if (en.name && !nameIdx["#" + en.name]) { nameIdx["#" + en.name] = { plugin: pl, en: en }; }
            }
        }
        for (i = 0; i < needList.length; i++) {
            var mk = "#" + needList[i];
            if (found[mk]) { continue; }
            if (nameIdx[mk]) {
                // plugin tanpa match name: AE memakai nama efek sebagai match name
                found[mk] = { plugin: nameIdx[mk].plugin, how: "pipl-nama", effectName: nameIdx[mk].en.name, category: nameIdx[mk].en.cat };
                continue;
            }
            var alt = looseIdx["#" + normKey(needList[i])];
            if (alt) {
                found[mk] = { plugin: alt.plugin, how: "pipl-mirip", effectName: alt.en.name, category: alt.en.cat };
            }
        }
        return found;
    }

    // ------------------------------------------------- pencarian cadangan

    function utf16le(s) {
        var o = "";
        for (var i = 0; i < s.length; i++) { o += s.charAt(i) + "\u0000"; }
        return o;
    }

    // Cari teks match name di seluruh isi file (untuk plugin yang dikompres /
    // yang PiPL-nya tidak terbaca). 2 = cocok kuat, 1 = cocok lemah.
    function scanFileNeedles(file, needles) {
        var hits = {};
        if (!needles.length) { return hits; }
        var pas = [], wide = [], i;
        for (i = 0; i < needles.length; i++) {
            pas.push(String.fromCharCode(Math.min(needles[i].length, 255)) + needles[i]);
            wide.push(utf16le(needles[i]));
        }
        try {
            file.encoding = "BINARY";
            if (!file.open("r")) { return hits; }
            var tail = "", left = needles.length;
            while (!file.eof && left > 0) {
                var buf = str(file.read(SCAN_CHUNK));
                if (!buf.length) { break; }
                var data = tail + buf;
                for (var j = 0; j < needles.length; j++) {
                    var nd = "#" + needles[j];
                    if (hits[nd] === 2) { continue; }
                    if (data.indexOf(pas[j]) !== -1) {
                        hits[nd] = 2;
                        left--;
                    } else if (!hits[nd] && (data.indexOf(needles[j]) !== -1 || data.indexOf(wide[j]) !== -1)) {
                        hits[nd] = 1;
                    }
                }
                tail = (data.length > SCAN_OVERLAP) ? data.substring(data.length - SCAN_OVERLAP) : data;
            }
            file.close();
        } catch (e) {
            try { file.close(); } catch (e2) {}
        }
        return hits;
    }

    function fullScanFiles(pl) {
        if (!pl.isBundle) { return [pl.target]; }
        return pl.rsrc.concat(pl.bins);
    }

    function fallbackScan(plugins, missing, found) {
        var order = plugins.slice(), pending = {}, weak = {}, left = 0, budget = FALLBACK_BUDGET, i;
        for (i = 0; i < missing.length; i++) {
            pending["#" + missing[i]] = missing[i];
            left++;
        }
        order.sort(function (a, b) {
            if (a.hasPiPL !== b.hasPiPL) { return a.hasPiPL ? 1 : -1; }
            if (a.score !== b.score) { return b.score - a.score; }
            return a.size - b.size;
        });
        for (i = 0; i < order.length && left > 0 && budget > 0; i++) {
            var pl = order[i], files = fullScanFiles(pl), needles = [];
            for (var k in pending) {
                if (pending.hasOwnProperty(k) && pending[k]) { needles.push(pending[k]); }
            }
            for (var f = 0; f < files.length && left > 0; f++) {
                budget -= Math.max(0, files[f].length);
                progress("Pencarian cadangan (" + (i + 1) + "/" + order.length + "): " + pl.parts.join(" / "));
                var hits = scanFileNeedles(files[f], needles);
                for (var h in hits) {
                    if (!hits.hasOwnProperty(h)) { continue; }
                    if (hits[h] === 2 && pending[h]) {
                        found[h] = { plugin: pl, how: "isi-file" };
                        pending[h] = null;
                        left--;
                    } else if (hits[h] === 1 && !weak[h]) {
                        weak[h] = pl;
                    }
                }
            }
        }
        for (var w in pending) {
            if (pending.hasOwnProperty(w) && pending[w] && weak[w]) {
                found[w] = { plugin: weak[w], how: "isi-file-lemah" };
            }
        }
        return budget <= 0;
    }

    function guessByFileName(plugins, ef) {
        var keys = [], best = null, bestScore = 0, i, j;

        function addKey(s) {
            var k = normKey(str(s).replace(/\s+\d+$/, ""));
            if (k.length >= 4) { keys.push(k); }
        }

        addKey(ef.displayName);
        addKey(ef.matchName);
        for (i = 0; i < ef.names.length; i++) { addKey(ef.names[i]); }
        for (i = 0; i < plugins.length; i++) {
            var b = normKey(stripExt(plugins[i].parts[plugins[i].parts.length - 1]));
            if (b.length < 4) { continue; }
            for (j = 0; j < keys.length; j++) {
                var k = keys[j], shorter = Math.min(b.length, k.length), longer = Math.max(b.length, k.length);
                var sc = 0;
                if (b === k) {
                    sc = 3;
                } else if (shorter >= 5 && shorter / longer >= 0.5 && (k.indexOf(b) !== -1 || b.indexOf(k) !== -1)) {
                    sc = 1;
                }
                if (sc > bestScore) {
                    best = plugins[i];
                    bestScore = sc;
                }
            }
        }
        return best ? { plugin: best, how: bestScore === 3 ? "nama-file" : "nama-file-mirip" } : null;
    }

    // ------------------------------------------------------- copy plugin
    // Yang dicopy HANYA file plugin (.aex / bundle .plugin) yang berisi efek
    // yang dipakai. Folder plugin / folder vendor tidak pernah dicopy utuh.
    // "File pendukung" (opsional) = file non-plugin di folder yang sama
    // (DLL, data) dan folder bernama sama; file plugin lain tidak pernah ikut.

    // Cara ketemu yang cukup pasti untuk langsung dicentang.
    var STRICT_HOW = { "pipl": 1, "pipl-nama": 1, "isi-file": 1 };
    var PLUGIN_BIN_EXT = { "aex": 1, "plugin": 1, "prm": 1, "8bf": 1, "8bi": 1, "8li": 1, "aip": 1, "bundle": 1 };

    function hasPluginBinary(folder, depth) {
        if (depth > 6) { return true; }
        var entries = null;
        try { entries = folder.getFiles(); } catch (e) { entries = null; }
        if (!entries) { return false; }
        for (var i = 0; i < entries.length; i++) {
            if (PLUGIN_BIN_EXT[getExt(dname(entries[i]))] === 1) { return true; }
            if (entries[i] instanceof Folder && hasPluginBinary(entries[i], depth + 1)) { return true; }
        }
        return false;
    }

    function supportItems(pl) {
        var out = [], parent = pl.target.parent;
        if (!parent) { return out; }
        var dirs = pl.parts.slice(0, pl.parts.length - 1);
        var vendorDir = dirs.length >= 1 && !isStructural(dirs[dirs.length - 1]);
        var base = stripExt(dname(pl.target)).toLowerCase(), self = pathKey(pl.target);
        var entries = null;
        try { entries = parent.getFiles(); } catch (e) { entries = null; }
        if (!entries) { return out; }
        for (var i = 0; i < entries.length; i++) {
            var en = entries[i], nm = dname(en);
            if (pathKey(en) === self || PLUGIN_BIN_EXT[getExt(nm)] === 1) { continue; }
            var sameBase = stripExt(nm).toLowerCase() === base;
            if (en instanceof File) {
                if (vendorDir || sameBase) { out.push(en); }
            } else if (en instanceof Folder && sameBase && !hasPluginBinary(en, 0)) {
                out.push(en);
            }
        }
        return out;
    }

    function candLabel(cd) {
        return cd.pl.root.label + "/" + cd.pl.parts.join("/");
    }

    function effectShortName(e) {
        return e.displayName || e.pluginName || e.names[0] || e.matchName;
    }

    function candEffectsText(cd) {
        var names = [];
        for (var i = 0; i < cd.effects.length; i++) { names.push(effectShortName(cd.effects[i])); }
        return names.join(", ") + (cd.others ? "  (+" + cd.others + " efek lain di file yang sama)" : "");
    }

    // Daftar file plugin yang akan dicopy; tiap baris bisa dicentang / tidak.
    // Mengembalikan array boolean sesuai urutan cands.
    function confirmPluginCopy(cands) {
        var dlg = new Window("dialog", SCRIPT_NAME + " - plugin yang akan dicopy");
        dlg.orientation = "column";
        dlg.alignChildren = "fill";
        dlg.add("statictext", undefined,
            "Hanya file plugin yang berisi efek yang kamu pakai. Klik dua kali (atau pilih lalu klik tombol) untuk centang / hapus centang.");
        var lb = dlg.add("listbox", undefined, undefined, {
            numberOfColumns: 3,
            showHeaders: true,
            multiselect: true,
            columnTitles: ["File plugin", "Efek yang dipakai", "Ukuran"],
            columnWidths: [330, 340, 80]
        });
        lb.preferredSize = [770, 320];
        var i;
        for (i = 0; i < cands.length; i++) {
            var cd = cands[i];
            var item = lb.add("item", (cd.strict ? "" : "(perkiraan) ") + candLabel(cd));
            item.subItems[0].text = candEffectsText(cd);
            item.subItems[1].text = formatBytes(cd.size);
            item.checked = cd.selected;
        }
        var total = dlg.add("statictext", undefined, "");
        total.preferredSize = [770, 20];

        function refresh() {
            var sum = 0, n = 0;
            for (var k = 0; k < lb.items.length; k++) {
                if (lb.items[k].checked) {
                    sum += cands[k].size;
                    n++;
                }
            }
            total.text = n + " dari " + lb.items.length + " file plugin dicentang, total " + formatBytes(sum);
        }

        function selectedItems() {
            var sel = lb.selection;
            if (!sel) { return []; }
            if (sel.length === undefined) { return [sel]; }
            return sel;
        }

        function setAll(v) {
            for (var k = 0; k < lb.items.length; k++) { lb.items[k].checked = v; }
            refresh();
        }

        function toggleSelected() {
            var sel = selectedItems();
            for (var k = 0; k < sel.length; k++) { sel[k].checked = !sel[k].checked; }
            refresh();
        }

        lb.onDoubleClick = toggleSelected;
        var row1 = dlg.add("group");
        var bToggle = row1.add("button", undefined, "Centang / hapus yang dipilih");
        var bAll = row1.add("button", undefined, "Centang semua");
        var bNone = row1.add("button", undefined, "Hapus semua centang");
        bToggle.onClick = toggleSelected;
        bAll.onClick = function () { setAll(true); };
        bNone.onClick = function () { setAll(false); };

        var row2 = dlg.add("group");
        row2.alignment = "right";
        var bSkip = row2.add("button", undefined, "Jangan copy plugin");
        var bOk = row2.add("button", undefined, "Copy yang dicentang");
        bSkip.onClick = function () { dlg.close(2); };
        bOk.onClick = function () { dlg.close(1); };
        dlg.defaultElement = bOk;
        dlg.cancelElement = bSkip;

        refresh();
        var r = dlg.show(), res = [];
        for (i = 0; i < cands.length; i++) { res.push(r === 1 && lb.items[i].checked === true); }
        return res;
    }

    function copyCandidate(cd, plugDir, copiedKeys) {
        var dirs = cd.pl.parts.slice(0, cd.pl.parts.length - 1);
        cd.destRel = cd.pl.root.label + (dirs.length ? "/" + dirs.join("/") : "");
        var dest = subFolder(plugDir, cd.destRel);
        var key = "#" + pathKey(cd.pl.target), ok = true;
        if (!copiedKeys[key]) {
            copiedKeys[key] = true;
            ok = cd.pl.isBundle ? copyFolder(cd.pl.target, dest) : (copyFile(cd.pl.target, dest, false) !== null);
        }
        for (var i = 0; i < cd.support.length; i++) {
            var s = cd.support[i], sk = "#" + pathKey(s);
            if (copiedKeys[sk]) { continue; }
            copiedKeys[sk] = true;
            if (s instanceof Folder) { copyFolder(s, dest); } else { copyFile(s, dest, false); }
        }
        cd.ok = ok;
        return ok;
    }

    // -------------------------------------------- animation preset (.ffx)

    function listFfx(folder, out, depth) {
        if (depth > 8 || out.length >= FFX_LIMIT || !folder.exists) { return; }
        var entries = null;
        try { entries = folder.getFiles(); } catch (e) { entries = null; }
        if (!entries) { return; }
        for (var i = 0; i < entries.length && out.length < FFX_LIMIT; i++) {
            if (entries[i] instanceof Folder) {
                listFfx(entries[i], out, depth + 1);
            } else if (entries[i] instanceof File && getExt(dname(entries[i])) === "ffx") {
                out.push(entries[i]);
            }
        }
    }

    function matchPresets(effects) {
        var keys = {}, any = false, i, n;
        for (i = 0; i < effects.length; i++) {
            var ef = effects[i], orig = ef.displayName || ef.pluginName;
            for (n = 0; n < ef.names.length; n++) {
                var inst = ef.names[n];
                if (ef.kind === "pseudo" || !orig || isRenamed(inst, orig)) {
                    var k = normKey(inst);
                    if (k.length >= 3) {
                        keys["#" + k] = inst;
                        any = true;
                    }
                }
            }
        }
        if (!any) { return []; }
        var files = [];
        try {
            var ap = isWin() ? Folder.appPackage : Folder.appPackage.parent;
            listFfx(new Folder(ap.absoluteURI + "/Presets"), files, 0);
        } catch (e) {}
        try {
            // Documents/Adobe/After Effects <versi>/User Presets, dll.
            var docs = new Folder(Folder.myDocuments.absoluteURI + "/Adobe");
            var subs = docs.exists ? (docs.getFiles() || []) : [];
            for (n = 0; n < subs.length; n++) {
                if (subs[n] instanceof Folder && /^after effects/i.test(dname(subs[n]))) { listFfx(subs[n], files, 0); }
            }
        } catch (e1) {}
        var out = [], seen = {};
        for (i = 0; i < files.length; i++) {
            var fk = "#" + normKey(stripExt(dname(files[i])));
            if (keys[fk] && !seen["#" + pathKey(files[i])]) {
                seen["#" + pathKey(files[i])] = true;
                out.push({ file: files[i], instance: keys[fk] });
            }
        }
        return out;
    }

    // ----------------------------------------------------- efek: laporan

    function usesText(ef, max) {
        var parts = [];
        for (var i = 0; i < ef.uses.length && i < max; i++) {
            parts.push(ef.uses[i].comp + " > " + ef.uses[i].layer);
        }
        if (ef.uses.length > max) { parts.push("... (+" + (ef.uses.length - max) + ")"); }
        return parts.join("; ");
    }

    function effectTitle(ef) {
        var nm = ef.displayName || ef.pluginName || ef.names[0] || ef.matchName;
        return nm + "  [match name: " + ef.matchName + "]" + (ef.version ? "  v" + ef.version : "");
    }

    function csvField(s) {
        return "\"" + str(s).replace(/[\t\r\n]+/g, " ").replace(/"/g, "\"\"") + "\"";
    }

    // CSV UTF-16LE + BOM + pemisah tab: Excel langsung membukanya per kolom
    // di setting regional apa pun (koma maupun titik koma), huruf non-ASCII aman.
    function writeCsv(file, rows) {
        var lines = [];
        for (var r = 0; r < rows.length; r++) {
            var cells = [];
            for (var c = 0; c < rows[r].length; c++) { cells.push(csvField(rows[r][c])); }
            lines.push(cells.join("\t"));
        }
        var text = lines.join("\r\n") + "\r\n", out = "\u00FF\u00FE";
        for (var i = 0; i < text.length; i++) {
            var code = text.charCodeAt(i);
            out += String.fromCharCode(code & 255, (code >>> 8) & 255);
        }
        try {
            file.encoding = "BINARY";
            if (!file.open("w")) { return false; }
            file.write(out);
            file.close();
            return true;
        } catch (e) {
            try { file.close(); } catch (e2) {}
            return false;
        }
    }

    var HOW_LABEL = {
        "pipl": "data PiPL",
        "pipl-nama": "data PiPL (nama efek sama dengan match name)",
        "pipl-mirip": "data PiPL (nama efek mirip, bukan persis)",
        "isi-file": "isi file (data PiPL tidak terbaca, plugin mungkin dikompres)",
        "isi-file-lemah": "teks di isi file (cocok lemah)",
        "nama-file": "nama file sama dengan nama efek",
        "nama-file-mirip": "nama file mirip nama efek"
    };

    var KIND_LABEL = {
        "plugin": "Plugin pihak ketiga",
        "builtin": "Bawaan After Effects",
        "pseudo": "Pseudo effect",
        "presetxml": "PresetEffects.xml"
    };

    var SCOPE_LABEL = {
        "selected": "comp yang dipilih",
        "rq": "comp di Render Queue",
        "all": "semua comp di project"
    };

    function scopeText(scope) {
        if (scope.mode === "all") { return SCOPE_LABEL.all + " (" + scope.comps.length + " comp)"; }
        var extra = scope.comps.length - scope.roots.length;
        return SCOPE_LABEL[scope.mode] + ": " + namesText(scope.roots, 8) +
            (extra > 0 ? "  (+" + extra + " precomp di dalamnya)" : "");
    }

    function collectPlugins(proj, destRoot, report, opt, csv, scope) {
        progress("Membaca efek di comp yang dipilih...");
        var gathered = gatherEffects(scope.comps, opt.skipDisabled);
        var effects = gathered.list;
        var installed = installedEffects();
        var xml = loadPresetEffectsXml();
        var st = {
            types: effects.length, uses: 0, plugin: 0, files: 0, copied: 0, notFound: 0, notInstalled: 0,
            unchecked: 0, builtin: 0, pseudo: 0, presetxml: 0, presets: 0, disabled: 0,
            budgetOut: false, previewError: ""
        };
        var i, ef, cd;

        function classify(e) {
            var inf = installed ? installed["#" + e.matchName] : null;
            e.displayName = inf ? inf.displayName : "";
            e.category = inf ? inf.category : "";
            e.version = inf ? inf.version : "";
            e.installed = installed ? !!inf : null;
            e.pluginName = "";
            e.found = null;
            e.cand = null;
            if (startsWith(e.matchName, "Pseudo/")) {
                e.kind = "pseudo";
            } else if (FIRST_PARTY["#" + e.matchName] === 1) {
                e.kind = "builtin";
            } else {
                e.kind = "plugin";
            }
            e.xmlBlock = (e.kind !== "builtin" && xml) ? findPresetEffectBlock(xml.text, e.matchName) : null;
            if (e.xmlBlock && e.kind === "plugin") { e.kind = "presetxml"; }
        }

        // --- 1. klasifikasi
        var usedSet = {};
        for (i = 0; i < effects.length; i++) {
            classify(effects[i]);
            st.uses += effects[i].count;
            usedSet["#" + effects[i].matchName] = true;
        }
        // efek yang semua pemakaiannya dimatikan: tidak dikumpulkan
        var offOnly = [];
        for (i = 0; i < gathered.disabled.length; i++) {
            classify(gathered.disabled[i]);
            st.disabled += gathered.disabled[i].count;
            if (!usedSet["#" + gathered.disabled[i].matchName]) { offOnly.push(gathered.disabled[i]); }
        }

        // --- 2. cari file plugin untuk efek pihak ketiga
        var wanted = [], needList = [];
        for (i = 0; i < effects.length; i++) {
            if (effects[i].kind === "plugin") {
                wanted.push(effects[i]);
                needList.push(effects[i].matchName);
            }
        }
        if (wanted.length) {
            var plugins = buildPluginList(wanted);
            var found = matchByPiPL(plugins, needList);
            // Pencarian cadangan (baca isi file penuh) hanya untuk efek yang
            // memang dimuat AE: efek yang tidak terinstall tidak perlu dicari lagi.
            var missing = [];
            for (i = 0; i < wanted.length; i++) {
                if (!found["#" + wanted[i].matchName] && wanted[i].installed !== false) {
                    missing.push(wanted[i].matchName);
                }
            }
            if (missing.length) { st.budgetOut = fallbackScan(plugins, missing, found); }
            for (i = 0; i < wanted.length; i++) {
                ef = wanted[i];
                ef.found = found["#" + ef.matchName] || null;
                if (!ef.found && ef.installed !== false) { ef.found = guessByFileName(plugins, ef); }
                if (ef.found && ef.found.effectName) { ef.pluginName = ef.found.effectName; }
                if (ef.found && !ef.category && ef.found.category) { ef.category = ef.found.category; }
            }
        }

        // --- 3. satu kandidat per FILE plugin (bukan per folder)
        var cands = [], candMap = {};
        for (i = 0; i < wanted.length; i++) {
            ef = wanted[i];
            if (!ef.found) { continue; }
            var pk = "#" + pathKey(ef.found.plugin.target);
            cd = candMap[pk];
            if (!cd) {
                cd = {
                    pl: ef.found.plugin, effects: [], strict: false, support: [], size: 0,
                    others: 0, selected: false, ok: false, destRel: ""
                };
                candMap[pk] = cd;
                cands.push(cd);
            }
            cd.effects.push(ef);
            ef.cand = cd;
            if (STRICT_HOW[ef.found.how] === 1) { cd.strict = true; }
        }
        for (i = 0; i < cands.length; i++) {
            cd = cands[i];
            cd.support = opt.support ? supportItems(cd.pl) : [];
            cd.size = measure(cd.pl.target);
            for (var s = 0; s < cd.support.length; s++) { cd.size += measure(cd.support[s]); }
            var ents = cd.pl.entries || [], otherSeen = {};
            for (var en = 0; en < ents.length; en++) {
                var mk = "#" + ents[en].mn;
                if (!usedSet[mk] && !otherSeen[mk]) {
                    otherSeen[mk] = true;
                    cd.others++;
                }
            }
            cd.selected = cd.strict;   // perkiraan tidak dicentang otomatis
        }
        st.files = cands.length;

        // --- 4. konfirmasi daftar plugin
        if (cands.length && opt.preview) {
            progressClose();
            var picks = null;
            try {
                picks = confirmPluginCopy(cands);
            } catch (eDlg) {
                picks = null;
                st.previewError = eDlg.toString();
            }
            if (picks) {
                for (i = 0; i < cands.length; i++) { cands[i].selected = picks[i]; }
            }
        }

        // --- 5. copy file plugin yang dicentang
        var plugDir = null, copiedKeys = {};
        for (i = 0; i < cands.length; i++) {
            cd = cands[i];
            if (!cd.selected) {
                st.unchecked++;
                continue;
            }
            if (!plugDir) { plugDir = subFolder(destRoot, "(Plugins)"); }
            progress("Copy plugin: " + candLabel(cd));
            if (copyCandidate(cd, plugDir, copiedKeys)) { st.copied++; }
        }

        // --- 6. PresetEffects.xml
        var blocks = [];
        for (i = 0; i < effects.length; i++) {
            if (effects[i].xmlBlock) { blocks.push(effects[i].xmlBlock); }
        }
        if (blocks.length) {
            var xdir = subFolder(destRoot, "(PresetEffects)");
            writeText(childFile(xdir, "PresetEffects_dari_project.xml"), [
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
                "<!-- " + SCRIPT_NAME + ": definisi efek dari PresetEffects.xml yang dipakai project ini.",
                "     Asal: " + xml.file.fsName,
                "     Efek dengan match name berawalan \"Pseudo/\" sudah tersimpan di dalam project,",
                "     jadi biasanya tidak perlu dipasang. Efek lainnya: salin blok <Effect> di bawah",
                "     ke PresetEffects.xml di komputer tujuan (sebelum tag </Effects> terakhir),",
                "     lalu restart After Effects. -->",
                "<Effects>",
                blocks.join("\n\n"),
                "</Effects>",
                ""
            ].join("\n"), false);
        }

        // --- 7. animation preset (.ffx) yang namanya cocok
        var presets = [];
        if (opt.presets) {
            progress("Mencari animation preset (.ffx) yang cocok...");
            presets = matchPresets(effects);
            if (presets.length) {
                var pdir = subFolder(destRoot, "(Presets)");
                for (i = 0; i < presets.length; i++) {
                    presets[i].ok = copyFile(presets[i].file, pdir, true) !== null;
                    if (presets[i].ok) { st.presets++; }
                }
            }
        }

        // --- 8. laporan
        function statusOf(e) {
            if (e.kind === "builtin") { return { tag: "", csv: "bawaan AE" }; }
            if (e.kind === "pseudo") { return { tag: "", csv: "tersimpan di project" }; }
            if (e.kind === "presetxml") { return { tag: "", csv: "definisi XML diekspor" }; }
            if (e.cand) {
                if (e.cand.selected) {
                    if (!e.cand.ok) { return { tag: "[GAGAL COPY]", csv: "gagal copy" }; }
                    return (e.found.how === "pipl" || e.found.how === "pipl-nama") ?
                        { tag: "[OK]", csv: "dicopy" } :
                        { tag: "[OK, CEK MANUAL]", csv: "dicopy (cek manual)" };
                }
                return e.cand.strict ?
                    { tag: "[TIDAK DICOPY]", csv: "tidak dicopy (centang dihapus)" } :
                    { tag: "[PERKIRAAN, TIDAK DICOPY]", csv: "perkiraan, tidak dicopy" };
            }
            if (e.installed === false) { return { tag: "[TIDAK TERINSTALL]", csv: "tidak terinstall" }; }
            return { tag: "[TIDAK KETEMU]", csv: "file tidak ketemu" };
        }

        var groups = { plugin: [], presetxml: [], pseudo: [], builtin: [] };
        for (i = 0; i < effects.length; i++) { groups[effects[i].kind].push(effects[i]); }
        st.plugin = groups.plugin.length;
        st.builtin = groups.builtin.length;
        st.pseudo = groups.pseudo.length;
        st.presetxml = groups.presetxml.length;

        report.push("=== EFEK & PLUGIN ===");
        report.push("Comp yang dibaca : " + scopeText(scope));
        report.push("Terbaca          : " + st.uses + " pemakaian efek, " + st.types + " jenis efek" +
            (st.disabled ? "  (" + st.disabled + " pemakaian efek yang dimatikan dilewati)" : "") + ".");
        report.push("Efek plugin pihak ketiga: " + st.plugin + "  |  Bawaan AE: " + st.builtin +
            "  |  Pseudo effect: " + st.pseudo + "  |  PresetEffects.xml: " + st.presetxml);
        if (!installed) { report.push("(Catatan: daftar efek terinstall dari app.effects tidak tersedia di versi AE ini.)"); }
        if (st.previewError) { report.push("(Daftar konfirmasi plugin tidak bisa ditampilkan: " + st.previewError + ")"); }
        report.push("Yang dicopy hanya FILE plugin yang berisi efek di atas, bukan seluruh folder plugin.");
        report.push("Daftar lengkap per comp & layer ada di file *_daftar_efek.csv.");
        report.push("");

        report.push("--- PLUGIN PIHAK KETIGA ---");
        if (!groups.plugin.length) { report.push("Tidak ada."); }
        for (i = 0; i < groups.plugin.length; i++) {
            ef = groups.plugin[i];
            var stt = statusOf(ef);
            if (stt.tag === "[TIDAK TERINSTALL]") { st.notInstalled++; }
            if (stt.tag === "[TIDAK KETEMU]") { st.notFound++; }
            report.push(stt.tag + " " + effectTitle(ef));
            if (ef.category) { report.push("     kategori      : " + ef.category); }
            report.push("     nama di layer : " + ef.names.join(", "));
            report.push("     dipakai " + ef.count + "x    : " + usesText(ef, 6));
            if (ef.found) {
                report.push("     file plugin   : " + ef.found.plugin.target.fsName);
                if (ef.found.how !== "pipl") {
                    report.push("     cara ketemu   : " + HOW_LABEL[ef.found.how] + " -> pastikan file ini memang plugin-nya");
                }
                if (ef.cand && ef.cand.selected && ef.cand.ok) {
                    report.push("     dicopy ke     : (Plugins)/" + ef.cand.destRel);
                } else if (ef.cand && !ef.cand.selected) {
                    report.push("     catatan       : " + (ef.cand.strict ?
                        "tidak dicopy karena centangnya kamu hapus" :
                        "tidak dicopy otomatis karena hanya perkiraan; centang di daftar kalau memang benar"));
                }
                if (ef.found.plugin.root.isApp) {
                    report.push("     catatan       : file ini ada di folder plugin After Effects sendiri");
                }
                if (ef.installed === false) {
                    report.push("     catatan       : efek ini tidak dimuat oleh After Effects yang sedang dipakai");
                }
            } else if (ef.installed === false) {
                report.push("     catatan       : plugin ini tidak ada di komputer ini (project dibuat di komputer lain?)");
            } else {
                report.push("     catatan       : terinstall, tapi file-nya tidak ketemu. Cari file .aex/.plugin-nya manual.");
            }
        }
        if (st.budgetOut) {
            report.push("(Pencarian cadangan dihentikan setelah membaca " + formatBytes(FALLBACK_BUDGET) + ".)");
        }
        report.push("");

        report.push("--- FILE PLUGIN YANG DICOPY ---");
        var anyCopied = false;
        for (i = 0; i < cands.length; i++) {
            cd = cands[i];
            if (!cd.selected) { continue; }
            anyCopied = true;
            report.push((cd.ok ? "- " : "- [GAGAL] ") + candLabel(cd) + "  (" + formatBytes(cd.size) + ")");
            var used = [];
            for (var u = 0; u < cd.effects.length; u++) { used.push(effectShortName(cd.effects[u])); }
            report.push("     efek dipakai  : " + used.join(", "));
            if (cd.others) {
                report.push("     catatan       : file ini juga berisi " + cd.others +
                    " efek lain yang tidak dipakai (satu file, tidak bisa dipisah)");
            }
            if (cd.support.length) { report.push("     file pendukung: " + cd.support.length + " file/folder ikut dicopy"); }
        }
        if (!anyCopied) { report.push("Tidak ada."); }
        report.push("");

        if (groups.presetxml.length) {
            report.push("--- EFEK DARI PresetEffects.xml ---");
            for (i = 0; i < groups.presetxml.length; i++) {
                ef = groups.presetxml[i];
                report.push("[XML] " + effectTitle(ef));
                report.push("     nama di layer : " + ef.names.join(", "));
                report.push("     dipakai " + ef.count + "x    : " + usesText(ef, 6));
            }
            report.push("Definisinya diekspor ke (PresetEffects)/PresetEffects_dari_project.xml.");
            report.push("");
        }

        if (groups.pseudo.length) {
            report.push("--- PSEUDO EFFECT (sudah tersimpan di dalam project, tidak perlu dicopy) ---");
            for (i = 0; i < groups.pseudo.length; i++) {
                ef = groups.pseudo[i];
                report.push("[PSEUDO] " + effectTitle(ef) + (ef.xmlBlock ? "  (definisi ikut diekspor)" : ""));
                report.push("     nama di layer : " + ef.names.join(", "));
                report.push("     dipakai " + ef.count + "x    : " + usesText(ef, 6));
            }
            report.push("");
        }

        report.push("--- EFEK BAWAAN AFTER EFFECTS (tidak perlu dicopy) ---");
        if (!groups.builtin.length) { report.push("Tidak ada."); }
        for (i = 0; i < groups.builtin.length; i++) {
            ef = groups.builtin[i];
            report.push("- " + effectTitle(ef) + "  " + ef.count + "x  | nama di layer: " + ef.names.join(", "));
        }
        report.push("");

        if (offOnly.length) {
            report.push("--- EFEK YANG DIMATIKAN (ikon fx mati, tidak dikumpulkan) ---");
            for (i = 0; i < offOnly.length; i++) {
                ef = offOnly[i];
                report.push("[DIMATIKAN] " + effectTitle(ef) + "  (" + KIND_LABEL[ef.kind] + ")");
                report.push("     nama di layer : " + ef.names.join(", "));
                report.push("     di            : " + usesText(ef, 6));
            }
            report.push("Kalau plugin efek ini tidak ada di komputer tujuan, AE tetap memberi peringatan");
            report.push("\"missing\" saat project dibuka, tapi hasil render tidak berubah.");
            report.push("");
        }

        if (opt.presets) {
            report.push("--- ANIMATION PRESET (.ffx) YANG NAMANYA COCOK ---");
            if (!presets.length) { report.push("Tidak ada preset yang namanya cocok dengan efek yang di-rename."); }
            for (i = 0; i < presets.length; i++) {
                report.push((presets[i].ok ? "[OK] " : "[GAGAL] ") + presets[i].file.fsName +
                    "  (cocok dengan efek \"" + presets[i].instance + "\")");
            }
            report.push("");
        }

        report.push("Total: " + st.plugin + " efek plugin pihak ketiga dipakai -> " + st.copied + " file plugin dicopy" +
            (st.unchecked ? ", " + st.unchecked + " tidak dicentang" : "") + ", " + st.notFound + " tidak ketemu, " +
            st.notInstalled + " tidak terinstall.");
        report.push("");

        // --- 9. CSV semua pemakaian efek
        csv.push(["Comp", "Layer", "Nama efek di layer", "Nama efek asli", "Match name", "Jenis",
            "Status", "File plugin", "Efek aktif"]);
        var u2;
        for (i = 0; i < effects.length; i++) {
            ef = effects[i];
            var sc = statusOf(ef).csv;
            for (u2 = 0; u2 < ef.uses.length; u2++) {
                csv.push([ef.uses[u2].comp, ef.uses[u2].layer, ef.uses[u2].instance,
                    ef.displayName || ef.pluginName, ef.matchName, KIND_LABEL[ef.kind], sc,
                    ef.found ? ef.found.plugin.target.fsName : "", ef.uses[u2].enabled ? "ya" : "tidak"]);
            }
        }
        for (i = 0; i < gathered.disabled.length; i++) {
            ef = gathered.disabled[i];
            for (u2 = 0; u2 < ef.uses.length; u2++) {
                csv.push([ef.uses[u2].comp, ef.uses[u2].layer, ef.uses[u2].instance,
                    ef.displayName, ef.matchName, KIND_LABEL[ef.kind], "dimatikan, tidak dikumpulkan", "", "tidak"]);
            }
        }
        return st;
    }

    // ================================================================= UI

    var SCOPE_MODES = ["selected", "rq", "all"];

    function showOptions(defaultPath, scopeInfo) {
        var dlg = new Window("dialog", SCRIPT_NAME);
        dlg.orientation = "column";
        dlg.alignChildren = "fill";

        var pDest = dlg.add("panel", undefined, "Folder tujuan");
        pDest.orientation = "row";
        pDest.alignChildren = ["fill", "center"];
        pDest.margins = 14;
        var etPath = pDest.add("edittext", undefined, defaultPath);
        etPath.preferredSize.width = 470;
        var btnBrowse = pDest.add("button", undefined, "Browse...");
        btnBrowse.onClick = function () {
            var f = pickFolder("Pilih folder tujuan untuk hasil collect", trim(etPath.text));
            if (f) { etPath.text = f.fsName; }
        };

        var pScope = dlg.add("panel", undefined, "Efek, plugin & font dibaca dari");
        pScope.orientation = "column";
        pScope.alignChildren = "fill";
        pScope.margins = 14;
        var ddScope = pScope.add("dropdownlist", undefined, [
            (scopeInfo.selectedIsActive ? "Comp yang sedang aktif" : "Comp yang dipilih di panel Project") +
                " + precomp di dalamnya (" + scopeInfo.selected.length + " comp)",
            "Comp di Render Queue + precomp di dalamnya (" + scopeInfo.rq.length + " comp)",
            "Semua comp di project (" + scopeInfo.all.length + " comp, termasuk yang tidak dipakai)"
        ]);
        var stScope = pScope.add("statictext", undefined, "", { multiline: true });
        stScope.preferredSize = [560, 32];
        var cbSkipOff = pScope.add("checkbox", undefined, "Lewati efek yang dimatikan (ikon fx mati)");

        var pnl = dlg.add("panel", undefined, "Yang dikumpulkan");
        pnl.orientation = "column";
        pnl.alignChildren = "left";
        pnl.margins = 14;
        var cbFoot = pnl.add("checkbox", undefined, "Footage + relink, simpan project baru (proxy, sequence, PSD/AI berlayer)");
        var grpRed = pnl.add("group");
        grpRed.margins = [22, 0, 0, 0];
        var cbReduce = grpRed.add("checkbox", undefined, "Buang comp & footage yang tidak dipakai dari project hasil (Reduce Project)");
        var cbFont = pnl.add("checkbox", undefined, "Font yang dipakai");
        var cbPlug = pnl.add("checkbox", undefined, "Plugin pihak ketiga (hanya file plugin yang efeknya dipakai)");
        var grpPrev = pnl.add("group");
        grpPrev.margins = [22, 0, 0, 0];
        var cbPreview = grpPrev.add("checkbox", undefined, "Tampilkan daftar plugin dulu sebelum dicopy (bisa hapus centang)");
        var grpSup = pnl.add("group");
        grpSup.margins = [22, 0, 0, 0];
        var cbSupport = grpSup.add("checkbox", undefined, "Ikut file pendukung (DLL/data di folder yang sama, tanpa plugin lain)");
        var grpPre = pnl.add("group");
        grpPre.margins = [22, 0, 0, 0];
        var cbPresets = grpPre.add("checkbox", undefined, "Ikut copy animation preset (.ffx) yang namanya sama dengan efek yang di-rename");

        var pnl2 = dlg.add("panel", undefined, "Setelah selesai");
        pnl2.alignChildren = "left";
        pnl2.margins = 14;
        var cbReopen = pnl2.add("checkbox", undefined, "Buka lagi project asli (bukan salinan hasil collect)");

        cbFoot.value = getSetting("footage", "1") === "1";
        cbFont.value = getSetting("fonts", "1") === "1";
        cbPlug.value = getSetting("plugins", "1") === "1";
        cbSkipOff.value = getSetting("skipOff4", "1") === "1";
        cbPreview.value = getSetting("preview4", "1") === "1";
        cbSupport.value = getSetting("support4", "0") === "1";
        cbPresets.value = getSetting("presets4", "0") === "1";
        cbReduce.value = getSetting("reduce4", "0") === "1";
        cbReopen.value = getSetting("reopen", "0") === "1";

        var defIndex = 2;
        if (scopeInfo.selected.length && !scopeInfo.selectedIsActive) {
            defIndex = 0;
        } else if (scopeInfo.rq.length) {
            defIndex = 1;
        } else if (scopeInfo.selected.length) {
            defIndex = 0;
        }
        ddScope.selection = defIndex;

        function currentMode() {
            return SCOPE_MODES[ddScope.selection ? ddScope.selection.index : 2];
        }

        function sync() {
            var m = currentMode(), roots = scopeInfo[m];
            if (m === "all") {
                stScope.text = "Semua comp ikut dibaca, termasuk comp yang tidak dipakai.";
            } else if (!roots.length) {
                stScope.text = (m === "selected") ?
                    "Belum ada comp yang dipilih. Pilih comp utama di panel Project, lalu jalankan script lagi." :
                    "Render Queue kosong.";
            } else {
                stScope.text = "Comp: " + namesText(roots, 6);
            }
            cbPreview.enabled = cbPlug.value;
            cbSupport.enabled = cbPlug.value;
            cbPresets.enabled = cbPlug.value;
            cbReopen.enabled = cbFoot.value;
            cbReduce.enabled = cbFoot.value && m !== "all";
        }
        ddScope.onChange = sync;
        cbPlug.onClick = sync;
        cbFoot.onClick = sync;
        sync();

        var btns = dlg.add("group");
        btns.alignment = "right";
        var btnCancel = btns.add("button", undefined, "Batal");
        var btnOk = btns.add("button", undefined, "Mulai");
        dlg.defaultElement = btnOk;
        dlg.cancelElement = btnCancel;
        btnCancel.onClick = function () { dlg.close(0); };
        btnOk.onClick = function () {
            var p = trim(etPath.text);
            if (!p) {
                alert("Pilih folder tujuan dulu.", SCRIPT_NAME);
                return;
            }
            var m = currentMode();
            if (m !== "all" && !scopeInfo[m].length) {
                alert((m === "selected" ?
                    "Belum ada comp yang dipilih di panel Project." :
                    "Render Queue kosong.") + "\nPilih opsi lain di \"Efek, plugin & font dibaca dari\".", SCRIPT_NAME);
                return;
            }
            var f = new Folder(p);
            if (!f.exists) {
                if (!confirm("Folder belum ada:\n" + p + "\n\nBuat folder ini?", false, SCRIPT_NAME)) { return; }
                if (!makeFolder(f) || !f.exists) {
                    alert("Folder tidak bisa dibuat:\n" + p, SCRIPT_NAME);
                    return;
                }
            }
            if (!cbFoot.value && !cbFont.value && !cbPlug.value) {
                alert("Pilih minimal satu yang dikumpulkan.", SCRIPT_NAME);
                return;
            }
            dlg.close(1);
        };

        if (dlg.show() !== 1) { return null; }

        var mode = currentMode();
        var opt = {
            dest: new Folder(trim(etPath.text)),
            scope: mode,
            skipDisabled: cbSkipOff.value,
            footage: cbFoot.value,
            reduce: cbFoot.value && mode !== "all" && cbReduce.value,
            fonts: cbFont.value,
            plugins: cbPlug.value,
            preview: cbPlug.value && cbPreview.value,
            support: cbPlug.value && cbSupport.value,
            presets: cbPlug.value && cbPresets.value,
            reopen: cbFoot.value && cbReopen.value
        };
        saveSetting("lastFolder", opt.dest.fsName);
        saveSetting("footage", opt.footage ? "1" : "0");
        saveSetting("fonts", opt.fonts ? "1" : "0");
        saveSetting("plugins", opt.plugins ? "1" : "0");
        saveSetting("skipOff4", cbSkipOff.value ? "1" : "0");
        saveSetting("preview4", cbPreview.value ? "1" : "0");
        saveSetting("support4", cbSupport.value ? "1" : "0");
        saveSetting("presets4", cbPresets.value ? "1" : "0");
        saveSetting("reduce4", cbReduce.value ? "1" : "0");
        saveSetting("reopen", cbReopen.value ? "1" : "0");
        return opt;
    }

    function howToUse() {
        return [
            "=== CARA PAKAI DI KOMPUTER LAIN ===",
            "1. Font: install semua file di (Fonts) sebelum membuka project.",
            "   Windows: pilih semua > klik kanan > Install for all users.  Mac: buka dengan Font Book.",
            "   Font [ADOBE FONTS] cukup diaktifkan dari aplikasi Creative Cloud.",
            "2. Plugin: tutup After Effects dulu, lalu copy isi:",
            "   (Plugins)/MediaCore    ->  Windows: C:\\Program Files\\Adobe\\Common\\Plug-ins\\7.0\\MediaCore",
            "                              Mac: /Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore",
            "   (Plugins)/AE Plug-ins  ->  Windows: C:\\Program Files\\Adobe\\Adobe After Effects <versi>\\Support Files\\Plug-ins",
            "                              Mac: /Applications/Adobe After Effects <versi>/Plug-ins",
            "   (Plugins)/Lainnya      ->  lokasi aslinya tercatat di laporan (baris \"file plugin\").",
            "   Lewati plugin yang sudah terinstall supaya tidak dobel.",
            "   .aex hanya jalan di Windows, .plugin hanya jalan di Mac.",
            "   Yang dicopy hanya file plugin dari efek yang dipakai. Plugin besar/berbayar",
            "   (Boris FX, Red Giant/Maxon, Video Copilot, dll.) tetap butuh installer + lisensi",
            "   resmi di komputer tujuan; file .aex-nya saja biasanya tidak cukup.",
            "3. (PresetEffects): ikuti petunjuk di dalam file XML-nya.",
            "4. (Presets): copy file .ffx ke Documents\\Adobe\\After Effects <versi>\\User Presets.",
            "5. Buka file project di folder ini.",
            "   Item [RELINK MANUAL]: klik kanan > Replace Footage > File..., pilih file yang sama",
            "   di folder (Footage), lalu pilih layer yang sesuai.",
            ""
        ];
    }

    // =============================================================== main

    var stage = "awal";

    function main() {
        var proj = app.project;

        if (!proj || !proj.file) {
            alert("Simpan project dulu sebelum menjalankan script ini.", SCRIPT_NAME);
            return;
        }
        if (!canWriteFiles()) {
            alert("Aktifkan dulu:\nPreferences > Scripting & Expressions >\n" +
                "\"Allow Scripts to Write Files and Access Network\"", SCRIPT_NAME);
            openScriptingPrefs();
            return;
        }

        // Ambil pilihan comp sebelum ada dialog apa pun.
        var scopeInfo = {
            selected: scopeRoots(proj, "selected"),
            selectedIsActive: false,
            rq: scopeRoots(proj, "rq"),
            all: scopeRoots(proj, "all")
        };
        if (!scopeInfo.selected.length) {
            var act = null;
            try { act = proj.activeItem; } catch (eAct) { act = null; }
            if (act instanceof CompItem) {
                scopeInfo.selected = [act];
                scopeInfo.selectedIsActive = true;
            }
        }

        if (proj.dirty) {
            if (!confirm("Project punya perubahan yang belum disimpan.\nSimpan sekarang lalu lanjut?", false, SCRIPT_NAME)) {
                return;
            }
            proj.save();
        }

        var originalFile = proj.file;
        var defaultPath = getSetting("lastFolder", "");
        if (!defaultPath || !(new Folder(defaultPath)).exists) { defaultPath = originalFile.parent.fsName; }

        var opt = showOptions(defaultPath, scopeInfo);
        if (!opt) { return; }
        var scope = makeScope(proj, opt.scope, scopeInfo[opt.scope]);

        var projFileName = dname(originalFile);
        var projName = stripExt(projFileName);
        var projExt = getExt(projFileName) || "aep";
        var destRoot = subFolder(opt.dest, projName + "_Collected");

        var report = [], csv = [];
        report.push(SCRIPT_NAME + " - laporan");
        report.push("Project asal : " + originalFile.fsName);
        report.push("Folder hasil : " + destRoot.fsName);
        report.push("Comp dibaca  : " + scopeText(scope));
        report.push("Tanggal      : " + (new Date()).toString());
        report.push("After Effects: " + app.version + "  |  OS: " + $.os);
        report.push("");

        var rFoot = null, rFont = null, rPlug = null, removed = -1;

        // Font & efek hanya membaca project, jadi dikerjakan duluan.
        if (opt.fonts) {
            stage = "font";
            rFont = collectFonts(proj, destRoot, report, scope);
        }
        if (opt.plugins) {
            stage = "plugin";
            rPlug = collectPlugins(proj, destRoot, report, opt, csv, scope);
        }

        if (opt.footage) {
            // Simpan salinan DULU, supaya semua perubahan hanya terjadi di salinan.
            progress("Menyimpan salinan project...");
            proj.save(childFile(destRoot, projName + "." + projExt));
            stage = "footage";
            if (opt.reduce && scope.roots.length) {
                progress("Reduce Project...");
                report.push("=== REDUCE PROJECT ===");
                try {
                    removed = proj.reduceProject(scope.roots);
                    report.push(removed + " item yang tidak dipakai " + SCOPE_LABEL[scope.mode] +
                        " dibuang dari project hasil (project asli tidak berubah).");
                } catch (eRed) {
                    report.push("[GAGAL] " + eRed.toString());
                }
                report.push("");
            }
            rFoot = collectFootage(proj, destRoot, report);
            progress("Menyimpan project hasil collect...");
            proj.save();
        } else {
            copyFile(originalFile, destRoot, false);
        }

        var rep = childFile(destRoot, projName + "_report.txt");
        writeText(rep, report.concat(howToUse()).join("\n"), false);

        var csvFile = null;
        if (csv.length > 1) {
            csvFile = childFile(destRoot, projName + "_daftar_efek.csv");
            if (!writeCsv(csvFile, csv)) { csvFile = null; }
        }

        progressClose();

        var msg = "Selesai.\n\nComp dibaca: " + scopeText(scope) + "\n\n";
        if (rFoot) {
            msg += "Footage: " + rFoot.copied + " tercopy, " + rFoot.proxies + " proxy, " +
                rFoot.missing + " hilang, " + rFoot.failed + " gagal, " + rFoot.manual + " relink manual\n";
            if (removed >= 0) { msg += "Reduce Project: " + removed + " item tidak dipakai dibuang\n"; }
        }
        if (rFont) {
            msg += "Font: " + rFont.copied + " dari " + rFont.total + " tercopy\n";
        }
        if (rPlug) {
            msg += "Efek: " + rPlug.uses + " pemakaian, " + rPlug.types + " jenis (" + rPlug.builtin + " bawaan AE, " +
                rPlug.pseudo + " pseudo)" + (rPlug.disabled ? ", " + rPlug.disabled + " dimatikan dilewati" : "") + "\n";
            msg += "Plugin pihak ketiga: " + rPlug.plugin + " efek -> " + rPlug.copied + " file plugin dicopy" +
                (rPlug.unchecked ? ", " + rPlug.unchecked + " tidak dicentang" : "") + ", " +
                rPlug.notFound + " tidak ketemu, " + rPlug.notInstalled + " tidak terinstall\n";
            if (rPlug.presets) { msg += "Animation preset: " + rPlug.presets + " tercopy\n"; }
        }
        msg += "\nDetail & cara pakai ada di " + dname(rep) + ".";
        if (csvFile) { msg += "\nDaftar semua efek: " + dname(csvFile) + "."; }
        if (opt.footage && !opt.reopen) {
            msg += "\n\nProject yang terbuka sekarang adalah SALINAN hasil collect.";
        }
        alert(msg, SCRIPT_NAME);

        if (opt.reopen) {
            try { app.open(originalFile); } catch (e) {}
        }
        try { destRoot.execute(); } catch (e2) {}
    }

    try {
        main();
    } catch (err) {
        progressClose();
        alert("Error: " + err.toString() + (err.line ? "\nBaris: " + err.line : "") +
            (stage === "footage" ? "\n\nProject asli aman. Yang terbuka sekarang adalah salinan di folder hasil." : ""),
            SCRIPT_NAME);
    }

})();
