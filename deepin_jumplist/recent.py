"""Read the freedesktop recently-used list (recently-used.xbel).

GTK, Qt/KDE (via KRecentDocument mirroring), LibreOffice, the Deepin file
manager and most Deepin apps record opened files in
``$XDG_DATA_HOME/recently-used.xbel``.  This module parses that file without
any Qt dependency so it can be unit tested in isolation.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional
from urllib.parse import unquote, urlparse

MIME_NS = "http://www.freedesktop.org/standards/shared-mime-info"


@dataclass
class RecentItem:
    path: str
    timestamp: float  # seconds since epoch of the latest access
    mime_type: Optional[str] = None

    @property
    def name(self) -> str:
        return os.path.basename(self.path.rstrip("/")) or self.path


def default_xbel_path() -> str:
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(data_home, "recently-used.xbel")


def parse_timestamp(value: Optional[str]) -> float:
    """Parse the ISO 8601 timestamps written by GLib (``...Z`` with optional
    fractional seconds).  Returns 0.0 when missing or unparsable."""
    if not value:
        return 0.0
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    # Python < 3.11 cannot parse more than 6 fractional digits.
    if "." in v:
        head, _dot, rest = v.partition(".")
        frac = ""
        i = 0
        while i < len(rest) and rest[i].isdigit():
            frac += rest[i]
            i += 1
        v = head + "." + (frac[:6] or "0") + rest[i:]
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def uri_to_path(uri: str) -> Optional[str]:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    if parsed.netloc not in ("", "localhost"):
        return None
    return unquote(parsed.path)


def parse_xbel(source) -> List[RecentItem]:
    """Parse an xbel file (path or file object). Returns items newest first,
    de-duplicated by path. Non-local URIs are skipped. Existence on disk is
    *not* checked here, see :func:`load_recent`."""
    try:
        tree = ET.parse(source)
    except (ET.ParseError, OSError):
        return []
    items = {}
    for bm in tree.getroot().iter("bookmark"):
        path = uri_to_path(bm.get("href", ""))
        if not path:
            continue
        ts = max(
            parse_timestamp(bm.get("visited")),
            parse_timestamp(bm.get("modified")),
            parse_timestamp(bm.get("added")),
        )
        mime_el = bm.find(".//{%s}mime-type" % MIME_NS)
        mime = mime_el.get("type") if mime_el is not None else None
        old = items.get(path)
        if old is None or ts > old.timestamp:
            items[path] = RecentItem(path, ts, mime)
    return sorted(items.values(), key=lambda i: i.timestamp, reverse=True)


def load_recent(
    limit: int,
    exclude: Iterable[str] = (),
    hidden: Optional[dict] = None,
    include_folders: bool = False,
    xbel_path: Optional[str] = None,
) -> List[RecentItem]:
    """Return up to ``limit`` recent items that still exist on disk.

    ``exclude`` paths (e.g. pinned items) are skipped.  ``hidden`` maps a path
    to the timestamp at which the user removed it from the list; the item comes
    back once it is opened again after that time.
    """
    exclude = set(exclude)
    hidden = hidden or {}
    result: List[RecentItem] = []
    for item in parse_xbel(xbel_path or default_xbel_path()):
        if len(result) >= limit:
            break
        if item.path in exclude:
            continue
        if item.path in hidden and item.timestamp <= float(hidden[item.path]):
            continue
        if os.path.isfile(item.path) or (include_folders and os.path.isdir(item.path)):
            result.append(item)
    return result


def load_recent_folders(
    limit: int,
    exclude: Iterable[str] = (),
    hidden: Optional[dict] = None,
    xbel_path: Optional[str] = None,
) -> List[RecentItem]:
    """Return up to ``limit`` recently used folders, newest first.

    Most apps (and the Deepin file manager) only record *files* in
    recently-used.xbel, so a folder counts as recent when it was recorded
    itself or when it contains a recently used file, like the "Frequent
    folders" of Windows. Each folder gets the time of its newest use.
    """
    exclude = set(exclude)
    hidden = hidden or {}
    seen = set()
    result: List[RecentItem] = []
    for item in parse_xbel(xbel_path or default_xbel_path()):
        if len(result) >= limit:
            break
        if os.path.isdir(item.path):
            folder = item.path.rstrip("/") or "/"
        elif os.path.isfile(item.path):
            folder = os.path.dirname(item.path)
        else:
            continue
        if folder in seen:
            continue
        seen.add(folder)  # items are newest first, so the first hit is the latest use
        if folder in exclude:
            continue
        if folder in hidden and item.timestamp <= float(hidden[folder]):
            continue
        result.append(RecentItem(folder, item.timestamp, "inode/directory"))
    return result
