"""Membaca isi file .aep (tanpa After Effects) lewat library py_aep."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import py_aep
from py_aep.binary.utils import (
    PENDING_ASCENDCOUNT,
    alas_platform,
    dump_alas,
    find_by_list_type,
    find_by_type,
)
from py_aep.models.items.composition import CompItem
from py_aep.models.items.footage import FootageItem
from py_aep.models.sources.file import FileSource


@dataclass
class EffectUse:
    comp: str
    layer_index: int  # 1 = layer paling atas (seperti di AE)
    layer_name: str
    instance: str     # nama efek di layer (bisa di-rename)
    enabled: bool


@dataclass
class EffectGroup:
    """Semua pemakaian satu efek (dikelompokkan per match name)."""

    match_name: str
    uses: List[EffectUse] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.uses)

    @property
    def names(self) -> List[str]:
        out: List[str] = []
        for u in self.uses:
            if u.instance not in out:
                out.append(u.instance)
        return out


@dataclass
class FootageRef:
    """Satu sumber file (main source atau proxy) dari sebuah footage item."""

    item: FootageItem
    role: str              # "main" / "proxy"
    source: FileSource
    path: str              # file (frame pertama untuk image sequence)
    is_sequence: bool
    frames: List[str]      # nama file frame kalau tersimpan di .aep

    @property
    def folder(self) -> str:
        return os.path.dirname(self.path)


class AepProject:
    def __init__(self, path: os.PathLike):
        self.path = Path(path)
        self.app = py_aep.parse(str(self.path))
        self.project = self.app.project

    # ----------------------------------------------------------- comp

    @property
    def comps(self) -> List[CompItem]:
        return list(self.project.compositions)

    def rq_comps(self) -> List[CompItem]:
        out: List[CompItem] = []
        try:
            for rqi in self.project.render_queue.items:
                c = getattr(rqi, "comp", None)
                if isinstance(c, CompItem) and c not in out:
                    out.append(c)
        except Exception:
            pass
        return out

    def active_comp(self) -> Optional[CompItem]:
        try:
            item = self.project.active_item
        except Exception:
            return None
        return item if isinstance(item, CompItem) else None

    def default_roots(self) -> Tuple[str, List[CompItem]]:
        """Pilihan comp awal: Render Queue > comp aktif > semua comp."""
        rq = self.rq_comps()
        if rq:
            return "rq", rq
        act = self.active_comp()
        if act is not None:
            return "active", [act]
        return "all", self.comps

    @staticmethod
    def layer_source(layer) -> object:
        try:
            return layer.source
        except Exception:
            return None

    def expand(self, roots: Sequence[CompItem]) -> List[CompItem]:
        """Comp akar + semua precomp di dalamnya."""
        out: List[CompItem] = []
        seen = set()

        def visit(c: CompItem) -> None:
            if c.id in seen:
                return
            seen.add(c.id)
            out.append(c)
            for layer in c.layers:
                src = self.layer_source(layer)
                if isinstance(src, CompItem):
                    visit(src)

        for r in roots:
            visit(r)
        return out

    def precomp_users(self) -> Dict[int, int]:
        """Berapa comp lain yang memakai comp ini sebagai precomp."""
        users: Dict[int, int] = {}
        for c in self.comps:
            for layer in c.layers:
                src = self.layer_source(layer)
                if isinstance(src, CompItem):
                    users[src.id] = users.get(src.id, 0) + 1
        return users

    # ---------------------------------------------------------- efek

    def effects(self, comps: Sequence[CompItem], skip_disabled: bool) -> Tuple[List[EffectGroup], List[EffectGroup]]:
        """(efek dipakai, efek yang dimatikan) di comp-comp ini."""
        used: Dict[str, EffectGroup] = {}
        off: Dict[str, EffectGroup] = {}
        for c in comps:
            for layer in c.layers:
                try:
                    effects = list(layer.effects)
                except Exception:
                    continue
                for e in effects:
                    try:
                        mn = str(e.match_name)
                        inst = str(e.name)
                    except Exception:
                        continue
                    try:
                        on = e.enabled is not False
                    except Exception:
                        on = True
                    use = EffectUse(c.name, int(layer.index) + 1, str(layer.name), inst, on)
                    target = off if (skip_disabled and not on) else used
                    target.setdefault(mn, EffectGroup(mn)).uses.append(use)
        return list(used.values()), list(off.values())

    # ---------------------------------------------------------- font

    def fonts(self, comps: Optional[Sequence[CompItem]] = None) -> List[str]:
        """PostScript name font yang dipakai text layer (di comp-comp ini)."""
        layer_ids = None
        if comps is not None:
            layer_ids = set()
            for c in comps:
                for layer in c.layers:
                    try:
                        layer_ids.add(int(layer.id))
                    except Exception:
                        pass
        out: List[str] = []
        try:
            used = self.project.used_fonts
        except Exception:
            used = []
        for entry in used:
            try:
                ps = entry["font"].post_script_name
                at = entry.get("used_at") or []
            except Exception:
                continue
            if layer_ids is not None and at:
                if not any(int(r.get("layer_id", -1)) in layer_ids for r in at):
                    continue
            if ps and ps not in out:
                out.append(ps)
        return out

    # ------------------------------------------------------- footage

    def footage(self, only_used_by: Optional[Sequence[CompItem]] = None) -> List[FootageRef]:
        """Semua sumber file footage (main + proxy).

        only_used_by: kalau diisi, hanya footage yang dipakai comp-comp itu.
        """
        allowed = None
        if only_used_by is not None:
            allowed = set()
            for c in only_used_by:
                for layer in c.layers:
                    src = self.layer_source(layer)
                    if isinstance(src, FootageItem):
                        allowed.add(src.id)
        refs: List[FootageRef] = []
        for item in self.project.footages:
            if allowed is not None and item.id not in allowed:
                continue
            for role, src in (("main", getattr(item, "main_source", None)),
                              ("proxy", getattr(item, "proxy_source", None))):
                if not isinstance(src, FileSource):
                    continue
                path = src.file or ""
                if not path:
                    continue
                try:
                    frames = list(src.file_names or [])
                except Exception:
                    frames = []
                is_seq = bool(frames) or bool(getattr(src, "target_is_folder", False))
                refs.append(FootageRef(item, role, src, path, is_seq, frames))
        return refs

    @staticmethod
    def relink(ref: FootageRef, new_path: str) -> None:
        """Ganti path di record `alas` saja (isi media tidak diproses ulang).

        Untuk image sequence, path-nya adalah folder sequence. Hitungan path
        relatif diisi ulang oleh py_aep saat project disimpan, sesuai lokasi
        project yang baru.
        """
        pin = ref.source._pin  # LIST:Pin  milik FileSource
        als2 = find_by_list_type(chunks=pin.chunks, list_type="Als2")
        alas = find_by_type(chunks=als2.chunks, chunk_type="alas")
        data = json.loads(alas.value) if alas.value else {}
        full = os.path.dirname(new_path) if ref.is_sequence else new_path
        data["fullpath"] = full
        data["platform"] = alas_platform(full)
        data["ascendcount_base"] = PENDING_ASCENDCOUNT
        data["ascendcount_target"] = PENDING_ASCENDCOUNT
        data.setdefault("server_name", "")
        data.setdefault("server_volume_name", "")
        data["target_is_folder"] = bool(ref.is_sequence and data.get("target_is_folder", ref.is_sequence))
        alas.value = dump_alas(data)
        ref.source._file = new_path

    def reduce(self, roots: Sequence[CompItem]) -> int:
        return int(self.project.reduce_project(list(roots)))

    def save(self, path: os.PathLike) -> None:
        self.project.save(path)


def sequence_frames(first_frame: Path) -> List[Path]:
    """Semua frame yang polanya sama dengan frame pertama (nama_0001.png ...)."""
    m = re.match(r"^(.*?)(\d+)(\.[^.]+)$", first_frame.name)
    if not m or not first_frame.parent.is_dir():
        return [first_frame]
    prefix, ext = m.group(1), m.group(3).lower()
    out = []
    for f in sorted(first_frame.parent.iterdir()):
        mm = re.match(r"^(.*?)(\d+)(\.[^.]+)$", f.name)
        if f.is_file() and mm and mm.group(1) == prefix and mm.group(3).lower() == ext:
            out.append(f)
    return out or [first_frame]
