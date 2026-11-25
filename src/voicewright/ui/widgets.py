"""Reusable glass widgets.

Everything is drawn from the active palette, so light and dark mode stay in
sync. Animations are short (150–240 ms) and can be switched off globally with
the ``reduce_motion`` setting.
"""
from __future__ import annotations

import math
from typing import Iterable, Optional

from PySide6.QtCore import (
    Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal,
)
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from voicewright.ui import theme

_motion = True


def set_motion(enabled: bool) -> None:
    global _motion
    _motion = enabled


def motion() -> bool:
    return _motion


def _duration(ms: int) -> int:
    return ms if _motion else 0


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("PageTitle")
    return lbl


def subtitle(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("PageSub")
    lbl.setWordWrap(True)
    return lbl


def section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("SectionTitle")
    return lbl


def muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Muted")
    lbl.setWordWrap(True)
    lbl.setOpenExternalLinks(True)
    lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
    return lbl


def faint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Faint")
    lbl.setWordWrap(True)
    return lbl


class Badge(QLabel):
    def __init__(self, text: str = "", accent: bool = True) -> None:
        super().__init__(text)
        self.setObjectName("Badge" if accent else "BadgeMuted")
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setAlignment(Qt.AlignCenter)

    def set_accent(self, accent: bool) -> None:
        self.setObjectName("Badge" if accent else "BadgeMuted")
        self.style().unpolish(self)
        self.style().polish(self)


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------
class Card(QFrame):
    """A soft panel. ``tone`` is ``card``, ``alt`` or ``hero``."""

    def __init__(self, tone: str = "card", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName({"card": "Card", "alt": "CardAlt", "hero": "Hero"}.get(tone, "Card"))
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 16, 18, 16)
        self.body.setSpacing(10)

    def add_title(self, text: str, hint: str = "") -> QLabel:
        head = QHBoxLayout()
        head.setSpacing(8)
        lbl = section(text)
        head.addWidget(lbl)
        head.addStretch(1)
        self.body.addLayout(head)
        if hint:
            self.body.addWidget(muted(hint))
        return lbl

    def add_row(self, left: QWidget, right: QWidget, spacing: int = 12) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(spacing)
        row.addWidget(left, 1)
        row.addWidget(right)
        self.body.addLayout(row)
        return row


class Separator(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(1)
        p = theme.active()
        self.setStyleSheet(f"background: {p.border}; border: none;")


class Hero(Card):
    """Layered panel with a soft accent glow, used for the main status block."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("hero", parent)
        self.body.setContentsMargins(24, 22, 24, 22)
        self.body.setSpacing(12)
        self.setMinimumHeight(120)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = theme.active()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, theme.RADIUS_CARD, theme.RADIUS_CARD)
        base = QLinearGradient(rect.topLeft(), rect.bottomRight())
        base.setColorAt(0.0, QColor(p.card))
        base.setColorAt(1.0, QColor(p.card_alt))
        painter.fillPath(path, base)

        glow = QLinearGradient(rect.topLeft(), rect.topRight())
        accent = QColor(p.accent)
        accent.setAlphaF(0.16 if p.dark else 0.09)
        glow.setColorAt(0.0, accent)
        glow.setColorAt(0.6, QColor(0, 0, 0, 0))
        painter.fillPath(path, glow)

        painter.setPen(QPen(QColor(p.border_strong), 1))
        painter.drawPath(path)
        painter.end()


class Metric(QWidget):
    def __init__(self, value: str, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("Metric")
        lay.addWidget(self.value_label)
        lay.addWidget(faint(label))

    def set_value(self, text: str) -> None:
        self.value_label.setText(text)


# ---------------------------------------------------------------------------
# Toggle switch
# ---------------------------------------------------------------------------
class ToggleSwitch(QAbstractButton):
    """iOS-style switch. Animates the knob instead of snapping."""

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 26)
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(_duration(170))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, on: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = Property(float, get_offset, set_offset)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(44, 26)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = theme.active()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        track = QRectF(1, 1, w - 2, h - 2)
        radius = track.height() / 2

        off = QColor(p.border_strong)
        on = QColor(p.accent)
        t = self._offset
        color = QColor(
            int(off.red() + (on.red() - off.red()) * t),
            int(off.green() + (on.green() - off.green()) * t),
            int(off.blue() + (on.blue() - off.blue()) * t),
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(track, radius, radius)

        knob_d = h - 6
        x = 3 + t * (w - knob_d - 6)
        knob = QRectF(x, 3, knob_d, knob_d)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(knob)
        painter.end()


# ---------------------------------------------------------------------------
# Segmented control
# ---------------------------------------------------------------------------
class Segmented(QWidget):
    """Rounded group of exclusive options with a sliding highlight."""

    changed = Signal(str)

    def __init__(self, options: Iterable[tuple[str, str]], current: str = "",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Segmented")
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setFixedHeight(34)
        self._items: list[tuple[str, QPushButton]] = []
        self._index = 0
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        for value, label in options:
            btn = QPushButton(label, self)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, v=value: self.set_value(v, emit=True))
            btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; padding: 5px 14px;"
                " font-weight: 600; }")
            lay.addWidget(btn)
            self._items.append((value, btn))
        self._slide = 0.0
        self._anim = QPropertyAnimation(self, b"slide", self)
        self._anim.setDuration(_duration(200))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.set_value(current or (self._items[0][0] if self._items else ""), emit=False)

    def value(self) -> str:
        return self._items[self._index][0] if self._items else ""

    def set_value(self, value: str, emit: bool = False) -> None:
        for i, (val, btn) in enumerate(self._items):
            if val == value:
                self._index = i
                btn.setChecked(True)
            else:
                btn.setChecked(False)
        self._anim.stop()
        self._anim.setStartValue(self._slide)
        self._anim.setEndValue(float(self._index))
        self._anim.start()
        if emit:
            self.changed.emit(value)
        self.update()

    def get_slide(self) -> float:
        return self._slide

    def set_slide(self, value: float) -> None:
        self._slide = float(value)
        self.update()

    slide = Property(float, get_slide, set_slide)

    def paintEvent(self, _event) -> None:  # noqa: N802
        if not self._items:
            return
        p = theme.active()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        radius = rect.height() / 2
        painter.setPen(QPen(QColor(p.border), 1))
        painter.setBrush(QColor(p.field))
        painter.drawRoundedRect(rect, radius, radius)

        idx_lo = max(0, min(len(self._items) - 1, int(math.floor(self._slide))))
        idx_hi = max(0, min(len(self._items) - 1, int(math.ceil(self._slide))))
        frac = self._slide - idx_lo
        g_lo = self._items[idx_lo][1].geometry()
        g_hi = self._items[idx_hi][1].geometry()
        x = g_lo.x() + (g_hi.x() - g_lo.x()) * frac
        w = g_lo.width() + (g_hi.width() - g_lo.width()) * frac
        pill = QRectF(x, 3, max(4.0, float(w)), self.height() - 6)
        painter.setPen(QPen(QColor(p.border_strong), 1))
        painter.setBrush(QColor(p.card))
        painter.drawRoundedRect(pill, pill.height() / 2, pill.height() / 2)
        painter.end()


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
class NavList(QWidget):
    """Vertical sidebar navigation with an accent bar for the active page."""

    selected = Signal(int)

    def __init__(self, labels: Iterable[tuple[str, str]], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._current = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        for glyph, label in labels:
            btn = QPushButton(f"{glyph}   {label}" if glyph else label, self)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 9px 14px; border: none;"
                " border-radius: 10px; background: transparent; color: palette(mid); }"
                "QPushButton:hover { background: rgba(127,127,127,0.10); }"
                "QPushButton:checked { background: rgba(127,127,127,0.14);"
                " font-weight: 650; }")
            btn.clicked.connect(lambda _=False, i=len(self._buttons): self.set_current(i))
            lay.addWidget(btn)
            self._buttons.append(btn)
        lay.addStretch(1)
        self.set_current(0)

    def set_current(self, index: int) -> None:
        if not self._buttons:
            return
        index = max(0, min(index, len(self._buttons) - 1))
        self._current = index
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        self.selected.emit(index)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def hbox(*widgets: QWidget, spacing: int = 10, stretch_last: bool = False) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    for w in widgets:
        lay.addWidget(w)
    if stretch_last:
        lay.addStretch(1)
    return lay


def value_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    font = QFont(lbl.font())
    font.setWeight(QFont.DemiBold)
    lbl.setFont(font)
    return lbl
