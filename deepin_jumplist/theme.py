"""Colours, stylesheets and the rounded-corner building blocks used everywhere."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen, QRegion
from PyQt5.QtWidgets import QApplication, QMenu, QWidget

RADIUS = 12        # outer radius of popups and dialogs
ITEM_RADIUS = 7    # radius of rows, buttons and menu items


@dataclass
class Colors:
    dark: bool
    bg: QColor
    fg: QColor
    dim: QColor
    border: QColor
    hover: QColor
    pressed: QColor
    accent: QColor
    accent_fg: QColor
    field: QColor

    def css(self, c: QColor) -> str:
        return "rgba(%d,%d,%d,%d)" % (c.red(), c.green(), c.blue(), c.alpha())


def current_colors(mode: str = "auto") -> Colors:
    pal = QApplication.palette()
    if mode == "dark":
        dark = True
    elif mode == "light":
        dark = False
    else:
        dark = pal.color(QPalette.Window).lightness() < 128
    accent = QColor(pal.color(QPalette.Highlight))
    if not accent.isValid() or accent.saturation() < 40:
        accent = QColor("#0081ff")  # Deepin blue
    if dark:
        return Colors(
            dark=True,
            bg=QColor(40, 40, 44, 242),
            fg=QColor("#f0f0f0"),
            dim=QColor(255, 255, 255, 140),
            border=QColor(255, 255, 255, 30),
            hover=QColor(255, 255, 255, 22),
            pressed=QColor(255, 255, 255, 36),
            accent=accent,
            accent_fg=QColor("#ffffff"),
            field=QColor(255, 255, 255, 18),
        )
    return Colors(
        dark=False,
        bg=QColor(250, 250, 252, 245),
        fg=QColor("#1d1d1f"),
        dim=QColor(0, 0, 0, 130),
        border=QColor(0, 0, 0, 28),
        hover=QColor(0, 0, 0, 14),
        pressed=QColor(0, 0, 0, 26),
        accent=accent,
        accent_fg=QColor("#ffffff"),
        field=QColor(0, 0, 0, 10),
    )


def compositing_available() -> bool:
    """True if translucent windows will render (needed for antialiased
    rounded corners). Without a compositor we fall back to a shape mask."""
    app = QApplication.instance()
    if app is None or app.platformName() != "xcb":
        return True
    try:
        from PyQt5.QtX11Extras import QX11Info  # type: ignore

        return bool(QX11Info.isCompositingManagerRunning())
    except Exception:
        return True


def rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def make_rounded_window(widget: QWidget) -> None:
    """Frameless + translucent, so a painted rounded background shows."""
    widget.setAttribute(Qt.WA_TranslucentBackground, True)
    widget.setAttribute(Qt.WA_NoSystemBackground, True)


def apply_mask_if_needed(widget: QWidget, radius: int = RADIUS) -> None:
    if compositing_available():
        widget.clearMask()
        return
    path = rounded_path(QRectF(widget.rect()), radius)
    widget.setMask(QRegion(path.toFillPolygon().toPolygon()))


def paint_rounded_background(widget: QWidget, colors: Colors, radius: int = RADIUS) -> None:
    p = QPainter(widget)
    p.setRenderHint(QPainter.Antialiasing)
    rect = QRectF(widget.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
    p.setPen(QPen(colors.border, 1))
    bg = QColor(colors.bg)
    if not compositing_available():
        bg.setAlpha(255)
    p.setBrush(bg)
    p.drawPath(rounded_path(rect, radius))
    p.end()


def menu_stylesheet(c: Colors) -> str:
    bg = QColor(c.bg)
    if not compositing_available():
        bg.setAlpha(255)
    return f"""
    QMenu {{
        background-color: {c.css(bg)};
        color: {c.css(c.fg)};
        border: 1px solid {c.css(c.border)};
        border-radius: {RADIUS}px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 7px 28px 7px 12px;
        border-radius: {ITEM_RADIUS}px;
        background: transparent;
    }}
    QMenu::item:selected {{
        background-color: {c.css(c.accent)};
        color: {c.css(c.accent_fg)};
    }}
    QMenu::item:disabled {{ color: {c.css(c.dim)}; }}
    QMenu::icon {{ padding-left: 10px; }}
    QMenu::separator {{
        height: 1px;
        background: {c.css(c.border)};
        margin: 5px 8px;
    }}
    """


def check_image(color: QColor) -> str:
    """Render a check mark PNG once and return its path for use in a stylesheet."""
    import os
    import tempfile

    folder = os.path.join(tempfile.gettempdir(), "deepin-jumplist-images-%d" % os.getuid())
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "check-%s.png" % color.name().lstrip("#"))
    if not os.path.exists(path):
        from PyQt5.QtGui import QPixmap

        pm = QPixmap(32, 32)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(color, 4.5)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        path_ = QPainterPath()
        path_.moveTo(7, 17)
        path_.lineTo(13, 23)
        path_.lineTo(25, 9)
        p.drawPath(path_)
        p.end()
        pm.save(path, "PNG")
    return path


def dialog_stylesheet(c: Colors) -> str:
    return f"""
    QWidget {{ color: {c.css(c.fg)}; font-size: 10pt; }}
    QLabel#dimLabel {{ color: {c.css(c.dim)}; }}
    QLabel#titleLabel {{ font-size: 11pt; font-weight: 600; }}
    QLabel#bigTitle {{ font-size: 16pt; font-weight: 600; }}
    QPushButton {{
        background-color: {c.css(c.field)};
        border: 1px solid {c.css(c.border)};
        border-radius: {ITEM_RADIUS}px;
        padding: 6px 16px;
        min-height: 20px;
    }}
    QPushButton:hover {{ background-color: {c.css(c.hover)}; }}
    QPushButton:pressed {{ background-color: {c.css(c.pressed)}; }}
    QPushButton#primary {{
        background-color: {c.css(c.accent)};
        color: {c.css(c.accent_fg)};
        border: none;
    }}
    QPushButton#primary:hover {{ background-color: {c.css(c.accent.lighter(110))}; }}
    QToolButton#closeButton {{
        border: none; border-radius: {ITEM_RADIUS}px;
        background: transparent; padding: 4px;
        font-size: 12pt;
    }}
    QToolButton#closeButton:hover {{ background-color: #e5484d; color: white; }}
    QSpinBox, QComboBox {{
        background-color: {c.css(c.field)};
        border: 1px solid {c.css(c.border)};
        border-radius: {ITEM_RADIUS}px;
        padding: 4px 8px;
        min-height: 20px;
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background-color: {c.css(QColor(c.bg.red(), c.bg.green(), c.bg.blue()))};
        border: 1px solid {c.css(c.border)};
        border-radius: {ITEM_RADIUS}px;
        selection-background-color: {c.css(c.accent)};
        outline: none;
    }}
    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border-radius: 5px;
        border: 1px solid {c.css(c.dim)};
        background: {c.css(c.field)};
    }}
    QCheckBox::indicator:checked {{
        background: {c.css(c.accent)};
        border: 1px solid {c.css(c.accent)};
        image: url({check_image(c.accent_fg)});
    }}
    QListWidget {{
        background-color: {c.css(c.field)};
        border: 1px solid {c.css(c.border)};
        border-radius: {ITEM_RADIUS}px;
        padding: 4px;
        outline: none;
    }}
    QListWidget::item {{ border-radius: 5px; padding: 4px; }}
    QListWidget::item:selected {{ background: {c.css(c.accent)}; color: {c.css(c.accent_fg)}; }}
    QFrame#separator {{ background: {c.css(c.border)}; max-height: 1px; min-height: 1px; border: none; }}
    """


class RoundedMenu(QMenu):
    """A QMenu with rounded corners (used for the tray and context menus)."""

    def __init__(self, title: str = "", parent: QWidget | None = None, theme_mode: str = "auto"):
        super().__init__(title, parent)
        self.setWindowFlags(
            self.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        make_rounded_window(self)
        self.setStyleSheet(menu_stylesheet(current_colors(theme_mode)))

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        apply_mask_if_needed(self)
