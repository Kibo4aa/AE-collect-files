"""Collect banyak project sekaligus."""

from pathlib import Path

import pytest

from collect_files_plus import plugins
from collect_files_plus.batch import collect_many, find_projects, resolve_scope
from collect_files_plus.collector import Options, analyze
from collect_files_plus.plugins import PluginRoot
from collect_files_plus.project import AepProject
from helpers import DATA, env_for, files_under, make_fx_project, make_plugin_tree, make_project, make_ttf


def test_find_projects_skips_autosave_and_results(tmp_path: Path):
    def touch(rel):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        return p

    a = touch("Edit/AMV 1.aep")
    b = touch("Edit/Sub/AMV 2.AEP")
    touch("Edit/Adobe After Effects Auto-Save/AMV 1 auto-save 1.aep")
    touch("Edit/AMV 1_Collected/AMV 1.aep")
    touch("Edit/AMV 1_Collected (2)/(Backup)/AMV 1.aep")
    touch("Edit/catatan.txt")
    single = touch("Lain/Satu.aep")
    found = find_projects([tmp_path / "Edit", single, a, tmp_path / "tidak-ada"])
    assert found == [a, b, single]          # urut, tanpa duplikat


def test_resolve_scope_modes():
    aep = AepProject(DATA / "Item-01.aep")    # 2 comp, comp aktif "Comp 01", Render Queue kosong
    ids = {c.name: c.id for c in aep.comps}
    assert resolve_scope(aep, "auto") == ([ids["Comp 01"]], "comp aktif: Comp 01")
    assert resolve_scope(aep, "all") == (None, "semua comp (2)")
    assert resolve_scope(aep, "names", ["Comp 02"]) == ([ids["Comp 02"]], "comp: Comp 02")
    assert resolve_scope(aep, "active")[0] == [ids["Comp 01"]]
    with pytest.raises(ValueError, match="Render Queue kosong"):
        resolve_scope(aep, "rq")
    with pytest.raises(ValueError, match="Tidak Ada"):
        resolve_scope(aep, "names", ["Tidak Ada"])


def test_collect_many_mixed(tmp_path: Path):
    p1 = make_project(tmp_path / "A")
    p2 = make_project(tmp_path / "B")             # nama file sama dengan p1
    bad = tmp_path / "C" / "rusak.aep"
    bad.parent.mkdir()
    bad.write_bytes(b"bukan project")
    mc = make_plugin_tree(tmp_path)
    fx = make_fx_project(tmp_path)
    fonts = tmp_path / "fonts"
    make_ttf(fonts / "Myriad.ttf", "Myriad Pro", "Regular", "MyriadPro-Regular")
    make_ttf(fonts / "Britannic.ttf", "Britannic Bold", "Regular", "BritannicBold")
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)], font_dirs=[fonts])
    dest = tmp_path / "out"
    seen = []
    run = collect_many([p1, bad, p2, fx], Options(dest_dir=dest), "auto", env=env,
                       on_item=lambda i, it: seen.append((i, it.status)))

    assert [it.status for it in run.items] == ["catatan", "gagal", "catatan", "ok"]
    assert run.items[0].notes == ["1 footage hilang"]
    assert run.items[1].error and run.items[1].result is None
    assert run.items[0].scope == "semua comp (3)"
    assert run.items[3].scope == "comp aktif: Comp 01"
    assert (0, "jalan") in seen and (1, "gagal") in seen and (3, "ok") in seen
    assert not run.ok
    assert run.headline() == "1 OK, 2 ada catatan, 1 gagal (dari 4 project)"

    names = sorted(d.name for d in dest.iterdir() if d.is_dir())
    assert names == ["Efek_Collected", "Proyek Saya_Collected", "Proyek Saya_Collected (2)"]
    assert (dest / "Proyek Saya_Collected" / "(Footage)" / "Render" / "shot_0005.png").is_file()
    plug = [f for f in files_under(dest / "Efek_Collected") if f.startswith("(Plugins)/")]
    assert plug == ["(Plugins)/MediaCore/BorisFX/Continuum/BCC_Blur.aex",
                    "(Plugins)/MediaCore/Deep Glow.aex", "(Plugins)/MediaCore/VendorA/Kaca.aex"]

    assert run.summary is not None and run.summary.parent == dest
    text = run.summary.read_text(encoding="utf-8")
    assert "[GAGAL]      rusak.aep" in text and "[OK]         Efek.aep" in text
    assert "Proyek Saya_Collected (2)" in text and "1 footage hilang" in text


def test_collect_many_cancel_before_start(tmp_path: Path):
    import threading
    p1 = make_project(tmp_path / "A")
    cancel = threading.Event()
    cancel.set()
    run = collect_many([p1], Options(dest_dir=tmp_path / "out"), env=env_for(tmp_path), cancel=cancel)
    assert [it.status for it in run.items] == ["dibatalkan"]
    assert run.summary is None and not (tmp_path / "out").exists()


def test_pipl_read_once_per_file(tmp_path: Path, monkeypatch):
    """Batch/analisa ulang tidak membaca PiPL file plugin yang sama berkali-kali."""
    plugins._ENTRY_CACHE.clear()
    calls = []
    real = plugins.read_plugin_pipl
    monkeypatch.setattr(plugins, "read_plugin_pipl", lambda t, r: calls.append(t) or real(t, r))
    mc = make_plugin_tree(tmp_path)
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)])
    aep = AepProject(make_fx_project(tmp_path))
    first = analyze(aep, Options(dest_dir=tmp_path / "o"), env)
    n = len(calls)
    assert n > 0
    second = analyze(aep, Options(dest_dir=tmp_path / "o"), env)
    assert len(calls) == n
    assert sorted(c.label for c in first.candidates) == sorted(c.label for c in second.candidates)


def test_pipl_cache_on_disk(tmp_path: Path, monkeypatch):
    """Isi PiPL disimpan di disk: aplikasi yang dibuka lagi tidak membaca ulang file plugin yang sama."""
    import os
    mc = make_plugin_tree(tmp_path)
    env = env_for(tmp_path, plugin_roots=[PluginRoot(mc, "MediaCore", 1)])
    aep = AepProject(make_fx_project(tmp_path))
    first = analyze(aep, Options(dest_dir=tmp_path / "o"), env)
    cache = plugins.entry_cache_path()
    assert cache.is_file() and cache.parent == Path(os.environ["COLLECT_FILES_PLUS_CACHE_DIR"])

    plugins._ENTRY_CACHE.clear()                      # seperti aplikasi baru dibuka
    plugins._DISK.update(loaded=False, dirty=False)
    calls = []
    real = plugins.read_plugin_pipl
    monkeypatch.setattr(plugins, "read_plugin_pipl", lambda t, r: calls.append(t.name) or real(t, r))
    second = analyze(aep, Options(dest_dir=tmp_path / "o"), env)
    assert calls == []
    assert sorted(c.label for c in first.candidates) == sorted(c.label for c in second.candidates)

    blur = mc / "BorisFX" / "Continuum" / "BCC_Blur.aex"
    blur.write_bytes(blur.read_bytes() + b"\0")       # file berubah -> dibaca ulang, yang lain tetap dari cache
    plugins._ENTRY_CACHE.clear()
    plugins._DISK.update(loaded=False, dirty=False)
    analyze(aep, Options(dest_dir=tmp_path / "o"), env)
    assert calls == ["BCC_Blur.aex"]

    cache.write_text("rusak", encoding="utf-8")       # cache rusak diabaikan
    plugins._ENTRY_CACHE.clear()
    plugins._DISK.update(loaded=False, dirty=False)
    third = analyze(aep, Options(dest_dir=tmp_path / "o"), env)
    assert len(third.candidates) == len(first.candidates)


def test_copy_many_parallel_and_cancel(tmp_path: Path, monkeypatch):
    import threading
    from collect_files_plus import collector
    src = tmp_path / "seq"
    src.mkdir()
    files = []
    for i in range(60):
        f = src / ("frame_%04d.png" % i)
        f.write_bytes(bytes([i]) * (100 + i))
        files.append(f)
    done = []
    collector.copy_many(files, tmp_path / "out", on_done=done.append)
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [f.name for f in files]
    assert (tmp_path / "out" / "frame_0042.png").read_bytes() == bytes([42]) * 142
    assert done == list(range(1, 61))

    cancel = threading.Event()

    def tick(n):
        if n == 10:
            cancel.set()
    with pytest.raises(collector.Cancelled):
        collector.copy_many(files, tmp_path / "out2", on_done=tick, cancel=cancel)

    real = collector.copy_file

    def flaky(f, dest, **kw):
        if f.name == "frame_0030.png":
            raise OSError("disk penuh")
        return real(f, dest, **kw)
    monkeypatch.setattr(collector, "copy_file", flaky)
    with pytest.raises(OSError):
        collector.copy_many(files, tmp_path / "out3")
