"""Design tokens and the global stylesheet.

The look is calm and Apple-like: layered translucency instead of heavy blur,
one accent colour, generous spacing, 180–260 ms easing. Everything is painted
from a single token list so light and dark mode can never drift apart.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QFont, QGuiApplication

EASE = "cubic-bezier(0.22, 1, 0.36, 1)"

RADIUS_WINDOW = 22
RADIUS_CARD = 18
RADIUS_CONTROL = 10


@dataclass(frozen=True)
class Palette:
    dark: bool
    window: str
    window_alt: str
    sidebar: str
    card: str
    card_alt: str
    border: str
    border_strong: str
    text: str
    text_muted: str
    text_faint: str
    accent: str
    accent_hover: str
    accent_soft: str
    danger: str
    success: str
    warning: str
    shadow: str
    field: str
    selection: str


LIGHT = Palette(
    dark=False,
    window="#f4f5f8",
    window_alt="#eceef4",
    sidebar="#ffffff",
    card="#ffffff",
    card_alt="#f7f8fc",
    border="#e3e6ef",
    border_strong="#d3d7e4",
    text="#171a21",
    text_muted="#5c6273",
    text_faint="#8b91a3",
    accent="#5b5bf0",
    accent_hover="#4a4ae0",
    accent_soft="#ececfe",
    danger="#e5484d",
    success="#18a058",
    warning="#c98a12",
    shadow="rgba(23, 26, 33, 0.10)",
    field="#f2f3f8",
    selection="#dcdcff",
)

DARK = Palette(
    dark=True,
    window="#121318",
    window_alt="#171922",
    sidebar="#171922",
    card="#1c1f2a",
    card_alt="#222633",
    border="#2a2f3d",
    border_strong="#39404f",
    text="#f2f3f7",
    text_muted="#a7adbe",
    text_faint="#767d90",
    accent="#8b8bff",
    accent_hover="#9d9dff",
    accent_soft="#262650",
    danger="#ff6369",
    success="#3ddc97",
    warning="#f0b429",
    shadow="rgba(0, 0, 0, 0.45)",
    field="#232734",
    selection="#34346a",
)


def system_is_dark() -> bool:
    try:
        hints = QGuiApplication.styleHints()
        if hints is not None and hasattr(hints, "colorScheme"):
            return hints.colorScheme() == hints.ColorScheme.Dark
    except Exception:
        pass
    return False


def resolve(theme: str) -> Palette:
    if theme == "dark":
        return DARK
    if theme == "light":
        return LIGHT
    return DARK if system_is_dark() else LIGHT


_active: Palette | None = None


def set_active(palette: Palette) -> None:
    """Remember the palette the window was built with."""
    global _active
    _active = palette


def active() -> Palette:
    return _active if _active is not None else resolve("system")


def base_font() -> QFont:
    font = QFont()
    font.setPointSize(10)
    return font


def qss(p: Palette) -> str:
    """Global stylesheet. Object names and properties drive the variants."""
    return f"""
    QWidget {{
        color: {p.text};
        font-size: 13px;
    }}
    QMainWindow, #Root {{
        background: {p.window};
    }}
    #Sidebar {{
        background: {p.sidebar};
        border-right: 1px solid {p.border};
    }}
    #Brand {{
        font-size: 16px;
        font-weight: 700;
        letter-spacing: 0.2px;
    }}
    #BrandSub {{
        color: {p.text_faint};
        font-size: 11px;
    }}
    #PageTitle {{
        font-size: 26px;
        font-weight: 700;
        letter-spacing: -0.4px;
    }}
    #PageSub {{
        color: {p.text_muted};
        font-size: 13px;
    }}
    #SectionTitle {{
        font-size: 14px;
        font-weight: 650;
    }}
    #Muted {{
        color: {p.text_muted};
        font-size: 12px;
    }}
    #Faint {{
        color: {p.text_faint};
        font-size: 11px;
    }}
    #Metric {{
        font-size: 22px;
        font-weight: 700;
    }}
    #Badge {{
        background: {p.accent_soft};
        color: {p.accent};
        border-radius: 9px;
        padding: 3px 9px;
        font-size: 11px;
        font-weight: 600;
    }}
    #BadgeMuted {{
        background: {p.field};
        color: {p.text_muted};
        border-radius: 9px;
        padding: 3px 9px;
        font-size: 11px;
        font-weight: 600;
    }}
    #Card {{
        background: {p.card};
        border: 1px solid {p.border};
        border-radius: {RADIUS_CARD}px;
    }}
    #CardAlt {{
        background: {p.card_alt};
        border: 1px solid {p.border};
        border-radius: {RADIUS_CARD}px;
    }}
    #Hero {{
        background: {p.card};
        border: 1px solid {p.border_strong};
        border-radius: {RADIUS_CARD}px;
    }}
    QPushButton {{
        background: {p.field};
        border: 1px solid {p.border};
        border-radius: {RADIUS_CONTROL}px;
        padding: 7px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        border-color: {p.border_strong};
    }}
    QPushButton:pressed {{
        background: {p.window_alt};
    }}
    QPushButton:disabled {{
        color: {p.text_faint};
        background: {p.card_alt};
    }}
    QPushButton#Primary {{
        background: {p.accent};
        color: white;
        border: 1px solid {p.accent};
        padding: 9px 18px;
    }}
    QPushButton#Primary:hover {{
        background: {p.accent_hover};
        border-color: {p.accent_hover};
    }}
    QPushButton#Danger {{
        color: {p.danger};
        background: transparent;
        border: 1px solid {p.border};
    }}
    QPushButton#Danger:hover {{
        border-color: {p.danger};
    }}
    QPushButton#Ghost {{
        background: transparent;
        border: 1px solid transparent;
        color: {p.text_muted};
        padding: 6px 10px;
    }}
    QPushButton#Ghost:hover {{
        background: {p.field};
        color: {p.text};
    }}
    QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {{
        background: {p.field};
        border: 1px solid {p.border};
        border-radius: {RADIUS_CONTROL}px;
        padding: 7px 10px;
        selection-background-color: {p.selection};
        selection-color: {p.text};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {p.accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background: {p.card};
        border: 1px solid {p.border};
        border-radius: 10px;
        selection-background-color: {p.accent_soft};
        selection-color: {p.text};
        padding: 4px;
        outline: none;
    }}
    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1px solid {p.border_strong};
        background: {p.field};
    }}
    QCheckBox::indicator:checked {{
        background: {p.accent};
        border-color: {p.accent};
    }}
    QListWidget {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        border-radius: 10px;
        padding: 9px 12px;
        margin: 2px 0;
        color: {p.text_muted};
    }}
    QListWidget::item:selected {{
        background: {p.accent_soft};
        color: {p.accent};
    }}
    QListWidget::item:hover:!selected {{
        background: {p.field};
        color: {p.text};
    }}
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border_strong};
        border-radius: 5px;
        min-height: 28px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p.border_strong};
        border-radius: 5px;
        min-width: 28px;
    }}
    QToolTip {{
        background: {p.card};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px 8px;
    }}
    QGroupBox {{
        border: 1px solid {p.border};
        border-radius: {RADIUS_CARD}px;
        margin-top: 14px;
        padding: 16px 14px 12px 14px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 6px;
        color: {p.text_muted};
        font-size: 12px;
    }}
    """


def alpha(color: str, a: float) -> QColor:
    c = QColor(color)
    c.setAlphaF(max(0.0, min(1.0, a)))
    return c
