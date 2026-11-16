import json

from deepin_jumplist.config import Config


def test_defaults_and_clamp(tmp_path):
    cfg = Config(str(tmp_path / "c.json"))
    assert cfg["max_items"] == 10 and cfg["show_pinned"] is True
    cfg["max_items"] = 999
    assert cfg["max_items"] == 30
    cfg["max_items"] = 0
    assert cfg["max_items"] == 1


def test_pins_persist_and_reorder(tmp_path):
    path = str(tmp_path / "c.json")
    cfg = Config(path)
    cfg.pin("/a")
    cfg.pin("/b")
    cfg.pin("/a")  # no duplicates
    assert cfg.pinned == ["/b", "/a"]
    cfg.move_pin("/a", -1)
    assert Config(path).pinned == ["/a", "/b"]
    cfg.unpin("/a")
    assert Config(path).pinned == ["/b"]


def test_corrupt_or_wrong_types(tmp_path):
    path = tmp_path / "c.json"
    path.write_text("{not json")
    assert Config(str(path))["max_items"] == 10
    path.write_text(json.dumps({"max_items": "x", "pinned": "nope", "show_pinned": False}))
    cfg = Config(str(path))
    assert cfg.pinned == [] and cfg["show_pinned"] is False
