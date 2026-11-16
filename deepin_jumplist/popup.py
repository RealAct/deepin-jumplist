"""The jump list popup that opens from the dock icon."""

from __future__ import annotations

import os
import time
from typing import Callable, List, Optional

from PyQt5.QtCore import QMimeData, QPoint, QRect, QRectF, QSize, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QDrag, QFontMetrics, QGuiApplication, QIcon, QPainter
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME
from .actions import open_path, reveal_path
from .config import Config
from .i18n import _
from .icons import app_icon, file_icon, gear_pixmap, pin_pixmap, plus_pixmap
from .recent import RecentItem, load_recent
from .theme import (
    ITEM_RADIUS,
    RADIUS,
    Colors,
    RoundedMenu,
    apply_mask_if_needed,
    current_colors,
    make_rounded_window,
    paint_rounded_background,
)

POPUP_WIDTH = 340
ROW_HEIGHT = 36
MARGIN = 8
GAP_FROM_CURSOR = 10


class IconButton(QToolButton):
    """Small round-cornered flat button with a painted glyph."""

    def __init__(self, colors: Colors, tooltip: str, parent=None):
        super().__init__(parent)
        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(28, 28)
        self.setIconSize(QSize(16, 16))
        self.setFocusPolicy(Qt.NoFocus)
        self.setAutoRaise(True)
        self.setStyleSheet(
            f"QToolButton {{ border: none; border-radius: {ITEM_RADIUS}px; background: transparent; }}"
            f"QToolButton:hover {{ background: {colors.css(colors.hover)}; }}"
            f"QToolButton:pressed {{ background: {colors.css(colors.pressed)}; }}"
        )


class ItemRow(QWidget):
    activated = pyqtSignal(str)
    pin_toggled = pyqtSignal(str)
    context_requested = pyqtSignal(str, QPoint)

    def __init__(self, path: str, pinned: bool, colors: Colors, parent=None):
        super().__init__(parent)
        self.path = path
        self.pinned = pinned
        self.colors = colors
        self._hover = False
        self._press_pos: Optional[QPoint] = None
        self.setFixedHeight(ROW_HEIGHT)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(path)
        self.setAttribute(Qt.WA_Hover, True)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 4, 0)
        lay.setSpacing(10)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setPixmap(file_icon(path).pixmap(20, 20))
        self.icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(self.icon_label)

        self.name = os.path.basename(path.rstrip("/")) or path
        self.name_label = QLabel(self.name, self)
        self.name_label.setStyleSheet(f"color: {colors.css(colors.fg)}; background: transparent;")
        self.name_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.name_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(self.name_label, 1)

        self.pin_button = IconButton(colors, _("Unpin from this list") if pinned else _("Pin to this list"), self)
        dpr = self.devicePixelRatioF()
        self.pin_button.setIcon(QIcon(pin_pixmap(colors.fg if pinned else colors.dim, pinned, 16, dpr)))
        self.pin_button.clicked.connect(lambda: self.pin_toggled.emit(self.path))
        lay.addWidget(self.pin_button)
        self._update_pin_visibility()

    # -- helpers -------------------------------------------------------------
    def _update_pin_visibility(self) -> None:
        # Like Windows: the pin shows on hover/focus; pinned rows keep it subtle.
        visible = self._hover or self.hasFocus()
        self.pin_button.setVisible(visible)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        fm = QFontMetrics(self.name_label.font())
        self.name_label.setText(fm.elidedText(self.name, Qt.ElideMiddle, max(10, self.name_label.width())))

    def enterEvent(self, event):  # noqa: N802
        self._hover = True
        self._update_pin_visibility()
        self.update()

    def leaveEvent(self, event):  # noqa: N802
        self._hover = False
        self._update_pin_visibility()
        self.update()

    def focusInEvent(self, event):  # noqa: N802
        super().focusInEvent(event)
        self._update_pin_visibility()
        self.update()

    def focusOutEvent(self, event):  # noqa: N802
        super().focusOutEvent(event)
        self._update_pin_visibility()
        self.update()

    def paintEvent(self, event):  # noqa: N802
        if not (self._hover or self.hasFocus()):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self.colors.pressed if self._press_pos else self.colors.hover)
        p.drawRoundedRect(QRectF(self.rect()), ITEM_RADIUS, ITEM_RADIUS)
        p.end()

    # -- interaction ---------------------------------------------------------
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._press_pos = event.pos()
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802
        # Drag the file out of the jump list into another app.
        if self._press_pos is not None and (event.pos() - self._press_pos).manhattanLength() > QApplication.startDragDistance():
            self._press_pos = None
            self.update()
            drag = QDrag(self)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(self.path)])
            mime.setText(self.path)
            drag.setMimeData(mime)
            drag.setPixmap(file_icon(self.path).pixmap(32, 32))
            drag.exec_(Qt.CopyAction | Qt.LinkAction)

    def mouseReleaseEvent(self, event):  # noqa: N802
        was_pressed = self._press_pos is not None
        self._press_pos = None
        self.update()
        if event.button() == Qt.LeftButton and was_pressed and self.rect().contains(event.pos()):
            self.activated.emit(self.path)

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.activated.emit(self.path)
        elif event.key() == Qt.Key_Menu:
            self.context_requested.emit(self.path, self.mapToGlobal(self.rect().center()))
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):  # noqa: N802
        self.context_requested.emit(self.path, event.globalPos())


class JumpListPopup(QWidget):
    """Frameless, rounded popup listing pinned and recent files."""

    def __init__(self, config: Config, show_options: Callable[[], None]):
        super().__init__(None, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.config = config
        self.show_options = show_options
        self.last_hidden = 0.0
        self.recent_items: List[RecentItem] = []
        self.rows: List[ItemRow] = []
        self.colors = current_colors(config["theme"])
        self._anchor = QPoint()
        self.setWindowTitle(APP_NAME)
        self.setFixedWidth(POPUP_WIDTH)
        make_rounded_window(self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        outer.setSpacing(4)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll.setAttribute(Qt.WA_TranslucentBackground)
        outer.addWidget(self.scroll)

        self.separator = QFrame(self)
        self.separator.setFixedHeight(1)
        outer.addWidget(self.separator)

        footer = QHBoxLayout()
        footer.setContentsMargins(8, 2, 0, 0)
        footer.setSpacing(8)
        self.footer_icon = QLabel(self)
        self.footer_icon.setFixedSize(20, 20)
        self.footer_icon.setPixmap(app_icon().pixmap(20, 20))
        footer.addWidget(self.footer_icon)
        self.footer_label = QLabel(APP_NAME, self)
        footer.addWidget(self.footer_label, 1)
        self.add_button = IconButton(self.colors, _("Pin a file…"), self)
        self.add_button.clicked.connect(self._pin_file_dialog)
        footer.addWidget(self.add_button)
        self.options_button = IconButton(self.colors, _("Options"), self)
        self.options_button.clicked.connect(self._open_options)
        footer.addWidget(self.options_button)
        outer.addLayout(footer)

        self.apply_theme()

    # -- theme ---------------------------------------------------------------
    def apply_theme(self) -> None:
        self.colors = c = current_colors(self.config["theme"])
        dpr = self.devicePixelRatioF()
        self.separator.setStyleSheet(f"background: {c.css(c.border)}; border: none;")
        self.footer_label.setStyleSheet(f"color: {c.css(c.dim)}; background: transparent;")
        self.scroll.setStyleSheet(
            "QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }"
            f"QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}"
            f"QScrollBar::handle:vertical {{ background: {c.css(c.dim)}; border-radius: 2px; min-height: 24px; }}"
            "QScrollBar::add-line, QScrollBar::sub-line { height: 0; }"
            "QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }"
        )
        for b in (self.add_button, self.options_button):
            b.setStyleSheet(
                f"QToolButton {{ border: none; border-radius: {ITEM_RADIUS}px; background: transparent; }}"
                f"QToolButton:hover {{ background: {c.css(c.hover)}; }}"
                f"QToolButton:pressed {{ background: {c.css(c.pressed)}; }}"
            )
        self.add_button.setIcon(QIcon(plus_pixmap(c.fg, 16, dpr)))
        self.options_button.setIcon(QIcon(gear_pixmap(c.fg, 16, dpr)))

    # -- content -------------------------------------------------------------
    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {self.colors.css(self.colors.dim)}; font-weight: 600; background: transparent;"
            "padding: 6px 10px 2px 10px;"
        )
        return label

    def _make_row(self, path: str, pinned: bool) -> ItemRow:
        row = ItemRow(path, pinned, self.colors)
        row.activated.connect(self._open)
        row.pin_toggled.connect(self._toggle_pin)
        row.context_requested.connect(self._context_menu)
        self.rows.append(row)
        return row

    def rebuild(self) -> None:
        self.apply_theme()
        self.rows = []
        content = QWidget()
        content.setAttribute(Qt.WA_TranslucentBackground)
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)

        pinned = [p for p in self.config.pinned if os.path.exists(p)] if self.config["show_pinned"] else []
        if pinned:
            lay.addWidget(self._section_label(_("Pinned")))
            for path in pinned:
                lay.addWidget(self._make_row(path, True))

        self.recent_items = load_recent(
            self.config["max_items"],
            exclude=self.config.pinned,
            hidden=self.config["hidden"],
            include_folders=self.config["include_folders"],
        )
        lay.addWidget(self._section_label(_("Recent")))
        if self.recent_items:
            for item in self.recent_items:
                lay.addWidget(self._make_row(item.path, False))
        else:
            empty = QLabel(_("Files you open will show up here."))
            empty.setStyleSheet(
                f"color: {self.colors.css(self.colors.dim)}; background: transparent; padding: 8px 10px;"
            )
            lay.addWidget(empty)
        lay.addStretch(1)

        old = self.scroll.takeWidget()
        if old is not None:
            old.deleteLater()
        self.scroll.setWidget(content)

        # Height: fit the content, but never taller than the screen.
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        footer_h = 1 + 4 + 30 + 4
        max_scroll = max(ROW_HEIGHT * 3, avail.height() - 2 * MARGIN - footer_h - 40)
        content_h = content.sizeHint().height()
        self.scroll.setFixedHeight(min(content_h, max_scroll))
        self.adjustSize()

    # -- placement -----------------------------------------------------------
    def position_near(self, anchor: QPoint) -> None:
        """Place the popup next to where the dock was clicked, on whichever
        side of the screen the dock is (bottom, top, left or right)."""
        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        avail: QRect = screen.availableGeometry()
        full: QRect = screen.geometry()
        w, h = self.width(), self.height()
        g = GAP_FROM_CURSOR

        if anchor.y() >= avail.bottom() or anchor.y() > full.bottom() - 120:  # dock at bottom
            x, y = anchor.x() - w // 2, min(anchor.y(), avail.bottom()) - h - g
        elif anchor.y() <= avail.top() or anchor.y() < full.top() + 120:  # dock at top
            x, y = anchor.x() - w // 2, max(anchor.y(), avail.top()) + g
        elif anchor.x() <= avail.left() or anchor.x() < full.left() + 120:  # dock on the left
            x, y = max(anchor.x(), avail.left()) + g, anchor.y() - h // 2
        elif anchor.x() >= avail.right() or anchor.x() > full.right() - 120:  # dock on the right
            x, y = min(anchor.x(), avail.right()) - w - g, anchor.y() - h // 2
        else:  # launched some other way: open above the cursor
            x, y = anchor.x() - w // 2, anchor.y() - h - g

        x = max(avail.left() + g, min(x, avail.right() - w - g))
        y = max(avail.top() + g, min(y, avail.bottom() - h - g))
        self.move(x, y)

    def show_at(self, anchor: Optional[QPoint] = None) -> None:
        self._anchor = anchor or QCursor.pos()
        self.rebuild()
        self.position_near(self._anchor)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()  # rows highlight only once the arrow keys are used

    def toggle(self, anchor: Optional[QPoint] = None) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show_at(anchor)

    # -- events --------------------------------------------------------------
    def paintEvent(self, event):  # noqa: N802
        paint_rounded_background(self, self.colors, RADIUS)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        apply_mask_if_needed(self, RADIUS)

    def hideEvent(self, event):  # noqa: N802
        self.last_hidden = time.time()
        super().hideEvent(event)

    def keyPressEvent(self, event):  # noqa: N802
        key = event.key()
        if key == Qt.Key_Escape:
            self.hide()
            return
        if key in (Qt.Key_Down, Qt.Key_Up) and self.rows:
            focused = self.focusWidget()
            idx = self.rows.index(focused) if focused in self.rows else -1
            if key == Qt.Key_Down:
                idx = (idx + 1) % len(self.rows)
            else:
                idx = (idx - 1) % len(self.rows) if idx >= 0 else len(self.rows) - 1
            self.rows[idx].setFocus(Qt.TabFocusReason)
            self.scroll.ensureWidgetVisible(self.rows[idx])
            return
        super().keyPressEvent(event)

    # -- actions -------------------------------------------------------------
    def _open(self, path: str) -> None:
        self.hide()
        open_path(path)

    def _toggle_pin(self, path: str) -> None:
        if self.config.is_pinned(path):
            self.config.unpin(path)
        else:
            self.config.pin(path)
        self._refresh_in_place()

    def _refresh_in_place(self) -> None:
        self.rebuild()
        self.position_near(self._anchor)

    def _context_menu(self, path: str, pos: QPoint) -> None:
        theme = self.config["theme"]
        menu = RoundedMenu(parent=self, theme_mode=theme)
        menu.addAction(_("Open"), lambda: self._open(path))
        menu.addAction(_("Open file location"), lambda: (self.hide(), reveal_path(path)))
        menu.addAction(_("Copy path"), lambda: QApplication.clipboard().setText(path))
        menu.addSeparator()
        if self.config.is_pinned(path):
            menu.addAction(_("Unpin from this list"), lambda: self._toggle_pin(path))
            pins = self.config.pinned
            i = pins.index(path)
            up = menu.addAction(_("Move up"), lambda: (self.config.move_pin(path, -1), self._refresh_in_place()))
            up.setEnabled(i > 0)
            down = menu.addAction(_("Move down"), lambda: (self.config.move_pin(path, 1), self._refresh_in_place()))
            down.setEnabled(i < len(pins) - 1)
        else:
            menu.addAction(_("Pin to this list"), lambda: self._toggle_pin(path))
            menu.addAction(_("Remove from this list"), lambda: self._remove_recent(path))
        menu.exec_(pos)

    def _remove_recent(self, path: str) -> None:
        for item in self.recent_items:
            if item.path == path:
                self.config.hide_recent(path, item.timestamp)
        self._refresh_in_place()

    def _pin_file_dialog(self) -> None:
        self.hide()
        paths, _ = QFileDialog.getOpenFileNames(None, _("Pin files to the jump list"), os.path.expanduser("~"))
        for path in reversed(paths):
            self.config.pin(path)

    def _open_options(self) -> None:
        self.hide()
        self.show_options()
