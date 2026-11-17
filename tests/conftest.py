import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _bahasa_indonesia(monkeypatch):
    """Test memakai bahasa Indonesia kecuali test itu sendiri menggantinya."""
    from collect_files_plus import i18n
    monkeypatch.setenv(i18n.ENV_VAR, "id")
    monkeypatch.setenv("COLLECT_FILES_PLUS_NO_UPDATE_CHECK", "1")   # test tidak boleh ke internet
    monkeypatch.delenv("COLLECT_FILES_PLUS_UPDATE_RESULT", raising=False)
    i18n.set_language("id")
    yield
    i18n.set_language("id")
