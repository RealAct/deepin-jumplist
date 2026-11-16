import re
from pathlib import Path

import pytest

from deepin_jumplist import i18n


@pytest.fixture(autouse=True)
def reset_language():
    yield
    i18n.set_language(None)


@pytest.mark.parametrize(
    "env, expected",
    [
        ({"LANG": "es_ES.UTF-8"}, "es"),
        ({"LANG": "es_MX.UTF-8"}, "es"),
        ({"LANGUAGE": "es_AR:en", "LANG": "en_US.UTF-8"}, "es"),
        ({"LC_ALL": "en_US.UTF-8", "LANG": "es_ES.UTF-8"}, "en"),
        ({"LC_MESSAGES": "es_CL.UTF-8", "LANG": "en_US.UTF-8"}, "es"),
        ({"LANG": "en_GB.UTF-8"}, "en"),
        ({"LANG": "fr_FR.UTF-8"}, "fr"),
    ],
)
def test_detect_language(monkeypatch, env, expected):
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert i18n.detect_language() == expected


def test_unsupported_language_falls_back_to_english(monkeypatch):
    i18n.set_language("fr")
    assert i18n.language() == "en"
    assert i18n._("Pinned") == "Pinned"


def test_spanish_and_formatting():
    i18n.set_language("es")
    assert i18n._("Pinned") == "Anclados"
    assert i18n._("Version {version}", version="1.1.0") == "Versión 1.1.0"
    assert i18n._("Created by Eli Linares for {link}", link="X") == "Creado por Eli Linares para X"
    assert i18n._("Not in catalog") == "Not in catalog"


def test_every_ui_string_has_a_spanish_translation():
    """Every _("...") literal in the package must exist in the Spanish catalog."""
    pkg = Path(i18n.__file__).parent
    pattern = re.compile(r'_\(\s*((?:"(?:[^"\\]|\\.)*"\s*)+)', re.S)
    missing = []
    for src in pkg.glob("*.py"):
        for match in pattern.finditer(src.read_text(encoding="utf-8")):
            text = eval("(" + match.group(1) + ")")  # adjacent string literals
            if text not in i18n.ES:
                missing.append(f"{src.name}: {text!r}")
    assert not missing, missing
