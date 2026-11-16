"""GUI smoke tests (offscreen). Skipped when PyQt5 is not installed."""
import os

import pytest

pytest.importorskip("PyQt5.QtWidgets")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QFileDialog  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def env(tmp_path, monkeypatch):
    for var, sub in (("HOME", ""), ("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache")):
        d = tmp_path / sub
        d.mkdir(exist_ok=True)
        monkeypatch.setenv(var, str(d))
    docs = tmp_path / "Docs"
    docs.mkdir()
    (docs / "a.txt").write_text("x")
    (tmp_path / "data" / "recently-used.xbel").write_text(
        f'<xbel version="1.0"><bookmark href="file://{docs}/a.txt" added="2026-01-01T00:00:00Z"/></xbel>'
    )
    return tmp_path


@pytest.mark.parametrize("lang", ["en", "es"])
def test_pin_a_file_does_not_crash(app, env, monkeypatch, lang):
    from deepin_jumplist import i18n
    from deepin_jumplist.config import Config
    from deepin_jumplist.popup import JumpListPopup

    i18n.set_language(lang)
    picked = str(env / "Docs" / "a.txt")
    calls = []

    def fake_dialog(parent, title, directory):
        calls.append(title)
        return [picked], ""

    monkeypatch.setattr(QFileDialog, "getOpenFileNames", staticmethod(fake_dialog))
    cfg = Config()
    popup = JumpListPopup(cfg, lambda: None)
    popup._pin_file_dialog()
    assert cfg.pinned == [picked]
    assert calls == [i18n._("Pin files to the jump list")]
    i18n.set_language(None)


def test_recent_folders_section(app, env):
    from deepin_jumplist import i18n
    from deepin_jumplist.config import Config
    from deepin_jumplist.popup import JumpListPopup

    i18n.set_language("en")
    cfg = Config()
    popup = JumpListPopup(cfg, lambda: None)
    popup.rebuild()
    assert [r.path for r in popup.rows] == [str(env / "Docs" / "a.txt")]

    cfg["include_folders"] = True
    popup.rebuild()
    assert [r.path for r in popup.rows] == [str(env / "Docs" / "a.txt"), str(env / "Docs")]

    popup._remove_recent(str(env / "Docs"))
    assert [r.path for r in popup.rows] == [str(env / "Docs" / "a.txt")]
    i18n.set_language(None)
