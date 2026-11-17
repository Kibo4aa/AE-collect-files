import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


import faulthandler  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_hang():
    """Test yang macet (mis. jendela Tk menunggu klik) dihentikan dengan traceback, bukan menggantung CI."""
    faulthandler.dump_traceback_later(240, exit=True)
    yield
    faulthandler.cancel_dump_traceback_later()


@pytest.fixture(autouse=True)
def _bahasa_indonesia(monkeypatch, tmp_path_factory):
    """Test memakai bahasa Indonesia kecuali test itu sendiri menggantinya; cache (font, PiPL)
    ditulis ke folder sementara milik test itu sendiri, bukan ke folder cache pengguna."""
    from collect_files_plus import i18n, plugins
    monkeypatch.setenv(i18n.ENV_VAR, "id")
    monkeypatch.setenv("COLLECT_FILES_PLUS_NO_UPDATE_CHECK", "1")   # test tidak boleh ke internet
    monkeypatch.delenv("COLLECT_FILES_PLUS_UPDATE_RESULT", raising=False)
    monkeypatch.setenv("COLLECT_FILES_PLUS_CACHE_DIR", str(tmp_path_factory.mktemp("cache")))
    plugins._ENTRY_CACHE.clear()
    plugins._DISK.update(loaded=False, dirty=False)
    i18n.set_language("id")
    yield
    i18n.set_language("id")
