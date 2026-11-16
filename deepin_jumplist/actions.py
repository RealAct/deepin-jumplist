"""Opening files and revealing them in the file manager."""

from __future__ import annotations

import os

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices


def open_path(path: str) -> bool:
    """Open with the user's default application (same as xdg-open)."""
    if not os.path.exists(path):
        return False
    return QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def reveal_path(path: str) -> bool:
    """Show the file selected in the file manager (dde-file-manager, Nautilus,
    Dolphin, Nemo... all implement org.freedesktop.FileManager1)."""
    uri = QUrl.fromLocalFile(path).toString()
    try:
        from PyQt5.QtCore import QMetaType
        from PyQt5.QtDBus import QDBusArgument, QDBusConnection, QDBusInterface

        iface = QDBusInterface(
            "org.freedesktop.FileManager1",
            "/org/freedesktop/FileManager1",
            "org.freedesktop.FileManager1",
            QDBusConnection.sessionBus(),
        )
        if iface.isValid():
            reply = iface.call("ShowItems", QDBusArgument([uri], QMetaType.QStringList), "")
            if not reply.errorName():
                return True
    except Exception:
        pass
    return QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
