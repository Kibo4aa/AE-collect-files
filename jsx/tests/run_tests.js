"use strict";
const assert = require("assert");
const H = require("./harness.js");
const { putFile, Folder, File, CompItem, FSDATA, mkdirs, normPath } = H;

const le16 = v => String.fromCharCode(v & 255, (v >>> 8) & 255);
const le32 = v => String.fromCharCode(v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255);
const be32 = v => String.fromCharCode((v >>> 24) & 255, (v >>> 16) & 255, (v >>> 8) & 255, v & 255);
const pad4 = x => (x % 4 ? 4 - (x % 4) : 0);
const align = (x, a) => Math.ceil(x / a) * a;

// Port dari pipl::build_pipl (crate after-effects): format byte PiPL asli.
function pipl(props, win) {
    const u32 = v => (win ? le32(v) : be32(v));
    const cc = s => (win ? s.split("").reverse().join("") : s);
    let buf = win ? "\x01\x00" : "";
    buf += u32(0) + u32(props.length);
    for (const p of props) {
        buf += cc("8BIM") + cc(p.key) + u32(0);
        let data;
        if (p.pstr !== undefined) {
            data = String.fromCharCode(p.pstr.length) + p.pstr;
            if (win) data += "\0".repeat(pad4(p.pstr.length + 1));
        } else {
            data = p.raw;
        }
        buf += u32(data.length) + data;
        if (!win) buf += "\0".repeat(pad4(data.length));
    }
    return buf;
}
function effectPiPL(name, cat, mn, win) {
    return pipl([
        { key: "kind", raw: win ? "TKFe" : "eFKT" },
        { key: "name", pstr: name },
        { key: "catg", pstr: cat },
        { key: "eVER", raw: win ? le32(0x80001) : be32(0x80001) },
        { key: "eMNA", pstr: mn }
    ], win);
}
function sect(name, vsize, va, rawSize, rawPtr) {
    return (name + "\0\0\0\0\0\0\0\0").slice(0, 8) + le32(vsize) + le32(va) + le32(rawSize) + le32(rawPtr) + "\0".repeat(16);
}
function makePE(rsrc, text, plus) {
    let h = "MZ" + "\0".repeat(0x3a) + le32(0x80) + "\0".repeat(0x40);
    h += "PE\0\0";
    const optSize = plus ? 0xf0 : 0xe0;
    h += le16(plus ? 0x8664 : 0x14c) + le16(2) + le32(0) + le32(0) + le32(0) + le16(optSize) + le16(0x2022);
    const ddStart = plus ? 112 : 96;
    let opt = le16(plus ? 0x20b : 0x10b);
    opt += "\0".repeat(ddStart - 4 - opt.length) + le32(16);
    for (let i = 0; i < 16; i++) opt += i === 2 ? le32(0x3000) + le32(rsrc.length) : le32(0) + le32(0);
    assert.strictEqual(opt.length, optSize);
    h += opt;
    const textRaw = 0x400, textSize = align(Math.max(text.length, 1), 0x200);
    const rsrcRaw = textRaw + textSize, rsrcSize = align(Math.max(rsrc.length, 1), 0x200);
    h += sect(".text", text.length, 0x1000, textSize, textRaw);
    h += sect(".rsrc", rsrc.length, 0x3000, rsrcSize, rsrcRaw);
    h += "\0".repeat(textRaw - h.length);
    h += text + "\0".repeat(textSize - text.length);
    h += rsrc + "\0".repeat(rsrcSize - rsrc.length);
    return h;
}
const RSRC_HEAD = "\0\0\0\0junk-resource-directory\x10\x00PiPL\x00\x00";

let passed = 0;
function test(name, fn) {
    try { fn(); passed++; console.log("ok   - " + name); }
    catch (e) { console.log("FAIL - " + name + "\n       " + (e && e.stack ? e.stack.split("\n").slice(0, 3).join("\n       ") : e)); process.exitCode = 1; }
}

H.setOS("Windows 10");
const api = H.loadScript();

// -------------------------------------------------------------- unit tests
test("FIRST_PARTY berisi efek bawaan termasuk CC & non-ADBE", () => {
    for (const n of ["ADBE Gaussian Blur 2", "CC Light Sweep", "ADBE Slider Control", "Keylight 906", "APC Colorama", "CS Vignette", "VISINF Grain Implant"]) {
        assert.strictEqual(api.FIRST_PARTY["#" + n], 1, n);
    }
    for (const n of ["ADBE Hobby Glow", "a_paya", "VNDA A_kaca", "PEDG"]) assert.notStrictEqual(api.FIRST_PARTY["#" + n], 1, n);
});

test("PiPL Windows & Mac terbaca lengkap (name, category, match name)", () => {
    for (const win of [true, false]) {
        const data = "xx" + effectPiPL("A_kaca", "Vendor A", "VNDA A_kaca", win) + effectPiPL("a_paya", "Vendor A", "a_paya", win) + "yy";
        putFile("/t/p" + win + ".bin", data);
        const st = { entries: [], curName: "", curCat: "" };
        api.scanPiPLRange(new File("/t/p" + win + ".bin"), 0, data.length, st);
        assert.deepStrictEqual(st.entries, [
            { mn: "VNDA A_kaca", name: "A_kaca", cat: "Vendor A" },
            { mn: "a_paya", name: "a_paya", cat: "Vendor A" }
        ], "win=" + win);
    }
});

test("PiPL di batas potongan baca 4 MB tetap terbaca", () => {
    const CH = 4 * 1024 * 1024;
    for (const off of [CH - 700, CH - 601, CH - 600, CH - 599, CH - 300, CH - 17, CH - 8, CH - 3, CH, CH + 5]) {
        const pl = effectPiPL("Edge FX", "Cat", "EDGE Fx " + off, true);
        const data = "\0".repeat(off) + pl + "\0".repeat(64);
        putFile("/t/edge.bin", data);
        const st = { entries: [], curName: "", curCat: "" };
        api.scanPiPLRange(new File("/t/edge.bin"), 0, data.length, st);
        assert.strictEqual(st.entries.length, 1, "off=" + off);
        assert.strictEqual(st.entries[0].mn, "EDGE Fx " + off);
        assert.strictEqual(st.entries[0].name, "Edge FX");
    }
});

test("Resource section PE32 & PE32+ ditemukan, PiPL di .text tidak dihitung", () => {
    for (const plus of [false, true]) {
        const rsrc = RSRC_HEAD + effectPiPL("Deep Glow", "PE", "PEDG", true);
        const text = "code" + effectPiPL("Fake", "X", "FAKE in text", true);
        putFile("/t/pe" + plus + ".aex", makePE(rsrc, text, plus));
        const f = new File("/t/pe" + plus + ".aex");
        const rg = api.peResourceRange(f);
        assert.ok(rg && rg.size > 0, "range");
        const pl = api.makePlugin(f, { folder: new Folder("/t"), label: "T" }, false);
        const e = api.readPiPL(pl);
        assert.deepStrictEqual(e.map(x => x.mn), ["PEDG"], "plus=" + plus);
    }
    putFile("/t/notpe.aex", "hello" + effectPiPL("N", "C", "NOTPE Fx", true));
    assert.strictEqual(api.peResourceRange(new File("/t/notpe.aex")), null);
});

test("Pencarian cadangan: pascal = kuat, teks biasa / UTF-16 = lemah", () => {
    const w16 = s => s.split("").map(c => c + "\0").join("");
    putFile("/t/a.bin", "zz\x0dPKD Packed FXzz" + "PLAIN Only" + w16("WIDE Name"));
    const hits = api.scanFileNeedles(new File("/t/a.bin"), ["PKD Packed FX", "PLAIN Only", "WIDE Name", "None Here"]);
    assert.strictEqual(hits["#PKD Packed FX"], 2);
    assert.strictEqual(hits["#PLAIN Only"], 1);
    assert.strictEqual(hits["#WIDE Name"], 1);
    assert.strictEqual(hits["#None Here"], undefined);
});

test("isRenamed / normKey", () => {
    assert.strictEqual(api.isRenamed("Gaussian Blur 2", "Gaussian Blur"), false);
    assert.strictEqual(api.isRenamed("blur halus", "Gaussian Blur"), true);
    assert.strictEqual(api.isRenamed("A_kaca", "A_kaca"), false);
    assert.strictEqual(api.normKey("A_kaca 2"), "akaca2");
});

test("Ekstraksi blok PresetEffects.xml", () => {
    const xml = '<Effects>\n<Effect matchname="Pseudo/abc123" name="$$$/AE/Preset/K=Kontrol">\n<Slider name="x"/>\n</Effect>\n' +
        '<Effect matchname="MYXML &amp; Ctrl" name="Z">\n<Checkbox/>\n</Effect>\n</Effects>';
    assert.ok(api.findPresetEffectBlock(xml, "Pseudo/abc123").indexOf('<Effect matchname="Pseudo/abc123"') === 0);
    assert.ok(/<\/Effect>$/.test(api.findPresetEffectBlock(xml, "Pseudo/abc123")));
    assert.ok(api.findPresetEffectBlock(xml, "MYXML & Ctrl").indexOf("Checkbox") !== -1);
    assert.strictEqual(api.findPresetEffectBlock(xml, "nope"), null);
});

test("Parse Plugin Loading.log", () => {
    putFile("/t/log.txt", [
        "Loading from root path: C:\\Program Files\\Adobe\\Common\\Plug-ins\\7.0\\MediaCore",
        "Loading C:\\Program Files\\Adobe\\Common\\Plug-ins\\7.0\\MediaCore\\NeuralWarp\\NeuralWarpWrapper.aex",
        "The registry tells us to cache so the plugin will be loaded from the cache.",
        "Loading D:\\Plugins\\Saber.aex (cached)",
        "Loading /Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/X.plugin/",
        "Loading C:\\x\\PlayerMediaCore.prm"
    ].join("\r\n"));
    const r = api.parsePluginLogs([new File("/t/log.txt")]);
    assert.deepStrictEqual(r.roots, ["C:\\Program Files\\Adobe\\Common\\Plug-ins\\7.0\\MediaCore"]);
    assert.deepStrictEqual(r.files, [
        "C:\\Program Files\\Adobe\\Common\\Plug-ins\\7.0\\MediaCore\\NeuralWarp\\NeuralWarpWrapper.aex",
        "D:\\Plugins\\Saber.aex",
        "/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/X.plugin"
    ]);
});

test("csvField meng-escape tanda kutip", () => {
    assert.strictEqual(api.csvField('a "b"; c'), '"a ""b""; c"');
});

// -------------------------------------------------------- integration test
function findIn(c, pred) {
    if (!c) return null;
    if (pred(c)) return c;
    for (const ch of (c.children || [])) { const r = findIn(ch, pred); if (r) return r; }
    return null;
}
function fx(mn, name, enabled) { return { matchName: mn, name: name, enabled: enabled !== false }; }
let layerIdSeq = 100;
function layer(name, effects, source) {
    return {
        id: ++layerIdSeq,
        name: name,
        source: source || null,
        property: (k) => k === "ADBE Effect Parade" ? { numProperties: effects.length, property: i => effects[i - 1] } : null
    };
}
function textLayer(name, font) {
    const L = Object.create(global.TextLayer.prototype);
    L.id = ++layerIdSeq;
    L.name = name;
    L.source = null;
    L.property = (k) => {
        if (k === "ADBE Effect Parade") return { numProperties: 0, property: () => null };
        if (k === "ADBE Text Properties") {
            return { property: () => ({ value: { font: font, fontFamily: font.split("-")[0], fontStyle: "Regular", fontLocation: "" }, numKeys: 0 }) };
        }
        return null;
    };
    return L;
}
function project(comps, extra) {
    const p = { numItems: comps.length, item: i => comps[i - 1], selection: [], renderQueue: { numItems: 0, item: () => null } };
    return Object.assign(p, extra || {});
}

const MC = "C:\\Program Files\\Adobe\\Common\\Plug-ins\\7.0\\MediaCore";
const AE = "C:\\Program Files\\Adobe\\Adobe After Effects 2025\\Support Files";

function buildWorld() {
    FSDATA.files.clear(); FSDATA.dirs.clear(); FSDATA.dirs.add("/");
    const pe = (pls, text) => makePE(RSRC_HEAD + pls.join(""), text || "code");
    putFile(MC + "\\VendorA\\AKaca.aex", pe([effectPiPL("A_kaca", "Vendor A", "VNDA A_kaca", true), effectPiPL("a_paya", "Vendor A", "a_paya", true)]));
    putFile(MC + "\\VendorA\\AKacaUnused.aex", pe([effectPiPL("Tidak Dipakai", "Vendor A", "VNDA Unused", true)]));
    putFile(MC + "\\VendorA\\vendor_core.dll", "DLL");
    putFile(MC + "\\VendorA\\AKaca_data\\lut.bin", "LUTDATA");
    putFile(MC + "\\Deep Glow.aex", pe([effectPiPL("Deep Glow", "Plugin Everything", "PEDG", true)]));
    putFile(MC + "\\Deep Glow\\presets.dat", "P");
    putFile(MC + "\\random_other_vendor.dll", "X");
    putFile(MC + "\\Other.aex", pe([effectPiPL("Other", "X", "OTHER Fx", true)]));
    putFile(MC + "\\Packed\\Packed.aex", makePE(RSRC_HEAD + "noPiPLhere", "stub\x0dPKD Packed FXstub"));
    // Boris-like: satu folder banyak file efek + satu file berisi 2 efek
    putFile(MC + "\\BorisFX\\Continuum\\BCC_Glow.aex", pe([effectPiPL("BCC Glow", "BCC Light", "BCC Glow", true)]));
    putFile(MC + "\\BorisFX\\Continuum\\BCC_Lens.aex", pe([effectPiPL("BCC Lens Flare", "BCC Light", "BCC Lens Flare", true)]));
    putFile(MC + "\\BorisFX\\Continuum\\BCC_Blur.aex", pe([effectPiPL("BCC Gaussian Blur", "BCC Blur", "BCC Gaussian Blur", true),
        effectPiPL("BCC Directional Blur", "BCC Blur", "BCC Directional Blur", true)]));
    putFile(MC + "\\BorisFX\\Continuum\\bcc_core.dll", "BCCDLL");
    putFile(MC + "\\BorisFX\\Continuum\\Resources\\huge.dat", "HUGE".repeat(1000));
    putFile(MC + "\\BorisFX\\Sapphire\\S_Glow.aex", pe([effectPiPL("S_Glow", "Sapphire", "S_Glow", true)]));
    putFile(AE + "\\AfterFX.exe", "exe");
    putFile(AE + "\\Plug-ins\\Effects\\HobbyFX.aex", pe([effectPiPL("Hobby Glow", "Hobby", "ADBE Hobby Glow", true)]));
    putFile(AE + "\\Plug-ins\\Effects\\GaussBlur.aex", pe([effectPiPL("Gaussian Blur", "Blur & Sharpen", "ADBE Gaussian Blur 2", true)]));
    putFile(AE + "\\Plug-ins\\(AdobePSL)\\Hidden.aex", pe([effectPiPL("Hidden", "X", "HID Hidden", true)]));
    putFile(AE + "\\PresetEffects.xml", '<?xml version="1.0"?>\n<Effects>\n<Effect matchname="Pseudo/abc123" name="$$$/AE/Preset/K=Kontrol">\n<Slider name="Kekuatan"/>\n</Effect>\n<Effect matchname="MYXML Ctrl" name="$$$/AE/Preset/C=Ctrl XML">\n<Checkbox name="On"/>\n</Effect>\n</Effects>\n');
    putFile("C:\\Users\\test\\Documents\\Adobe\\After Effects 2025\\User Presets\\Blur Halus.ffx", "RIFX");
    putFile("D:\\Plugins Kustom\\Saber\\Saber.aex", pe([effectPiPL("Saber", "Video Copilot", "VIDEOCOPILOT Saber", true)]));
    putFile("D:\\Plugins Kustom\\Saber\\Saber Presets\\a.xml", "x");
    putFile("E:\\Lain\\Twitch.aex", pe([effectPiPL("Twitch", "Video Copilot", "VIDEOCOPILOT Twitch", true)]));
    putFile("C:\\Users\\test\\AppData\\Roaming\\Adobe\\After Effects\\25.5\\logs\\Plugin Loading.log",
        "Loading from root path: D:\\Plugins Kustom\r\nLoading D:\\Plugins Kustom\\Saber\\Saber.aex\r\nLoading E:\\Lain\\Twitch.aex\r\n");
    mkdirs(normPath("C:\\Users\\test\\Desktop\\Hasil"));

    Folder.appPackage = new Folder(AE);
    Folder.startup = new Folder(AE);
    Folder.temp = new Folder("C:\\Users\\test\\AppData\\Local\\Temp");
    Folder.temp.create();
    Folder.userData = new Folder("C:\\Users\\test\\AppData\\Roaming");
    Folder.myDocuments = new Folder("C:\\Users\\test\\Documents");

    app.effects = [
        ["A_kaca", "VNDA A_kaca"], ["a_paya", "a_paya"], ["Tidak Dipakai", "VNDA Unused"], ["Deep Glow", "PEDG"],
        ["Hobby Glow", "ADBE Hobby Glow"], ["Packed FX", "PKD Packed FX"], ["Gaussian Blur", "ADBE Gaussian Blur 2"],
        ["CC Light Sweep", "CC Light Sweep"], ["Slider Control", "ADBE Slider Control"], ["Saber", "VIDEOCOPILOT Saber"],
        ["Twitch", "VIDEOCOPILOT Twitch"], ["Hidden", "HID Hidden"], ["BCC Glow", "BCC Glow"], ["BCC Lens Flare", "BCC Lens Flare"],
        ["BCC Gaussian Blur", "BCC Gaussian Blur"], ["BCC Directional Blur", "BCC Directional Blur"], ["S_Glow", "S_Glow"]
    ].map(a => ({ displayName: a[0], matchName: a[1], category: "Cat", version: "1.0" }));

    // Main -> Sub (precomp). Template = comp yang tidak dipakai (penuh efek Boris).
    const sub = new CompItem(2, "Sub", [
        layer("adj", [fx("VNDA A_kaca", "A_kaca 2"), fx("CC Light Sweep", "CC Light Sweep"), fx("ADBE Slider Control", "Slider Control"),
            fx("BCC Directional Blur", "blur arah")]),
        textLayer("judul", "ScopeFont-Regular")
    ]);
    const main = new CompItem(1, "Main", [
        layer("BG", [fx("VNDA A_kaca", "A_kaca"), fx("ADBE Gaussian Blur 2", "Gaussian Blur"), fx("ADBE Gaussian Blur 2", "blur halus"),
            fx("BCC Glow", "BCC Glow")]),
        layer("Teks", [fx("a_paya", "a_paya"), fx("PEDG", "Deep Glow"), fx("ADBE Hobby Glow", "Hobby Glow"), fx("PKD Packed FX", "Packed FX"),
            fx("Pseudo/abc123", "Kontrol"), fx("XYZ Missing", "Missing"), fx("VIDEOCOPILOT Saber", "Saber"),
            fx("VIDEOCOPILOT Twitch", "Twitch"), fx("MYXML Ctrl", "Ctrl XML"), fx("HID Hidden", "Hidden"),
            fx("S_Glow", "S_Glow mati", false)]),
        layer("Sub", [], sub)
    ]);
    const template = new CompItem(3, "Template Transisi", [
        layer("t1", [fx("BCC Lens Flare", "BCC Lens Flare"), fx("BCC Gaussian Blur", "BCC Gaussian Blur"), fx("OTHER Fx", "Other")]),
        textLayer("judul2", "OutFont-Bold")
    ]);
    return { proj: project([main, sub, template]), main: main, sub: sub, template: template };
}

function runCollect(opts, scopeMode, roots) {
    const w = buildWorld();
    const dest = new Folder("C:\\Users\\test\\Desktop\\Hasil\\Proj_Collected");
    dest.create();
    const report = [], csv = [];
    const opt = Object.assign({ preview: false, support: false, presets: true, skipDisabled: true }, opts || {});
    const scope = api.makeScope(w.proj, scopeMode || "selected", roots || (scopeMode === "all" ? undefined : [w.main]));
    const st = api.collectPlugins(w.proj, dest, report, opt, csv, scope);
    const files = [...FSDATA.files.keys()].filter(p => p.startsWith(dest._p + "/")).map(p => p.substring(dest._p.length + 1)).sort();
    return { st, report: report.join("\n"), csv, files, w };
}
const has = (f, p) => assert.ok(f.indexOf(p) !== -1, "harus ada: " + p + "\n  ada:\n        " + f.join("\n        "));
const hasNot = (f, p) => assert.ok(f.indexOf(p) === -1, "TIDAK boleh ada: " + p + "\n  ada:\n        " + f.join("\n        "));

test("Scope: comp utama + precomp-nya saja, comp template diabaikan", () => {
    const w = buildWorld();
    const sc = api.makeScope(w.proj, "selected", [w.main]);
    assert.deepStrictEqual(sc.comps.map(c => c.name), ["Main", "Sub"]);
    const all = api.makeScope(w.proj, "all");
    assert.deepStrictEqual(all.comps.map(c => c.name), ["Main", "Sub", "Template Transisi"]);
    w.proj.selection = [w.sub, { name: "footage" }];
    assert.deepStrictEqual(api.scopeRoots(w.proj, "selected").map(c => c.name), ["Sub"]);
    w.proj.renderQueue = { numItems: 2, item: i => ({ comp: i === 1 ? w.main : w.main }) };
    assert.deepStrictEqual(api.scopeRoots(w.proj, "rq").map(c => c.name), ["Main"]);
});

test("Hanya FILE plugin yang efeknya dipakai yang dicopy (bukan folder Boris/vendor)", () => {
    const r = runCollect();
    const f = r.files;
    has(f, "(Plugins)/MediaCore/VendorA/AKaca.aex");
    has(f, "(Plugins)/MediaCore/Deep Glow.aex");
    has(f, "(Plugins)/MediaCore/Packed/Packed.aex");
    has(f, "(Plugins)/MediaCore/BorisFX/Continuum/BCC_Glow.aex");
    has(f, "(Plugins)/MediaCore/BorisFX/Continuum/BCC_Blur.aex");
    has(f, "(Plugins)/AE Plug-ins/Effects/HobbyFX.aex");
    has(f, "(Plugins)/Lainnya/Plugins Kustom/Saber/Saber.aex");
    has(f, "(Plugins)/Lainnya/Lain/Twitch.aex");
    for (const p of ["(Plugins)/MediaCore/VendorA/AKacaUnused.aex", "(Plugins)/MediaCore/VendorA/vendor_core.dll",
        "(Plugins)/MediaCore/VendorA/AKaca_data/lut.bin", "(Plugins)/MediaCore/Deep Glow/presets.dat",
        "(Plugins)/MediaCore/BorisFX/Continuum/BCC_Lens.aex", "(Plugins)/MediaCore/BorisFX/Continuum/bcc_core.dll",
        "(Plugins)/MediaCore/BorisFX/Continuum/Resources/huge.dat", "(Plugins)/MediaCore/BorisFX/Sapphire/S_Glow.aex",
        "(Plugins)/MediaCore/Other.aex", "(Plugins)/Lainnya/Plugins Kustom/Saber/Saber Presets/a.xml",
        "(Plugins)/AE Plug-ins/Effects/GaussBlur.aex"]) hasNot(f, p);
    assert.strictEqual(f.filter(p => p.startsWith("(Plugins)/")).length, 8, "tepat 8 file plugin");
    const rep = r.report;
    for (const s of ["Comp yang dibaca : comp yang dipilih: Main  (+1 precomp di dalamnya)",
        "[OK] A_kaca  [match name: VNDA A_kaca]", "nama di layer : A_kaca, A_kaca 2",
        "- MediaCore/BorisFX/Continuum/BCC_Blur.aex", "efek dipakai  : BCC Directional Blur",
        "file ini juga berisi 1 efek lain yang tidak dipakai", "[OK, CEK MANUAL] Packed FX",
        "--- EFEK YANG DIMATIKAN (ikon fx mati, tidak dikumpulkan) ---", "[DIMATIKAN] S_Glow  [match name: S_Glow]",
        "[TIDAK TERINSTALL] Missing", "[TIDAK KETEMU] Hidden", "1 pemakaian efek yang dimatikan dilewati",
        "Yang dicopy hanya FILE plugin"]) {
        assert.ok(rep.indexOf(s) !== -1, "laporan harus memuat: " + s + "\n---\n" + rep);
    }
    assert.ok(rep.indexOf("BCC Lens Flare") === -1, "efek di comp template tidak boleh muncul");
    assert.strictEqual(r.st.copied, 8);
    const offRow = r.csv.find(row => row[4] === "S_Glow");
    assert.strictEqual(offRow[6], "dimatikan, tidak dikumpulkan");
});

test("Opsi 'semua comp' membaca comp template juga", () => {
    const r = runCollect({}, "all");
    has(r.files, "(Plugins)/MediaCore/BorisFX/Continuum/BCC_Lens.aex");
    has(r.files, "(Plugins)/MediaCore/Other.aex");
    hasNot(r.files, "(Plugins)/MediaCore/BorisFX/Continuum/bcc_core.dll");
});

test("Efek yang dimatikan tetap ikut kalau opsi 'lewati' dimatikan", () => {
    const r = runCollect({ skipDisabled: false });
    has(r.files, "(Plugins)/MediaCore/BorisFX/Sapphire/S_Glow.aex");
});

test("Opsi file pendukung: DLL di folder vendor ikut, plugin lain & folder besar tidak", () => {
    const f = runCollect({ support: true }).files;
    has(f, "(Plugins)/MediaCore/VendorA/vendor_core.dll");
    has(f, "(Plugins)/MediaCore/BorisFX/Continuum/bcc_core.dll");
    has(f, "(Plugins)/MediaCore/Deep Glow/presets.dat");
    hasNot(f, "(Plugins)/MediaCore/random_other_vendor.dll");
    hasNot(f, "(Plugins)/MediaCore/BorisFX/Continuum/BCC_Lens.aex");
    hasNot(f, "(Plugins)/MediaCore/BorisFX/Continuum/Resources/huge.dat");
    hasNot(f, "(Plugins)/MediaCore/VendorA/AKacaUnused.aex");
});

test("Dialog daftar plugin: hapus centang -> file tidak dicopy, laporan jelas", () => {
    global.__onShow = (dlg) => {
        const lb = findIn(dlg, c => c.type === "listbox");
        const dg = lb.items.find(it => /Deep Glow\.aex$/.test(it.text));
        assert.ok(lb.items.every(it => it.checked === true), "semua yang pasti dicentang di awal");
        lb.selection = [dg];
        const btn = findIn(dlg, c => c.type === "button" && c.text === "Centang / hapus yang dipilih");
        btn.onClick();
        assert.strictEqual(dg.checked, false);
        const total = findIn(dlg, c => c.type === "statictext" && /file plugin dicentang/.test(c.text));
        assert.ok(/^7 dari 8 file plugin dicentang/.test(total.text), total.text);
        findIn(dlg, c => c.type === "button" && c.text === "Copy yang dicentang").onClick();
        return dlg.closed;
    };
    global.__controls = [];
    try {
        const r = runCollect({ preview: true });
        hasNot(r.files, "(Plugins)/MediaCore/Deep Glow.aex");
        has(r.files, "(Plugins)/MediaCore/VendorA/AKaca.aex");
        assert.ok(r.report.indexOf("[TIDAK DICOPY] Deep Glow") !== -1, r.report);
        assert.strictEqual(r.st.unchecked, 1);
    } finally { global.__onShow = null; }
});

test("Dialog daftar plugin: 'Jangan copy plugin' -> tidak ada yang dicopy", () => {
    global.__onShow = (dlg) => { findIn(dlg, c => c.text === "Jangan copy plugin").onClick(); return dlg.closed; };
    global.__controls = [];
    try {
        const r = runCollect({ preview: true });
        assert.strictEqual(r.files.filter(p => p.startsWith("(Plugins)/")).length, 0);
        assert.strictEqual(r.st.copied, 0);
    } finally { global.__onShow = null; }
});

test("Font hanya dari comp yang dibaca", () => {
    const w = buildWorld();
    w.proj.usedFonts = [
        { font: { postScriptName: "ScopeFont-Regular", familyName: "ScopeFont", styleName: "Regular", location: "" }, usedAt: [{ layerID: w.sub.layer(2).id }] },
        { font: { postScriptName: "OutFont-Bold", familyName: "OutFont", styleName: "Bold", location: "" }, usedAt: [{ layerID: w.template.layer(2).id }] }
    ];
    const inScope = api.gatherFonts(w.proj, api.makeScope(w.proj, "selected", [w.main])).list.map(f => f.ps);
    assert.deepStrictEqual(inScope, ["ScopeFont-Regular"]);
    const all = api.gatherFonts(w.proj, api.makeScope(w.proj, "all")).list.map(f => f.ps).sort();
    assert.deepStrictEqual(all, ["OutFont-Bold", "ScopeFont-Regular"]);
});

test("Efek yang tidak terinstall tidak memicu pencarian isi file penuh", () => {
    buildWorld();
    let fullScans = 0;
    const origRead = File.prototype.read;
    File.prototype.read = function (n) {
        if (this.encoding === "BINARY" && n === 4 * 1024 * 1024 && this._pos === 0 && /\.aex$/i.test(this._p)) fullScans++;
        return origRead.call(this, n);
    };
    try {
        const comp = new CompItem(9, "X", [layer("L", [fx("VNDA A_kaca", "A_kaca"), fx("XYZ Missing", "Missing")])]);
        const proj = project([comp]);
        const dest = new Folder("C:\\Users\\test\\Desktop\\Hasil\\P2"); dest.create();
        const st = api.collectPlugins(proj, dest, [], { preview: false, support: false, presets: false, skipDisabled: true }, [], api.makeScope(proj, "all"));
        assert.strictEqual(st.notInstalled, 1);
        assert.strictEqual(fullScans, 0, "tidak boleh ada pembacaan isi file penuh");
    } finally { File.prototype.read = origRead; }
});

test("Mac: hanya bundle .plugin yang dipakai, bukan folder vendor", () => {
    H.setOS("Macintosh");
    try {
        FSDATA.files.clear(); FSDATA.dirs.clear(); FSDATA.dirs.add("/");
        const MCM = "/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore";
        putFile(MCM + "/VendorM/Glow.plugin/Contents/Resources/Glow.rsrc", "rsrcHDR" + effectPiPL("M Glow", "Vendor M", "VNDM Glow", false));
        putFile(MCM + "/VendorM/Glow.plugin/Contents/MacOS/Glow", "\xcf\xfa\xed\xfebinary");
        putFile(MCM + "/VendorM/Other.plugin/Contents/Resources/O.rsrc", "rsrc" + effectPiPL("M Other", "Vendor M", "VNDM Other", false));
        putFile(MCM + "/VendorM/Shared/lib.dylib", "lib");
        const APP = "/Applications/Adobe After Effects 2025/Adobe After Effects 2025.app";
        putFile(APP + "/Contents/MacOS/After Effects", "bin");
        Folder.appPackage = new Folder(APP);
        Folder.startup = new Folder(APP + "/Contents/MacOS");
        Folder.userData = new Folder("/Users/test/Library/Application Support");
        Folder.myDocuments = new Folder("/Users/test/Documents");
        app.effects = [{ displayName: "M Glow", matchName: "VNDM Glow", category: "Vendor M", version: "2" },
            { displayName: "M Other", matchName: "VNDM Other", category: "Vendor M", version: "2" }];
        const proj = project([new CompItem(1, "Main", [layer("L", [fx("VNDM Glow", "kaca mac")])])]);
        const dest = new Folder("/Users/test/Desktop/Out"); dest.create();
        const report = [];
        const st = api.collectPlugins(proj, dest, report, { preview: false, support: false, presets: false, skipDisabled: true }, [], api.makeScope(proj, "all"));
        const files = [...FSDATA.files.keys()].filter(p => p.startsWith("/Users/test/Desktop/Out/")).map(p => p.substring(24)).sort();
        has(files, "(Plugins)/MediaCore/VendorM/Glow.plugin/Contents/Resources/Glow.rsrc");
        has(files, "(Plugins)/MediaCore/VendorM/Glow.plugin/Contents/MacOS/Glow");
        hasNot(files, "(Plugins)/MediaCore/VendorM/Shared/lib.dylib");
        hasNot(files, "(Plugins)/MediaCore/VendorM/Other.plugin/Contents/Resources/O.rsrc");
        assert.ok(report.join("\n").indexOf("nama di layer : kaca mac") !== -1);
        assert.strictEqual(st.copied, 1);
    } finally { H.setOS("Windows 10"); }
});

test("Tebakan nama file tidak asal cocok", () => {
    const mk = (n) => ({ parts: [n], target: { fsName: n } });
    const plugins = [mk("Deep Glow.aex"), mk("Saber.aex")];
    assert.strictEqual(api.guessByFileName(plugins, { displayName: "Glow", matchName: "XX Glow", names: ["Glow"] }), null);
    const g = api.guessByFileName(plugins, { displayName: "Saber", matchName: "VC Saber", names: ["Saber"] });
    assert.ok(g && g.how === "nama-file");
});

test("CSV UTF-16LE + BOM + tab, non-ASCII aman", () => {
    putFile("/t/x.csv", "");
    const f = new File("/t/x.csv");
    assert.ok(api.writeCsv(f, [["Comp", "Layer"], ["Kaca \u00e9", 'a"b\tc']]));
    const raw = FSDATA.files.get("/t/x.csv");
    assert.strictEqual(raw.substring(0, 2), "\xff\xfe");
    const text = Buffer.from(raw.substring(2), "latin1").toString("utf16le");
    assert.strictEqual(text, '"Comp"\t"Layer"\r\n"Kaca \u00e9"\t"a""b c"\r\n');
});

test("Folder picker Windows: perintah PowerShell & hasil OK/CANCEL/ERROR", () => {
    buildWorld();
    let cmdSeen = "";
    global.__callSystem = (cmd) => {
        cmdSeen = cmd;
        const outPath = cmd.match(/"([^"]*pick_out\.txt)"/)[1];
        const o = new File(outPath); o.encoding = "UTF-8"; o.open("w"); o.write(global.__pickerAnswer); o.close();
        return "";
    };
    global.__pickerAnswer = "OK|C:\\Users\\test\\Desktop\\Hasil";
    let r = api.pickFolderWindows("Pilih folder", "C:\\Users\\test\\Desktop");
    assert.strictEqual(r.status, "ok");
    assert.strictEqual(r.folder.fsName, "C:\\Users\\test\\Desktop\\Hasil");
    assert.ok(/^powershell\.exe -NoProfile .* -File "C:\\Users\\test\\AppData\\Local\\Temp\\CollectFilesPlus\\pick_folder_v3\.ps1" "/.test(cmdSeen), cmdSeen);
    global.__pickerAnswer = "CANCEL";
    assert.strictEqual(api.pickFolderWindows("x", "").status, "cancel");
    global.__pickerAnswer = "ERROR|Add-Type gagal";
    r = api.pickFolderWindows("x", "");
    assert.strictEqual(r.status, "error");
    assert.strictEqual(r.message, "Add-Type gagal");
});

test("Script PowerShell: here-string & kurung seimbang", () => {
    const ps = api.pickerPowerShell();
    const lines = ps.split("\n");
    const open = lines.findIndex(l => /@'$/.test(l));
    const close = lines.findIndex(l => l === "'@");
    assert.ok(open > 0 && close > open, "here-string");
    assert.ok(lines[0].startsWith("param("), "param harus baris pertama");
    const cs = lines.slice(open + 1, close).join("\n");
    const psOnly = lines.slice(0, open + 1).concat(lines.slice(close + 1)).join("\n");
    const bal = (s, a, b) => s.split(a).length - s.split(b).length;
    assert.strictEqual(bal(cs, "{", "}"), 0, "C# { }");
    assert.strictEqual(bal(cs, "(", ")"), 0, "C# ( )");
    assert.strictEqual(bal(psOnly, "{", "}"), 0, "PS { }");
    assert.strictEqual(bal(psOnly, "(", ")"), 0, "PS ( )");
});

test("Dialog opsi: default scope & validasi", () => {
    const w = buildWorld();
    // 1) ada comp yang dipilih -> default 'selected'
    let captured = null;
    global.__onShow = (dlg) => {
        const dd = findIn(dlg, c => c.type === "dropdownlist");
        captured = dd.selection.index;
        findIn(dlg, c => c.type === "button" && c.text === "Mulai").onClick();
        return dlg.closed;
    };
    global.__controls = [];
    try {
        let opt = api.showOptions("C:\\Users\\test\\Desktop\\Hasil", { selected: [w.main], selectedIsActive: false, rq: [], all: [w.main, w.sub, w.template] });
        assert.strictEqual(captured, 0);
        assert.strictEqual(opt.scope, "selected");
        assert.strictEqual(opt.preview, true);
        assert.strictEqual(opt.support, false);
        assert.strictEqual(opt.presets, false);
        assert.strictEqual(opt.skipDisabled, true);
        // 2) tidak ada pilihan, RQ ada -> default 'rq'
        global.__controls = [];
        opt = api.showOptions("C:\\Users\\test\\Desktop\\Hasil", { selected: [w.sub], selectedIsActive: true, rq: [w.main], all: [w.main] });
        assert.strictEqual(captured, 1);
        assert.strictEqual(opt.scope, "rq");
        // 3) pilih 'selected' tapi kosong -> ditolak (dialog tidak tertutup)
        global.__onShow = (dlg) => {
            const dd = findIn(dlg, c => c.type === "dropdownlist");
            dd.selection = 0;
            findIn(dlg, c => c.type === "button" && c.text === "Mulai").onClick();
            return dlg.closed === undefined ? 0 : dlg.closed;
        };
        global.__controls = [];
        global.__alerts = [];
        opt = api.showOptions("C:\\Users\\test\\Desktop\\Hasil", { selected: [], selectedIsActive: false, rq: [], all: [w.main] });
        assert.strictEqual(opt, null);
        assert.ok(global.__alerts.some(a => /Belum ada comp yang dipilih/.test(a)), global.__alerts.join("|"));
    } finally { global.__onShow = null; }
});

test("main(): alur lengkap jalan tanpa error (scope comp dipilih + reduce)", () => {
    const w = buildWorld();
    let reducedWith = null, saves = [];
    const projFile = new File("C:\\Users\\test\\Desktop\\Proj.aep");
    putFile("C:\\Users\\test\\Desktop\\Proj.aep", "AEP");
    Object.assign(w.proj, {
        file: projFile, dirty: false, selection: [w.main], activeItem: null,
        save: (f) => { saves.push(f ? f.fsName : "(same)"); if (f) putFile(f.fsName, "AEPCOPY"); },
        reduceProject: (items) => { reducedWith = items.map(i => i.name); return 5; }
    });
    global.app.project = w.proj;
    global.__alerts = [];
    global.__callSystem = () => "";
    global.__onShow = (dlg) => {
        if (dlg.text === "Collect Files Plus") {
            findIn(dlg, c => c.type === "edittext").text = "C:\\Users\\test\\Desktop\\Hasil";
            findIn(dlg, c => c.type === "checkbox" && /Reduce Project/.test(c.text)).value = true;
            findIn(dlg, c => c.type === "button" && c.text === "Mulai").onClick();
            return dlg.closed;
        }
        findIn(dlg, c => c.text === "Copy yang dicentang").onClick();
        return dlg.closed;
    };
    global.__controls = [];
    try {
        api.main();
    } finally { global.__onShow = null; }
    const errs = global.__alerts.filter(a => /^Error/.test(a));
    assert.deepStrictEqual(errs, [], "tidak boleh ada error");
    const done = global.__alerts.find(a => /^Selesai/.test(a));
    assert.ok(done, global.__alerts.join("\n---\n"));
    assert.ok(/Comp dibaca: comp yang dipilih: Main/.test(done), done);
    assert.ok(/Reduce Project: 5 item/.test(done), done);
    assert.deepStrictEqual(reducedWith, ["Main"]);
    const base = "C:\\Users\\test\\Desktop\\Hasil\\Proj_Collected\\";
    assert.ok(FSDATA.files.has(normPath(base + "Proj_report.txt")));
    assert.ok(FSDATA.files.has(normPath(base + "Proj_daftar_efek.csv")));
    assert.ok(FSDATA.files.has(normPath(base + "(Plugins)\\MediaCore\\BorisFX\\Continuum\\BCC_Glow.aex")));
    assert.ok(!FSDATA.files.has(normPath(base + "(Plugins)\\MediaCore\\BorisFX\\Continuum\\BCC_Lens.aex")));
    assert.deepStrictEqual(saves, [base + "Proj.aep", "(same)"]);
    const rep = Buffer.from(FSDATA.files.get(normPath(base + "Proj_report.txt")), "latin1").toString("utf8");
    assert.ok(rep.indexOf("=== REDUCE PROJECT ===") !== -1);
    assert.ok(rep.indexOf("=== FONT ===") !== -1 && rep.indexOf("=== FOOTAGE ===") !== -1);
});

console.log("\n" + passed + " test lulus" + (process.exitCode ? ", ADA YANG GAGAL" : ""));
