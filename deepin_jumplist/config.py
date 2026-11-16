"""Persistent settings and pinned items, stored as JSON under XDG_CONFIG_HOME."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from typing import Any, Dict, List

from . import APP_ID

MIN_ITEMS = 1
MAX_ITEMS = 30

DEFAULTS: Dict[str, Any] = {
    "max_items": 10,
    "show_pinned": True,
    "include_folders": False,
    "theme": "auto",  # auto | light | dark
    "start_at_login": False,
    "native_tray_menu": False,
    "pinned": [],
    "hidden": {},
}


def config_dir() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, APP_ID)


def autostart_path() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "autostart", APP_ID + ".desktop")


class Config:
    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(config_dir(), "config.json")
        self.data: Dict[str, Any] = json.loads(json.dumps(DEFAULTS))
        self.load()

    # -- persistence -------------------------------------------------------
    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
        except (OSError, ValueError):
            return
        if isinstance(loaded, dict):
            for key, default in DEFAULTS.items():
                if key in loaded and isinstance(loaded[key], type(default)):
                    self.data[key] = loaded[key]
        self.data["max_items"] = clamp_items(self.data["max_items"])

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), prefix=".config-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2)
        os.replace(tmp, self.path)

    # -- accessors ---------------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if key == "max_items":
            value = clamp_items(value)
        self.data[key] = value

    @property
    def pinned(self) -> List[str]:
        return list(self.data["pinned"])

    def is_pinned(self, path: str) -> bool:
        return path in self.data["pinned"]

    def pin(self, path: str) -> None:
        if path not in self.data["pinned"]:
            self.data["pinned"].insert(0, path)
            self.save()

    def unpin(self, path: str) -> None:
        if path in self.data["pinned"]:
            self.data["pinned"].remove(path)
            self.save()

    def move_pin(self, path: str, offset: int) -> None:
        pins = self.data["pinned"]
        if path not in pins:
            return
        i = pins.index(path)
        j = max(0, min(len(pins) - 1, i + offset))
        pins.insert(j, pins.pop(i))
        self.save()

    def hide_recent(self, path: str, timestamp: float) -> None:
        self.data["hidden"][path] = timestamp
        self.save()

    def clear_recent(self, items) -> None:
        for item in items:
            self.data["hidden"][item.path] = item.timestamp
        self.save()


def clamp_items(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = DEFAULTS["max_items"]
    return max(MIN_ITEMS, min(MAX_ITEMS, n))


def launch_command() -> str:
    """Command used by the autostart entry."""
    exe = shutil.which(APP_ID)
    if exe:
        return f"{exe} --background"
    pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return f'env PYTHONPATH="{pkg_parent}" {sys.executable} -m deepin_jumplist --background'


def set_autostart(enabled: bool) -> None:
    path = autostart_path()
    if not enabled:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Deepin Jumplist\n"
            "Comment=Quick access to your recent and pinned files\n"
            "Comment[es]=Acceso rápido a tus archivos recientes y anclados\n"
            f"Exec={launch_command()}\n"
            f"Icon={APP_ID}\n"
            "Terminal=false\n"
            "NoDisplay=true\n"
            "X-GNOME-Autostart-enabled=true\n"
            "X-Deepin-Vendor=user-custom\n"
        )
