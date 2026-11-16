"""Application entry point: single instance, tray icon and wiring.

Clicking the dock icon runs the .desktop Exec line, which starts a new process
each time. That process hands its command to the already running instance over
a local socket and exits immediately, so the popup appears without the cost of
starting a second Qt GUI.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from . import APP_ID, APP_NAME, VERSION
from .i18n import _


def _socket_name() -> str:
    # Prefer the per-user runtime dir (mode 0700); fall back to Qt's default
    # location in /tmp with the uid in the name.
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime and os.path.isdir(runtime):
        return os.path.join(runtime, APP_ID + ".sock")
    return "%s-%d.sock" % (APP_ID, os.getuid())


SOCKET_NAME = _socket_name()

# If the popup was closed by the very click that launched this command
# (the click on the dock icon itself), treat the launch as "close", not "reopen".
REOPEN_GUARD_SECONDS = 0.6


def parse_args(argv):
    parser = argparse.ArgumentParser(prog=APP_ID, description="Windows 11 style jump list for the Deepin dock.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--background", action="store_true", help="start in the tray without opening the list")
    group.add_argument("--options", action="store_true", help="open the Options window")
    group.add_argument("--about", action="store_true", help="open the About window")
    group.add_argument("--quit", action="store_true", help="quit the running instance")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    return parser.parse_args(argv)


def command_from_args(args) -> str:
    if args.background:
        return "background"
    if args.options:
        return "options"
    if args.about:
        return "about"
    if args.quit:
        return "quit"
    return "toggle"


def send_to_running_instance(command: str, started: float) -> bool:
    """Return True if another instance accepted the command."""
    from PyQt5.QtNetwork import QLocalSocket

    sock = QLocalSocket()
    sock.connectToServer(SOCKET_NAME)
    if not sock.waitForConnected(400):
        return False
    sock.write(f"{command} {started:.3f}\n".encode())
    sock.flush()
    sock.waitForBytesWritten(400)
    sock.disconnectFromServer()
    return True


class JumpListApp:
    def __init__(self, app):
        from PyQt5.QtNetwork import QLocalServer
        from PyQt5.QtWidgets import QSystemTrayIcon

        from .config import Config
        from .icons import app_icon
        from .popup import JumpListPopup

        self.app = app
        self.config = Config()
        self.popup = JumpListPopup(self.config, self.show_options)
        self.options_dialog = None
        self.about_dialog = None

        self.server = QLocalServer()
        QLocalServer.removeServer(SOCKET_NAME)
        if not self.server.listen(SOCKET_NAME):
            print(f"{APP_ID}: cannot listen on {SOCKET_NAME}: {self.server.errorString()}", file=sys.stderr)
        self.server.newConnection.connect(self._on_connection)

        self.tray = QSystemTrayIcon(app_icon())
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(self._on_tray_activated)
        self.menu = None
        self._build_tray_menu()
        self.tray.show()

    # -- tray ----------------------------------------------------------------
    def _build_tray_menu(self) -> None:
        from .theme import RoundedMenu

        self.menu = RoundedMenu(theme_mode=self.config["theme"])
        self.menu.addAction(_("Show jump list"), lambda: self.popup.show_at())
        self.menu.addSeparator()
        self.menu.addAction(_("Options…"), self.show_options)
        self.menu.addAction(_("About"), self.show_about)
        self.menu.addSeparator()
        self.menu.addAction(_("Exit"), self.quit)
        # By default we pop the rounded menu up ourselves on right click, so
        # the panel cannot replace it with its own square menu.
        self.tray.setContextMenu(self.menu if self.config["native_tray_menu"] else None)

    def _on_tray_activated(self, reason) -> None:
        from PyQt5.QtGui import QCursor
        from PyQt5.QtWidgets import QSystemTrayIcon

        if reason == QSystemTrayIcon.Context and not self.config["native_tray_menu"]:
            self.menu.popup(QCursor.pos())
        elif reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.popup.toggle()
        elif reason == QSystemTrayIcon.MiddleClick:
            self.show_options()

    # -- windows -------------------------------------------------------------
    def show_options(self) -> None:
        from .dialogs import OptionsDialog

        if self.options_dialog is None:
            self.options_dialog = OptionsDialog(self.config, self.settings_changed)
            self.options_dialog.finished.connect(self._options_closed)
            self.options_dialog.center_on_screen()
        self.options_dialog.show()
        self.options_dialog.raise_()
        self.options_dialog.activateWindow()

    def _options_closed(self) -> None:
        self.options_dialog.deleteLater()
        self.options_dialog = None

    def show_about(self) -> None:
        from .dialogs import AboutDialog

        if self.about_dialog is None:
            self.about_dialog = AboutDialog(self.config["theme"])
            self.about_dialog.finished.connect(self._about_closed)
            self.about_dialog.center_on_screen()
        self.about_dialog.show()
        self.about_dialog.raise_()
        self.about_dialog.activateWindow()

    def _about_closed(self) -> None:
        self.about_dialog.deleteLater()
        self.about_dialog = None

    def settings_changed(self) -> None:
        self._build_tray_menu()
        self.popup.apply_theme()
        if self.popup.isVisible():
            self.popup.rebuild()

    def quit(self) -> None:
        self.tray.hide()
        self.server.close()
        self.app.quit()

    # -- commands ------------------------------------------------------------
    def handle(self, command: str, started: float) -> None:
        if command == "toggle":
            if self.popup.isVisible():
                self.popup.hide()
            elif started - self.popup.last_hidden < REOPEN_GUARD_SECONDS:
                pass  # the dock click that launched us already closed the list
            else:
                self.popup.show_at()
        elif command == "options":
            self.show_options()
        elif command == "about":
            self.show_about()
        elif command == "quit":
            self.quit()

    def _on_connection(self) -> None:
        sock = self.server.nextPendingConnection()
        if sock is None:
            return

        def read():
            while sock.canReadLine():
                line = bytes(sock.readLine()).decode(errors="replace").split()
                if not line:
                    continue
                try:
                    started = float(line[1]) if len(line) > 1 else time.time()
                except ValueError:
                    started = time.time()
                self.handle(line[0], started)

        sock.readyRead.connect(read)
        sock.disconnected.connect(sock.deleteLater)
        read()


def main(argv=None, started: float | None = None) -> int:
    started = started or time.time()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    command = command_from_args(args)

    if send_to_running_instance(command, started):
        return 0
    if command == "quit":
        return 0

    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication

    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(False)

    from .icons import app_icon

    app.setWindowIcon(app_icon())
    jl = JumpListApp(app)
    app._jumplist = jl  # keep a reference

    if command == "toggle":
        jl.popup.show_at()
    elif command in ("options", "about"):
        jl.handle(command, started)

    return app.exec_()
