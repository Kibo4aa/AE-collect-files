// Test harness: menjalankan fungsi-fungsi CollectFilesPlus.jsx di Node dengan
// tiruan ExtendScript (File/Folder in-memory) dan tiruan After Effects.
"use strict";
const fs = require("fs");
const path = require("path");

// ------------------------------------------------------------ in-memory FS
const FSDATA = { files: new Map(), dirs: new Set(["/"]) };
let OS = "Windows 10";
const isWinMode = () => OS.indexOf("Windows") !== -1;

function normPath(p) {
    p = String(p);
    if (/^file:\/\//.test(p)) p = p.replace(/^file:\/\//, "");
    if (/^[A-Za-z]:/.test(p)) p = "/" + p.substring(3).replace(/\\/g, "/");   // C:\a\b -> /a/b
    else if (p.startsWith("~")) p = "/Users/test" + p.substring(1);
    p = p.replace(/\\/g, "/");
    p = p.split("/").map(s => { try { return decodeURIComponent(s); } catch (e) { return s; } }).join("/");
    p = path.posix.normalize(p);
    if (p.length > 1 && p.endsWith("/")) p = p.slice(0, -1);
    if (!p.startsWith("/")) p = "/" + p;
    return p;
}
function mkdirs(p) {
    const parts = p.split("/").filter(Boolean);
    let cur = "";
    for (const s of parts) { cur += "/" + s; FSDATA.dirs.add(cur); }
}
function putFile(p, content) {
    p = normPath(p);
    mkdirs(path.posix.dirname(p));
    FSDATA.files.set(p, content);
}

class FSObj {
    constructor(p) { this._p = normPath(p); this.encoding = "UTF-8"; this.lineFeed = "Unix"; }
    get name() { return encodeURIComponent(path.posix.basename(this._p)); }
    get fsName() { return isWinMode() ? "C:" + this._p.replace(/\//g, "\\") : this._p; }
    get absoluteURI() { return this._p.split("/").map(s => encodeURIComponent(s)).join("/"); }
    get parent() { const d = path.posix.dirname(this._p); return d === this._p ? null : new Folder(d); }
    toString() { return this.fsName; }
}
class File extends FSObj {
    constructor(p) { super(p); this._pos = 0; this._open = false; this._buf = null; this._mode = null; this.alias = false; }
    get exists() { return FSDATA.files.has(this._p); }
    get length() { return FSDATA.files.has(this._p) ? FSDATA.files.get(this._p).length : -1; }
    get eof() { return this._pos >= (this._buf || "").length; }
    open(mode) {
        if (mode === "r") { if (!this.exists) return false; this._buf = FSDATA.files.get(this._p); }
        else { if (!FSDATA.dirs.has(path.posix.dirname(this._p))) return false; this._buf = ""; }
        this._mode = mode; this._pos = 0; this._open = true; return true;
    }
    seek(pos) { this._pos = pos; return true; }
    read(n) {
        if (this.encoding !== "BINARY" && n === undefined) {
            const s = Buffer.from(this._buf.slice(this._pos), "latin1").toString("utf8");
            this._pos = this._buf.length; return s;
        }
        const end = n === undefined ? this._buf.length : this._pos + n;
        const s = this._buf.substring(this._pos, end); this._pos = Math.min(end, this._buf.length); return s;
    }
    write(s) {
        if (this.encoding === "BINARY") this._buf += s;
        else this._buf += Buffer.from(s, "utf8").toString("latin1");
        return true;
    }
    close() { if (this._open && this._mode === "w") FSDATA.files.set(this._p, this._buf); this._open = false; return true; }
    copy(target) {
        const t = target instanceof FSObj ? target._p : normPath(target);
        if (!FSDATA.dirs.has(path.posix.dirname(t))) return false;
        FSDATA.files.set(t, FSDATA.files.get(this._p)); return true;
    }
    remove() { FSDATA.files.delete(this._p); return true; }
    resolve() { return this; }
}
File.encode = s => encodeURIComponent(s);
File.decode = s => decodeURIComponent(s);
class Folder extends FSObj {
    get exists() { return FSDATA.dirs.has(this._p); }
    create() { mkdirs(this._p); return true; }
    getFiles(mask) {
        if (!this.exists) return null;
        const out = [], pre = this._p === "/" ? "/" : this._p + "/";
        let re = null;
        if (mask) re = new RegExp("^" + mask.replace(/\./g, "\\.").replace(/\*/g, ".*") + "$", "i");
        const seen = new Set();
        for (const d of FSDATA.dirs) {
            if (d.startsWith(pre) && d !== this._p) {
                const rest = d.substring(pre.length);
                if (rest && rest.indexOf("/") === -1 && !seen.has(d)) { seen.add(d); if (!re || re.test(rest)) out.push(new Folder(d)); }
            }
        }
        for (const f of FSDATA.files.keys()) {
            if (f.startsWith(pre)) {
                const rest = f.substring(pre.length);
                if (rest.indexOf("/") === -1 && (!re || re.test(rest))) out.push(new File(f));
            }
        }
        out.sort((a, b) => a._p < b._p ? -1 : 1);
        return out;
    }
    execute() { return true; }
    selectDlg() { return null; }
}
Folder.selectDialog = () => null;

// ------------------------------------------------------- ExtendScript globals
const ENV = { ProgramW6432: "C:\\Program Files", ProgramFiles: "C:\\Program Files", SystemRoot: "C:\\Windows" };
global.$ = { get os() { return OS; }, getenv: n => ENV[n] || null };
global.File = File;
global.Folder = Folder;
function makeCtl(type, text, props) {
    const c = { type: type, text: text === undefined ? "" : text, preferredSize: {}, children: [], items: [],
        enabled: true, value: false, properties: props || {}, margins: 0 };
    let sel = null;
    Object.defineProperty(c, "selection", {
        get() { return sel; },
        set(v) {
            if (typeof v === "number") sel = { index: v, text: Array.isArray(c.text) ? c.text[v] : "" };
            else sel = v;
        }
    });
    c.add = function (t, b, txt, pr) {
        if (c.type === "listbox" && t === "item") {
            const it = { text: b, subItems: [{ text: "" }, { text: "" }, { text: "" }], checked: undefined };
            c.items.push(it);
            return it;
        }
        const child = makeCtl(t, txt, pr);
        c.children.push(child);
        global.__controls.push(child);
        return child;
    };
    c.show = function () {
        if (c.type === "dialog" && global.__onShow) {
            const r = global.__onShow(c);
            if (r !== undefined) return r;
        }
        return c.type === "dialog" ? 1 : undefined;
    };
    c.close = function (v) { c.closed = v; };
    c.update = function () {};
    return c;
}
global.__controls = [];
global.__onShow = null;
global.Window = function (type, title) { return makeCtl(type, title); };
global.alert = (m) => { global.__alerts.push(String(m)); };
global.__alerts = [];
global.confirm = () => true;
global.system = { callSystem: (cmd) => global.__callSystem(cmd) };
global.__callSystem = () => "";
class CompItem { constructor(id, name, layers) { this.id = id; this.name = name; this._layers = layers; } get numLayers() { return this._layers.length; } layer(i) { return this._layers[i - 1]; } }
global.CompItem = CompItem;
global.FootageItem = function () {};
global.FolderItem = function () {};
global.TextLayer = function () {};
global.FileSource = function () {};
global.ImportAsType = {};
global.app = {
    version: "25.5x12",
    effects: [],
    settings: { haveSetting: () => false, getSetting: () => "", saveSetting: () => {} },
    preferences: { getPrefAsLong: () => 1 }
};

// --------------------------------------------------- load script as module
function loadScript() {
    let src = fs.readFileSync(path.join(__dirname, "..", "CollectFilesPlus.jsx"), "utf8");
    const at = src.lastIndexOf("    try {\n        main();");
    if (at < 0) throw new Error("main() call not found");
    const exportsList = ["parsePiPLProp", "scanPiPLRange", "readPiPL", "peResourceRange", "matchByPiPL",
        "scanFileNeedles", "fallbackScan", "findPresetEffectBlock", "relParts", "parsePluginLogs",
        "isRenamed", "normKey", "FIRST_PARTY", "csvField", "collectPlugins", "buildPluginList", "makePlugin",
        "pickFolderWindows", "pickerPowerShell", "gatherEffects", "copyStats", "subFolder", "guessByFileName",
        "matchPresets", "writeCsv", "supportItems", "confirmPluginCopy", "scopeRoots", "expandComps", "makeScope",
        "gatherFonts", "copyCandidate", "scopeText", "showOptions", "main"];
    src = src.substring(0, at) + "    return {" + exportsList.map(n => n + ": " + n).join(", ") + "};\n})();\n";
    src = src.replace("(function collectFilesPlus() {", "global.__api = (function collectFilesPlus() {");
    // eslint-disable-next-line no-eval
    (0, eval)(src);
    return global.__api;
}

module.exports = { FSDATA, putFile, File, Folder, CompItem, normPath, mkdirs, loadScript, setOS: o => { OS = o; }, ENV };
