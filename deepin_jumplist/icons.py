"""Icons: the app icon, file-type icons / thumbnails and a painted pin glyph."""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache

from PyQt5.QtCore import QFileInfo, QPointF, QRectF, QSize, Qt, QUrl
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtCore import QMimeDatabase
from PyQt5.QtWidgets import QFileIconProvider

from . import APP_ID

_HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.path.join(_HERE, "resources", APP_ID + ".svg"),
]

_mime_db = None
_provider = None


def app_icon() -> QIcon:
    for path in _CANDIDATES:
        if os.path.exists(path):
            return QIcon.fromTheme(APP_ID, QIcon(path))
    return QIcon.fromTheme(APP_ID, QIcon.fromTheme("document-open-recent"))


def _thumbnail_for(path: str) -> str | None:
    uri = bytes(QUrl.fromLocalFile(path).toEncoded())
    digest = hashlib.md5(uri).hexdigest() + ".png"
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    for size in ("normal", "large", "x-large"):
        candidate = os.path.join(cache, "thumbnails", size, digest)
        if os.path.exists(candidate):
            return candidate
    return None


@lru_cache(maxsize=256)
def _icon_for(path: str, mtime: float) -> QIcon:
    global _mime_db, _provider
    if _mime_db is None:
        _mime_db = QMimeDatabase()
        _provider = QFileIconProvider()
    mime = _mime_db.mimeTypeForFile(path)
    if mime.name().startswith("image/"):
        thumb = _thumbnail_for(path)
        if thumb:
            icon = QIcon(thumb)
            if not icon.isNull():
                return icon
    fallback = _provider.icon(QFileInfo(path))
    generic = QIcon.fromTheme(mime.genericIconName(), fallback)
    return QIcon.fromTheme(mime.iconName(), generic)


def file_icon(path: str) -> QIcon:
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0.0
    return _icon_for(path, mtime)


def pin_pixmap(color: QColor, filled: bool, size: int = 16, dpr: float = 1.0) -> QPixmap:
    """Draw a small push-pin glyph (tilted 45 degrees like Windows')."""
    pm = QPixmap(QSize(int(size * dpr), int(size * dpr)))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 16.0
    p.scale(s, s)
    p.translate(8, 8)
    p.rotate(45)
    pen = QPen(color, 1.3)
    pen.setJoinStyle(Qt.RoundJoin)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(color if filled else Qt.transparent)
    body = QPainterPath()
    body.moveTo(-2.5, -6.5)
    body.lineTo(2.5, -6.5)
    body.lineTo(2.0, -5.5)
    body.lineTo(2.0, -1.5)
    body.lineTo(4.0, 1.0)
    body.lineTo(-4.0, 1.0)
    body.lineTo(-2.0, -1.5)
    body.lineTo(-2.0, -5.5)
    body.closeSubpath()
    p.drawPath(body)
    p.drawLine(QPointF(0, 1.0), QPointF(0, 7.0))
    p.end()
    return pm


def gear_pixmap(color: QColor, size: int = 16, dpr: float = 1.0) -> QPixmap:
    pm = QPixmap(QSize(int(size * dpr), int(size * dpr)))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 16.0, size / 16.0)
    p.translate(8, 8)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    for _ in range(8):
        p.drawRoundedRect(QRectF(-1.4, -7.2, 2.8, 3.4), 0.8, 0.8)
        p.rotate(45)
    outer = QPainterPath()
    outer.addEllipse(QPointF(0, 0), 5.2, 5.2)
    inner = QPainterPath()
    inner.addEllipse(QPointF(0, 0), 2.2, 2.2)
    p.drawPath(outer.subtracted(inner))
    p.end()
    return pm


def plus_pixmap(color: QColor, size: int = 16, dpr: float = 1.0) -> QPixmap:
    pm = QPixmap(QSize(int(size * dpr), int(size * dpr)))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 16.0, size / 16.0)
    pen = QPen(color, 1.6)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(8, 3), QPointF(8, 13))
    p.drawLine(QPointF(3, 8), QPointF(13, 8))
    p.end()
    return pm
