"""Laporan teks + CSV daftar efek."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple

from . import __version__
from .i18n import N_, _
from .plugins import CERTAIN_HOW, how_label

if TYPE_CHECKING:
    from .collector import Analysis, EffectInfo, Result

KIND_LABEL = {
    "plugin": N_("Plugin pihak ketiga"),
    "builtin": N_("Bawaan After Effects"),
    "pseudo": N_("Pseudo effect"),
    "presetxml": N_("PresetEffects.xml"),
}


def kind_label(kind: str) -> str:
    return _(KIND_LABEL.get(kind, kind))


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


def effect_status_key(e: "EffectInfo") -> str:
    if e.kind in ("builtin", "pseudo", "presetxml"):
        return e.kind
    cd = e.candidate
    if cd is not None:
        if cd.selected:
            if cd.ok is False:
                return "copy_failed"
            if cd.ok is None:
                return "selected"
            if e.match is not None and e.match.how in CERTAIN_HOW:
                return "ok"
            return "ok_check"
        return "unchecked" if cd.strict else "guess"
    return "not_found"


_STATUS = {
    "builtin": ("", N_("bawaan AE")),
    "pseudo": ("", N_("tersimpan di project")),
    "presetxml": ("", N_("definisi XML diekspor")),
    "copy_failed": (N_("[GAGAL COPY]"), N_("gagal copy")),
    "selected": (N_("[DIPILIH]"), N_("akan dicopy")),
    "ok": ("[OK]", N_("dicopy")),
    "ok_check": (N_("[OK, CEK MANUAL]"), N_("dicopy (cek manual)")),
    "unchecked": (N_("[TIDAK DICOPY]"), N_("tidak dicopy (centang dihapus)")),
    "guess": (N_("[PERKIRAAN, TIDAK DICOPY]"), N_("perkiraan, tidak dicopy")),
    "not_found": (N_("[TIDAK KETEMU]"), N_("file plugin tidak ketemu")),
}


def effect_status(e: "EffectInfo") -> Tuple[str, str]:
    """(tag laporan, status CSV)."""
    tag, status = _STATUS[effect_status_key(e)]
    return (_(tag) if tag else ""), _(status)


def scope_text(an: "Analysis") -> str:
    if an.options.scope_label:
        return an.options.scope_label
    if an.options.comp_ids is None:
        return _("semua comp di project (%d comp)") % len(an.comps)
    names = [c.name for c in an.roots[:8]]
    extra = len(an.comps) - len(an.roots)
    text = ", ".join(names) + (" ..." if len(an.roots) > 8 else "")
    return text + (_("  (+%d precomp di dalamnya)") % extra if extra > 0 else "")


RULE = "=" * 72


def build_report(an: "Analysis", res: Optional["Result"] = None) -> List[str]:
    """Laporan: ringkasan dulu (yang beres / yang perlu dicek), lalu cara pakai, lalu rincian."""
    import py_aep

    L: List[str] = []
    L.append(_("Collect Files Plus - laporan"))
    L.append(RULE)
    L.append(_("Project asal : %s") % an.aep.path)
    if res is not None:
        L.append(_("Folder hasil : %s") % res.dest_root)
    L.append(_("Comp dibaca  : %s") % scope_text(an))
    L.append(_("Tanggal      : %s") % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    L.append(_("Versi        : Collect Files Plus %s (py_aep %s)") % (__version__, getattr(py_aep, "__version__", "?")))
    L.append("")
    L.extend(summary_lines(an, res))
    L.extend(how_to_use())
    L.append(RULE)
    L.append(_("RINCIAN"))
    L.append(RULE)
    L.append("")

    if res is not None and res.errors:
        for err in res.errors:
            L.append("[ERROR] " + err)
        L.append("")

    opt = an.options
    if opt.collect_footage:
        L.append(_("=== FOOTAGE ==="))
        if res is not None and res.reduced >= 0:
            L.append(_("Reduce Project: %d item yang tidak dipakai dibuang dari project hasil.") % res.reduced)
        ok = missing = failed = 0
        total = 0
        for fe in an.footage:
            names = ", ".join(fe.names)
            extra = _("  (sequence, %d frame)") % len(fe.files) if fe.is_sequence else ""
            if fe.extras:
                extra += _("  (+%d file pendukung model 3D)") % len(fe.extras)
            if not fe.exists:
                missing += 1
                L.append(_("[HILANG]  %s  ->  %s") % (names, fe.src))
            elif fe.copied is False:
                failed += 1
                L.append(_("[GAGAL]   %s  ->  %s  (%s)") % (names, fe.src, fe.error))
            else:
                ok += 1
                total += fe.size
                tag = "[OK]     " if fe.copied else _("[DIPILIH]")
                L.append("%s %s  <-  %s  (%s)%s" % (tag, names, fe.src, fmt_bytes(fe.size), extra))
        if not an.footage:
            L.append(_("Tidak ada footage file."))
        L.append(_("Total: %d file/sequence (%s), %d hilang, %d gagal.") % (ok, fmt_bytes(total), missing, failed))
        L.append("")

    if opt.collect_fonts:
        L.append(_("=== FONT ==="))
        if not an.fonts:
            L.append(_("Tidak ada font yang dipakai."))
        n_ok = 0
        for f in an.fonts:
            if f.face is not None:
                n_ok += 1 if f.copied is not False else 0
                tag = "[OK]     " if f.copied else (_("[GAGAL]  ") if f.copied is False else _("[DIPILIH]"))
                L.append("%s %s  [%s %s]  <-  %s" % (tag, f.post_script_name, f.face.family, f.face.style, f.face.path))
            elif f.status == "adobe":
                L.append(_("[ADOBE FONTS] %s  -> aktifkan lewat Creative Cloud di komputer tujuan") % f.post_script_name)
            else:
                L.append(_("[TIDAK KETEMU] %s  -> tidak terinstall di komputer ini (atau dari Adobe Fonts)")
                         % f.post_script_name)
        L.append(_("Total: %d font dipakai, %d ada file-nya.") % (len(an.fonts), n_ok))
        L.append("")

    L.extend(_effects_section(an))
    return L


def _item(L: List[str], tag: str, text: str, hint: str = "") -> None:
    L.append("%-4s %s" % (tag, text))
    if hint:
        L.append("     -> " + hint)


def summary_lines(an: "Analysis", res: Optional["Result"] = None) -> List[str]:
    """Ringkasan di awal laporan. [OK] = beres, [!] = perlu dicek, [i] = info."""
    done = res is not None
    opt = an.options
    L: List[str] = [_("=== RINGKASAN ==="), _("[OK] = beres   [!] = perlu dicek   [i] = info"), ""]

    if done and not res.saved_ok:
        _item(L, "[!]", _("!!! PERHATIAN: %s") % res.validation_error,
              _("!!! Pakai project di folder (Backup) lalu relink footage ke folder (Footage)."))
    elif done and res.project_out is not None and res.backup is not None:
        _item(L, "[OK]", _("Project hasil collect: %s (sudah di-relink ke folder (Footage)).") % res.project_out.name)
        _item(L, "[i]", _("Cadangan project asli (belum diubah): (Backup)/%s") % res.backup.name)
    elif done and res.project_out is not None:
        _item(L, "[OK]", _("Project: %s (salinan project asli, tidak ada yang perlu diubah).") % res.project_out.name)
    if done and res.errors:
        _item(L, "[!]", _("%d error saat collect, lihat [ERROR] di bagian RINCIAN.") % len(res.errors))

    if opt.collect_footage:
        ok = [fe for fe in an.footage if fe.exists and fe.copied is not False]
        missing = sum(1 for fe in an.footage if not fe.exists)
        failed = sum(1 for fe in an.footage if fe.exists and fe.copied is False)
        if not an.footage:
            _item(L, "[OK]", _("Footage: tidak ada file footage."))
        elif ok:
            size = fmt_bytes(sum(fe.size for fe in ok))
            _item(L, "[OK]", (_("Footage: %d file/sequence dicopy ke (Footage), total %s.") if done else
                              _("Footage: %d file/sequence akan dicopy, total %s.")) % (len(ok), size))
        if missing:
            _item(L, "[!]", _("Footage: %d file hilang (tidak ada di komputer ini).") % missing,
                  _("Cari file aslinya, lalu relink di After Effects. Daftarnya: [HILANG] di bagian FOOTAGE."))
        if failed:
            _item(L, "[!]", _("Footage: %d file gagal dicopy.") % failed, _("Lihat [GAGAL] di bagian FOOTAGE."))
        if done and res.reduced > 0:
            _item(L, "[i]", _("Reduce Project: %d item yang tidak dipakai dibuang dari project hasil.") % res.reduced)

    if opt.collect_fonts:
        found = [f for f in an.fonts if f.face is not None and f.copied is not False]
        failed = sum(1 for f in an.fonts if f.face is not None and f.copied is False)
        adobe = sum(1 for f in an.fonts if f.face is None and f.status == "adobe")
        lost = sum(1 for f in an.fonts if f.face is None and f.status != "adobe")
        if not an.fonts:
            _item(L, "[OK]", _("Font: tidak ada font yang dipakai."))
        elif found:
            _item(L, "[OK]", (_("Font: %d font dicopy ke (Fonts).") if done else _("Font: %d font akan dicopy."))
                  % len(found))
        if lost:
            _item(L, "[!]", _("Font: %d font tidak ketemu di komputer ini.") % lost,
                  _("Install font itu di komputer tujuan. Daftarnya: [TIDAK KETEMU] di bagian FONT."))
        if adobe:
            _item(L, "[i]", _("Font: %d Adobe Fonts tidak dicopy.") % adobe,
                  _("Aktifkan lewat aplikasi Creative Cloud di komputer tujuan."))
        if failed:
            _item(L, "[!]", _("Font: %d font gagal dicopy.") % failed)

    if opt.collect_plugins:
        fx = [e for e in an.effects if e.kind == "plugin"]
        keys = [effect_status_key(e) for e in fx]
        chosen = [cd for cd in an.candidates if cd.selected and cd.ok is not False]
        covered = sum(1 for k in keys if k in ("ok", "ok_check", "selected"))
        if not fx:
            _item(L, "[OK]", _("Plugin: tidak ada efek plugin pihak ketiga yang dipakai."))
        elif chosen:
            _item(L, "[OK]", (_("Plugin: %d file plugin dicopy ke (Plugins), untuk %d efek.") if done else
                              _("Plugin: %d file plugin akan dicopy, untuk %d efek.")) % (len(chosen), covered))
        if keys.count("not_found"):
            _item(L, "[!]", _("Plugin: %d efek plugin tidak ketemu di komputer ini.") % keys.count("not_found"),
                  _("Install plugin itu di komputer tujuan. Daftarnya: [TIDAK KETEMU] di bagian EFEK & PLUGIN."))
        guesses = sum(1 for cd in an.candidates if not cd.selected and not cd.strict)
        if guesses:
            _item(L, "[!]", _("Plugin: %d file plugin perkiraan tidak dicopy.") % guesses,
                  _("Cek [PERKIRAAN, TIDAK DICOPY] di bagian EFEK & PLUGIN; centang di aplikasi kalau memang benar."))
        if keys.count("ok_check"):
            _item(L, "[!]", _("Plugin: %d efek perlu dicek manual.") % keys.count("ok_check"),
                  _("Lihat [OK, CEK MANUAL] di bagian EFEK & PLUGIN."))
        unticked = sum(1 for cd in an.candidates if not cd.selected and cd.strict)
        if unticked:
            _item(L, "[i]", _("Plugin: %d file plugin tidak dicopy karena centangnya dihapus.") % unticked)
        failed = sum(1 for cd in an.candidates if cd.selected and cd.ok is False)
        if failed:
            _item(L, "[!]", _("Plugin: %d file plugin gagal dicopy.") % failed)
        if chosen:
            _item(L, "[i]", _("Plugin berbayar tetap butuh installer + lisensi resmi di komputer tujuan."))

    if not any(line.startswith("[!]") for line in L):
        L.append("")
        _item(L, "[OK]", _("Tidak ada yang perlu dicek."))
    L.append("")
    return L


def _effects_section(an: "Analysis") -> List[str]:
    L: List[str] = []
    groups = {"plugin": [], "presetxml": [], "pseudo": [], "builtin": []}  # type: dict
    for e in an.effects:
        groups[e.kind].append(e)
    uses = sum(e.count for e in an.effects)
    L.append(_("=== EFEK & PLUGIN ==="))
    L.append(_("Terbaca          : %d pemakaian efek, %d jenis efek%s.") % (
        uses, len(an.effects),
        _("  (%d pemakaian efek yang dimatikan dilewati)") % an.disabled_uses if an.disabled_uses else ""))
    L.append(_("Efek plugin pihak ketiga: %d  |  Bawaan AE: %d  |  Pseudo effect: %d  |  PresetEffects.xml: %d") % (
        len(groups["plugin"]), len(groups["builtin"]), len(groups["pseudo"]), len(groups["presetxml"])))
    L.append(_("Yang dicopy hanya FILE plugin yang berisi efek di atas, bukan seluruh folder plugin."))
    L.append(_("Daftar lengkap per comp & layer ada di file *_daftar_efek.csv."))
    for note in an.notes:
        L.append("(%s)" % _(note))
    L.append("")

    L.append(_("--- PLUGIN PIHAK KETIGA ---"))
    if not groups["plugin"]:
        L.append(_("Tidak ada."))
    not_found = 0
    for e in groups["plugin"]:
        tag, _csv = effect_status(e)
        if effect_status_key(e) == "not_found":
            not_found += 1
        L.append("%s %s" % (tag, effect_title(e)))
        if e.category:
            L.append(_("     kategori      : %s") % e.category)
        L.append(_("     nama di layer : %s") % ", ".join(e.names))
        L.append(_("     dipakai %dx    : %s") % (e.count, uses_text(e)))
        if e.match is not None:
            L.append(_("     file plugin   : %s") % e.match.plugin.target)
            if e.match.how != "pipl":
                L.append(_("     cara ketemu   : %s -> pastikan file ini memang plugin-nya") % how_label(e.match.how))
            cd = e.candidate
            if cd is not None and cd.selected and cd.ok:
                L.append(_("     dicopy ke     : (Plugins)/%s") % cd.dest_rel)
            elif cd is not None and not cd.selected:
                L.append(_("     catatan       : %s") % (
                    _("tidak dicopy karena centangnya dihapus") if cd.strict else
                    _("tidak dicopy otomatis karena hanya perkiraan; centang di daftar kalau memang benar")))
            if e.match.plugin.root.is_app:
                L.append(_("     catatan       : file ini ada di folder plugin After Effects sendiri"))
        else:
            L.append(_("     catatan       : plugin ini tidak ada di komputer ini, atau file-nya di luar "
                       "folder plugin yang dimuat AE"))
    L.append("")

    L.append(_("--- FILE PLUGIN YANG DICOPY ---"))
    chosen = [cd for cd in an.candidates if cd.selected]
    if not chosen:
        L.append(_("Tidak ada."))
    for cd in chosen:
        tag = "- " if cd.ok is not False else "- " + _("[GAGAL]") + " "
        L.append("%s%s  (%s)" % (tag, cd.label, fmt_bytes(cd.size)))
        L.append(_("     efek dipakai  : %s") % ", ".join(e.title for e in cd.effects))
        if cd.others:
            L.append(_("     catatan       : file ini juga berisi %d efek lain yang tidak dipakai "
                       "(satu file, tidak bisa dipisah)") % cd.others)
        if cd.support:
            L.append(_("     file pendukung: %d file/folder ikut dicopy") % len(cd.support))
    L.append("")

    if groups["presetxml"]:
        L.append(_("--- EFEK DARI PresetEffects.xml ---"))
        for e in groups["presetxml"]:
            L.append("[XML] %s" % effect_title(e))
            L.append(_("     nama di layer : %s") % ", ".join(e.names))
            L.append(_("     dipakai %dx    : %s") % (e.count, uses_text(e)))
        L.append(_("Definisinya diekspor ke (PresetEffects)/PresetEffects_dari_project.xml."))
        L.append("")

    if groups["pseudo"]:
        L.append(_("--- PSEUDO EFFECT (sudah tersimpan di dalam project, tidak perlu dicopy) ---"))
        for e in groups["pseudo"]:
            L.append("[PSEUDO] %s%s" % (effect_title(e), _("  (definisi ikut diekspor)") if e.xml_block else ""))
            L.append(_("     nama di layer : %s") % ", ".join(e.names))
            L.append(_("     dipakai %dx    : %s") % (e.count, uses_text(e)))
        L.append("")

    L.append(_("--- EFEK BAWAAN AFTER EFFECTS (tidak perlu dicopy) ---"))
    if not groups["builtin"]:
        L.append(_("Tidak ada."))
    for e in groups["builtin"]:
        L.append(_("- %s  %dx  | nama di layer: %s") % (effect_title(e), e.count, ", ".join(e.names)))
    L.append("")

    if an.disabled_only:
        L.append(_("--- EFEK YANG DIMATIKAN (ikon fx mati, tidak dikumpulkan) ---"))
        for e in an.disabled_only:
            L.append(_("[DIMATIKAN] %s  (%s)") % (effect_title(e), kind_label(e.kind)))
            L.append(_("     nama di layer : %s") % ", ".join(e.names))
            L.append(_("     di            : %s") % uses_text(e))
        L.append(_("Kalau plugin efek ini tidak ada di komputer tujuan, AE tetap memberi peringatan"))
        L.append(_('"missing" saat project dibuka, tapi hasil render tidak berubah.'))
        L.append("")

    if an.options.presets:
        L.append(_("--- ANIMATION PRESET (.ffx) YANG NAMANYA COCOK ---"))
        if not an.presets:
            L.append(_("Tidak ada preset yang namanya cocok dengan efek yang di-rename."))
        for f, inst in an.presets:
            L.append(_('- %s  (cocok dengan efek "%s")') % (f, inst))
        L.append("")

    copied = sum(1 for cd in chosen if cd.ok)
    unchecked = sum(1 for cd in an.candidates if not cd.selected)
    L.append(_("Total: %d efek plugin pihak ketiga dipakai -> %d file plugin dicopy%s, %d tidak ketemu.") % (
        len(groups["plugin"]), copied, (_(", %d tidak dicentang") % unchecked) if unchecked else "", not_found))
    L.append("")
    return L


def how_to_use() -> List[str]:
    return [
        _("=== CARA PAKAI DI KOMPUTER LAIN ==="),
        _("1. Font: install semua file di (Fonts) sebelum membuka project."),
        _("   Windows: pilih semua > klik kanan > Install for all users.  Mac: buka dengan Font Book."),
        _("   Font [ADOBE FONTS] cukup diaktifkan dari aplikasi Creative Cloud."),
        _("2. Plugin: tutup After Effects dulu, lalu copy isi:"),
        "   (Plugins)/MediaCore    ->  Windows: C:\\Program Files\\Adobe\\Common\\Plug-ins\\7.0\\MediaCore",
        "                              Mac: /Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore",
        _("   (Plugins)/AE Plug-ins  ->  Windows: C:\\Program Files\\Adobe\\Adobe After Effects <versi>\\Support "
          "Files\\Plug-ins"),
        _("                              Mac: /Applications/Adobe After Effects <versi>/Plug-ins"),
        _("   (Plugins)/Lainnya      ->  lokasi aslinya tercatat di laporan (baris \"file plugin\")."),
        _("   Lewati plugin yang sudah terinstall supaya tidak dobel."),
        _("   .aex hanya jalan di Windows, .plugin hanya jalan di Mac."),
        _("   Plugin berbayar (Boris FX, Red Giant/Maxon, Video Copilot, dll.) tetap butuh installer +"),
        _("   lisensi resmi di komputer tujuan; file .aex-nya saja biasanya tidak cukup."),
        _("3. (PresetEffects): ikuti petunjuk di dalam file XML-nya."),
        _("4. (Presets): copy file .ffx ke Documents\\Adobe\\After Effects <versi>\\User Presets."),
        _("5. Buka file .aep di folder ini. Path footage sudah diarahkan ke folder (Footage);"),
        _("   kalau folder hasil dipindah, AE tetap bisa menemukannya lewat path relatif."),
        "",
    ]


def effect_rows(an: "Analysis") -> List[List[str]]:
    rows = [[_("Comp"), _("Layer"), _("Nama efek di layer"), _("Nama efek asli"), _("Match name"), _("Jenis"),
             _("Status"), _("File plugin"), _("Efek aktif")]]
    yes, no = _("ya"), _("tidak")
    for e in an.effects:
        _tag, status = effect_status(e)
        plugin = str(e.match.plugin.target) if e.match is not None else ""
        for u in e.group.uses:
            rows.append([u.comp, "#%d %s" % (u.layer_index, u.layer_name), u.instance, e.display,
                         e.match_name, kind_label(e.kind), status, plugin, yes if u.enabled else no])
    for e in an.disabled_all:
        for u in e.group.uses:
            rows.append([u.comp, "#%d %s" % (u.layer_index, u.layer_name), u.instance, e.display,
                         e.match_name, kind_label(e.kind), _("dimatikan, tidak dikumpulkan"), "", no])
    return rows


def write_csv(path: Path, rows: Sequence[Sequence[str]]) -> None:
    """CSV UTF-16LE + BOM, dipisah tab: Excel membukanya rapi per kolom
    di setting regional apa pun."""

    def cell(v: str) -> str:
        v = " ".join(str(v).replace("\t", " ").splitlines())
        return '"' + v.replace('"', '""') + '"'

    text = "\r\n".join("\t".join(cell(c) for c in r) for r in rows) + "\r\n"
    path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
