"""Laporan teks + CSV daftar efek."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple

from . import __version__
from .plugins import CERTAIN_HOW, HOW_LABEL

if TYPE_CHECKING:
    from .collector import Analysis, EffectInfo, Result

KIND_LABEL = {
    "plugin": "Plugin pihak ketiga",
    "builtin": "Bawaan After Effects",
    "pseudo": "Pseudo effect",
    "presetxml": "PresetEffects.xml",
}


def fmt_bytes(n: int) -> str:
    if n >= 1 << 30:
        return "%.1f GB" % (n / (1 << 30))
    if n >= 1 << 20:
        return "%.1f MB" % (n / (1 << 20))
    if n >= 1 << 10:
        return "%d KB" % round(n / 1024)
    return "%d B" % n


def uses_text(e: "EffectInfo", limit: int = 6) -> str:
    parts = ["%s > #%d %s" % (u.comp, u.layer_index, u.layer_name) for u in e.group.uses[:limit]]
    if e.count > limit:
        parts.append("... (+%d)" % (e.count - limit))
    return "; ".join(parts)


def effect_title(e: "EffectInfo") -> str:
    return "%s  [match name: %s]" % (e.title, e.match_name)


def effect_status(e: "EffectInfo") -> Tuple[str, str]:
    """(tag laporan, status CSV)."""
    if e.kind == "builtin":
        return "", "bawaan AE"
    if e.kind == "pseudo":
        return "", "tersimpan di project"
    if e.kind == "presetxml":
        return "", "definisi XML diekspor"
    cd = e.candidate
    if cd is not None:
        if cd.selected:
            if cd.ok is False:
                return "[GAGAL COPY]", "gagal copy"
            if cd.ok is None:
                return "[DIPILIH]", "akan dicopy"
            if e.match is not None and e.match.how in CERTAIN_HOW:
                return "[OK]", "dicopy"
            return "[OK, CEK MANUAL]", "dicopy (cek manual)"
        if cd.strict:
            return "[TIDAK DICOPY]", "tidak dicopy (centang dihapus)"
        return "[PERKIRAAN, TIDAK DICOPY]", "perkiraan, tidak dicopy"
    return "[TIDAK KETEMU]", "file plugin tidak ketemu"


def scope_text(an: "Analysis") -> str:
    if an.options.scope_label:
        return an.options.scope_label
    if an.options.comp_ids is None:
        return "semua comp di project (%d comp)" % len(an.comps)
    names = [c.name for c in an.roots[:8]]
    extra = len(an.comps) - len(an.roots)
    text = ", ".join(names) + (" ..." if len(an.roots) > 8 else "")
    return text + ("  (+%d precomp di dalamnya)" % extra if extra > 0 else "")


def build_report(an: "Analysis", res: Optional["Result"] = None) -> List[str]:
    import py_aep

    L: List[str] = []
    L.append("Collect Files Plus - laporan")
    L.append("Project asal : %s" % an.aep.path)
    if res is not None:
        L.append("Folder hasil : %s" % res.dest_root)
    L.append("Comp dibaca  : %s" % scope_text(an))
    L.append("Tanggal      : %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    L.append("Versi        : Collect Files Plus %s (py_aep %s)" % (__version__, getattr(py_aep, "__version__", "?")))
    L.append("")

    if res is not None:
        if not res.saved_ok:
            L.append("!!! PERHATIAN: %s" % res.validation_error)
            L.append("!!! Pakai project di folder (Backup) lalu relink footage ke folder (Footage).")
            L.append("")
        elif res.backup is not None:
            L.append("Project hasil collect: %s (sudah di-relink ke folder (Footage))." % res.project_out.name)
            L.append("Cadangan project asli (belum diubah): (Backup)/%s" % res.backup.name)
            L.append("")
        for err in res.errors:
            L.append("[ERROR] " + err)
        if res.errors:
            L.append("")

    opt = an.options
    if opt.collect_footage:
        L.append("=== FOOTAGE ===")
        if res is not None and res.reduced >= 0:
            L.append("Reduce Project: %d item yang tidak dipakai dibuang dari project hasil." % res.reduced)
        ok = missing = failed = 0
        total = 0
        for fe in an.footage:
            names = ", ".join(fe.names)
            extra = "  (sequence, %d frame)" % len(fe.files) if fe.is_sequence else ""
            if fe.extras:
                extra += "  (+%d file pendukung model 3D)" % len(fe.extras)
            if not fe.exists:
                missing += 1
                L.append("[HILANG]  %s  ->  %s" % (names, fe.src))
            elif fe.copied is False:
                failed += 1
                L.append("[GAGAL]   %s  ->  %s  (%s)" % (names, fe.src, fe.error))
            else:
                ok += 1
                total += fe.size
                tag = "[OK]     " if fe.copied else "[DIPILIH]"
                L.append("%s %s  <-  %s  (%s)%s" % (tag, names, fe.src, fmt_bytes(fe.size), extra))
        if not an.footage:
            L.append("Tidak ada footage file.")
        L.append("Total: %d file/sequence (%s), %d hilang, %d gagal." % (ok, fmt_bytes(total), missing, failed))
        L.append("")

    if opt.collect_fonts:
        L.append("=== FONT ===")
        if not an.fonts:
            L.append("Tidak ada font yang dipakai.")
        n_ok = 0
        for f in an.fonts:
            if f.face is not None:
                n_ok += 1 if f.copied is not False else 0
                tag = "[OK]     " if f.copied else ("[GAGAL]  " if f.copied is False else "[DIPILIH]")
                L.append("%s %s  [%s %s]  <-  %s" % (tag, f.post_script_name, f.face.family, f.face.style, f.face.path))
            elif f.status == "adobe":
                L.append("[ADOBE FONTS] %s  -> aktifkan lewat Creative Cloud di komputer tujuan" % f.post_script_name)
            else:
                L.append("[TIDAK KETEMU] %s  -> tidak terinstall di komputer ini (atau dari Adobe Fonts)" % f.post_script_name)
        L.append("Total: %d font dipakai, %d ada file-nya." % (len(an.fonts), n_ok))
        L.append("")

    L.extend(_effects_section(an))
    L.extend(how_to_use())
    return L


def _effects_section(an: "Analysis") -> List[str]:
    L: List[str] = []
    groups = {"plugin": [], "presetxml": [], "pseudo": [], "builtin": []}  # type: dict
    for e in an.effects:
        groups[e.kind].append(e)
    uses = sum(e.count for e in an.effects)
    L.append("=== EFEK & PLUGIN ===")
    L.append("Terbaca          : %d pemakaian efek, %d jenis efek%s." % (
        uses, len(an.effects),
        "  (%d pemakaian efek yang dimatikan dilewati)" % an.disabled_uses if an.disabled_uses else ""))
    L.append("Efek plugin pihak ketiga: %d  |  Bawaan AE: %d  |  Pseudo effect: %d  |  PresetEffects.xml: %d" % (
        len(groups["plugin"]), len(groups["builtin"]), len(groups["pseudo"]), len(groups["presetxml"])))
    L.append("Yang dicopy hanya FILE plugin yang berisi efek di atas, bukan seluruh folder plugin.")
    L.append("Daftar lengkap per comp & layer ada di file *_daftar_efek.csv.")
    for note in an.notes:
        L.append("(%s)" % note)
    L.append("")

    L.append("--- PLUGIN PIHAK KETIGA ---")
    if not groups["plugin"]:
        L.append("Tidak ada.")
    not_found = 0
    for e in groups["plugin"]:
        tag, _ = effect_status(e)
        if tag == "[TIDAK KETEMU]":
            not_found += 1
        L.append("%s %s" % (tag, effect_title(e)))
        if e.category:
            L.append("     kategori      : %s" % e.category)
        L.append("     nama di layer : %s" % ", ".join(e.names))
        L.append("     dipakai %dx    : %s" % (e.count, uses_text(e)))
        if e.match is not None:
            L.append("     file plugin   : %s" % e.match.plugin.target)
            if e.match.how != "pipl":
                L.append("     cara ketemu   : %s -> pastikan file ini memang plugin-nya" % HOW_LABEL.get(e.match.how, e.match.how))
            cd = e.candidate
            if cd is not None and cd.selected and cd.ok:
                L.append("     dicopy ke     : (Plugins)/%s" % cd.dest_rel)
            elif cd is not None and not cd.selected:
                L.append("     catatan       : %s" % (
                    "tidak dicopy karena centangnya dihapus" if cd.strict else
                    "tidak dicopy otomatis karena hanya perkiraan; centang di daftar kalau memang benar"))
            if e.match.plugin.root.is_app:
                L.append("     catatan       : file ini ada di folder plugin After Effects sendiri")
        else:
            L.append("     catatan       : plugin ini tidak ada di komputer ini, atau file-nya di luar folder plugin yang dimuat AE")
    L.append("")

    L.append("--- FILE PLUGIN YANG DICOPY ---")
    chosen = [cd for cd in an.candidates if cd.selected]
    if not chosen:
        L.append("Tidak ada.")
    for cd in chosen:
        tag = "- " if cd.ok is not False else "- [GAGAL] "
        L.append("%s%s  (%s)" % (tag, cd.label, fmt_bytes(cd.size)))
        L.append("     efek dipakai  : %s" % ", ".join(e.title for e in cd.effects))
        if cd.others:
            L.append("     catatan       : file ini juga berisi %d efek lain yang tidak dipakai (satu file, tidak bisa dipisah)" % cd.others)
        if cd.support:
            L.append("     file pendukung: %d file/folder ikut dicopy" % len(cd.support))
    L.append("")

    if groups["presetxml"]:
        L.append("--- EFEK DARI PresetEffects.xml ---")
        for e in groups["presetxml"]:
            L.append("[XML] %s" % effect_title(e))
            L.append("     nama di layer : %s" % ", ".join(e.names))
            L.append("     dipakai %dx    : %s" % (e.count, uses_text(e)))
        L.append("Definisinya diekspor ke (PresetEffects)/PresetEffects_dari_project.xml.")
        L.append("")

    if groups["pseudo"]:
        L.append("--- PSEUDO EFFECT (sudah tersimpan di dalam project, tidak perlu dicopy) ---")
        for e in groups["pseudo"]:
            L.append("[PSEUDO] %s%s" % (effect_title(e), "  (definisi ikut diekspor)" if e.xml_block else ""))
            L.append("     nama di layer : %s" % ", ".join(e.names))
            L.append("     dipakai %dx    : %s" % (e.count, uses_text(e)))
        L.append("")

    L.append("--- EFEK BAWAAN AFTER EFFECTS (tidak perlu dicopy) ---")
    if not groups["builtin"]:
        L.append("Tidak ada.")
    for e in groups["builtin"]:
        L.append("- %s  %dx  | nama di layer: %s" % (effect_title(e), e.count, ", ".join(e.names)))
    L.append("")

    if an.disabled_only:
        L.append("--- EFEK YANG DIMATIKAN (ikon fx mati, tidak dikumpulkan) ---")
        for e in an.disabled_only:
            L.append("[DIMATIKAN] %s  (%s)" % (effect_title(e), KIND_LABEL[e.kind]))
            L.append("     nama di layer : %s" % ", ".join(e.names))
            L.append("     di            : %s" % uses_text(e))
        L.append("Kalau plugin efek ini tidak ada di komputer tujuan, AE tetap memberi peringatan")
        L.append('"missing" saat project dibuka, tapi hasil render tidak berubah.')
        L.append("")

    if an.options.presets:
        L.append("--- ANIMATION PRESET (.ffx) YANG NAMANYA COCOK ---")
        if not an.presets:
            L.append("Tidak ada preset yang namanya cocok dengan efek yang di-rename.")
        for f, inst in an.presets:
            L.append('- %s  (cocok dengan efek "%s")' % (f, inst))
        L.append("")

    copied = sum(1 for cd in chosen if cd.ok)
    unchecked = sum(1 for cd in an.candidates if not cd.selected)
    L.append("Total: %d efek plugin pihak ketiga dipakai -> %d file plugin dicopy%s, %d tidak ketemu." % (
        len(groups["plugin"]), copied, (", %d tidak dicentang" % unchecked) if unchecked else "", not_found))
    L.append("")
    return L


def how_to_use() -> List[str]:
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
        "   Plugin berbayar (Boris FX, Red Giant/Maxon, Video Copilot, dll.) tetap butuh installer +",
        "   lisensi resmi di komputer tujuan; file .aex-nya saja biasanya tidak cukup.",
        "3. (PresetEffects): ikuti petunjuk di dalam file XML-nya.",
        "4. (Presets): copy file .ffx ke Documents\\Adobe\\After Effects <versi>\\User Presets.",
        "5. Buka file .aep di folder ini. Path footage sudah diarahkan ke folder (Footage);",
        "   kalau folder hasil dipindah, AE tetap bisa menemukannya lewat path relatif.",
        "",
    ]


def effect_rows(an: "Analysis") -> List[List[str]]:
    rows = [["Comp", "Layer", "Nama efek di layer", "Nama efek asli", "Match name", "Jenis",
             "Status", "File plugin", "Efek aktif"]]
    for e in an.effects:
        _tag, status = effect_status(e)
        plugin = str(e.match.plugin.target) if e.match is not None else ""
        for u in e.group.uses:
            rows.append([u.comp, "#%d %s" % (u.layer_index, u.layer_name), u.instance, e.display,
                         e.match_name, KIND_LABEL[e.kind], status, plugin, "ya" if u.enabled else "tidak"])
    for e in an.disabled_all:
        for u in e.group.uses:
            rows.append([u.comp, "#%d %s" % (u.layer_index, u.layer_name), u.instance, e.display,
                         e.match_name, KIND_LABEL[e.kind], "dimatikan, tidak dikumpulkan", "", "tidak"])
    return rows


def write_csv(path: Path, rows: Sequence[Sequence[str]]) -> None:
    """CSV UTF-16LE + BOM, dipisah tab: Excel membukanya rapi per kolom
    di setting regional apa pun."""

    def cell(v: str) -> str:
        v = " ".join(str(v).replace("\t", " ").splitlines())
        return '"' + v.replace('"', '""') + '"'

    text = "\r\n".join("\t".join(cell(c) for c in r) for r in rows) + "\r\n"
    path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
