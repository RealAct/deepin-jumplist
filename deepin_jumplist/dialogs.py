"""Options and About windows, both frameless with rounded corners."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, VERSION
from .config import MAX_ITEMS, MIN_ITEMS, Config, set_autostart
from .icons import app_icon
from .recent import load_recent
from .theme import (
    RADIUS,
    apply_mask_if_needed,
    current_colors,
    dialog_stylesheet,
    make_rounded_window,
    paint_rounded_background,
)


class RoundedDialog(QDialog):
    """Frameless dialog with a painted rounded background, its own title bar
    (drag to move) and a close button."""

    def __init__(self, title: str, theme_mode: str = "auto", parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setWindowTitle(title)
        self.setWindowIcon(app_icon())
        make_rounded_window(self)
        self.colors = current_colors(theme_mode)
        self.setStyleSheet(dialog_stylesheet(self.colors))
        self._drag_offset: Optional[QPoint] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 16)
        root.setSpacing(12)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(18, 18))
        bar.addWidget(icon)
        label = QLabel(title)
        label.setObjectName("titleLabel")
        bar.addWidget(label, 1)
        close = QToolButton()
        close.setObjectName("closeButton")
        close.setText("✕")
        close.setFixedSize(28, 28)
        close.setCursor(Qt.PointingHandCursor)
        close.setToolTip("Close")
        close.clicked.connect(self.reject)
        bar.addWidget(close)
        root.addLayout(bar)

        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        root.addLayout(self.body)

    def paintEvent(self, event):  # noqa: N802
        paint_rounded_background(self, self.colors, RADIUS)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        apply_mask_if_needed(self, RADIUS)

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton and event.pos().y() < 48:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def center_on_screen(self) -> None:
        screen = self.screen() if hasattr(self, "screen") else None
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.adjustSize()
        self.move(geo.center() - self.rect().center())


def _separator() -> QFrame:
    line = QFrame()
    line.setObjectName("separator")
    return line


class OptionsDialog(RoundedDialog):
    def __init__(self, config: Config, on_changed: Callable[[], None], parent=None):
        super().__init__("Options", config["theme"], parent)
        self.config = config
        self.on_changed = on_changed
        self.setMinimumWidth(420)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.max_items = QSpinBox()
        self.max_items.setRange(MIN_ITEMS, MAX_ITEMS)
        self.max_items.setValue(config["max_items"])
        self.max_items.setSuffix(" items")
        form.addRow("Recent items to show", self.max_items)

        self.show_pinned = QCheckBox("Show pinned items")
        self.show_pinned.setChecked(config["show_pinned"])
        form.addRow("", self.show_pinned)

        self.include_folders = QCheckBox("Include recently opened folders")
        self.include_folders.setChecked(config["include_folders"])
        form.addRow("", self.include_folders)

        self.theme = QComboBox()
        self.theme.addItem("Follow system", "auto")
        self.theme.addItem("Light", "light")
        self.theme.addItem("Dark", "dark")
        self.theme.setCurrentIndex(max(0, self.theme.findData(config["theme"])))
        form.addRow("Appearance", self.theme)

        self.start_at_login = QCheckBox("Start in the tray when I log in")
        self.start_at_login.setChecked(config["start_at_login"])
        form.addRow("", self.start_at_login)

        self.native_menu = QCheckBox("Use the system tray menu (compatibility)")
        self.native_menu.setToolTip(
            "Turn on if right-clicking the tray icon shows nothing on your desktop.\n"
            "The menu is then drawn by the panel instead of this app."
        )
        self.native_menu.setChecked(config["native_tray_menu"])
        form.addRow("", self.native_menu)
        self.body.addLayout(form)

        self.body.addWidget(_separator())
        clear_row = QHBoxLayout()
        clear_hint = QLabel("Hide everything currently in the Recent list.")
        clear_hint.setObjectName("dimLabel")
        clear_row.addWidget(clear_hint, 1)
        clear = QPushButton("Clear recent")
        clear.clicked.connect(self._clear_recent)
        clear_row.addWidget(clear)
        self.body.addLayout(clear_row)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setObjectName("primary")
        save.setDefault(True)
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        self.body.addLayout(buttons)

    def _clear_recent(self) -> None:
        items = load_recent(10_000, hidden=self.config["hidden"], include_folders=True)
        self.config.clear_recent(items)
        self.on_changed()

    def _save(self) -> None:
        c = self.config
        c["max_items"] = self.max_items.value()
        c["show_pinned"] = self.show_pinned.isChecked()
        c["include_folders"] = self.include_folders.isChecked()
        c["theme"] = self.theme.currentData()
        c["native_tray_menu"] = self.native_menu.isChecked()
        c["start_at_login"] = self.start_at_login.isChecked()
        try:
            set_autostart(c["start_at_login"])
        except OSError:
            pass
        c.save()
        self.on_changed()
        self.accept()


class AboutDialog(RoundedDialog):
    def __init__(self, theme_mode: str = "auto", parent=None):
        super().__init__("About", theme_mode, parent)
        self.setFixedWidth(360)

        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(72, 72))
        icon.setAlignment(Qt.AlignCenter)
        self.body.addWidget(icon)

        name = QLabel(APP_NAME)
        name.setObjectName("bigTitle")
        name.setAlignment(Qt.AlignCenter)
        self.body.addWidget(name)

        version = QLabel(f"Version {VERSION}")
        version.setObjectName("dimLabel")
        version.setAlignment(Qt.AlignCenter)
        self.body.addWidget(version)

        text = QLabel(
            "A Windows 11 style jump list for the Deepin dock and other "
            "Debian based desktops. Click the dock icon for one-click access "
            "to your recent and pinned files."
        )
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)
        text.setFixedHeight(text.heightForWidth(360 - 32) + 4)
        self.body.addWidget(text)

        link_color = self.colors.accent.lighter(135) if self.colors.dark else self.colors.accent
        link = QLabel(
            f'<a style="color:{link_color.name()}" href="https://github.com/RealAct/deepin-jumplist">'
            "github.com/RealAct/deepin-jumplist</a>"
        )
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignCenter)
        self.body.addWidget(link)

        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("Close")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        row.addStretch(1)
        self.body.addLayout(row)
