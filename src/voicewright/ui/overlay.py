"""Liquid-glass floating pill showing recording/processing state without stealing focus."""
from __future__ import annotations

import math
import sys
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor, QCursor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QWidget

from voicewright.i18n import tr
from voicewright.ui import theme


class Overlay(QWidget):
    W, H = 300, 64

    def __init__(self) -> None:
        super().__init__(None)
        flags = (
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
            | Qt.WindowTransparentForInput
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        if sys.platform == "darwin":
            self.setAttribute(Qt.WA_MacAlwaysShowToolWindow)
        self.resize(self.W, self.H)
        self.state = "idle"          # recording | processing | done | error
        self.message = ""
        self.levels = [0.0] * 24
        self._level = 0.0
        self._t0 = time.time()
        self.position = "bottom"
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    # ------------------------------------------------------------------
    def _place(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.W) // 2
        y = geo.y() + 40 if self.position == "top" else geo.y() + geo.height() - self.H - 60
        self.move(x, y)

    def show_state(self, state: str, message: str = "", auto_hide_ms: int = 0) -> None:
        self.state = state
        self.message = message
        if state == "recording":
            self._t0 = time.time()
            self.levels = [0.0] * len(self.levels)
        self._hide_timer.stop()
        self._place()
        if not self.isVisible():
            self.show()
        self._timer.start(33)
        if auto_hide_ms:
            self._hide_timer.start(auto_hide_ms)
        self.update()

    def set_level(self, rms: float) -> None:
        self._level = max(self._level * 0.6, min(1.0, rms * 12))

    def hideEvent(self, e) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(e)

    def _tick(self) -> None:
        if self.state == "recording":
            self.levels = self.levels[1:] + [self._level]
            self._level *= 0.85
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, _e) -> None:  # noqa: N802
        pal = theme.active()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(1.0, 1.0, self.W - 2.0, self.H - 2.0)
        radius = rect.height() / 2.0
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        # Layered translucent glass background
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        c_top = QColor(pal.card)
        c_bot = QColor(pal.card_alt)
        c_top.setAlpha(238 if pal.dark else 242)
        c_bot.setAlpha(224 if pal.dark else 230)
        grad.setColorAt(0.0, c_top)
        grad.setColorAt(1.0, c_bot)
        p.fillPath(path, grad)

        # Soft upper glass highlight
        highlight = QLinearGradient(rect.topLeft(), QPointF(rect.left(), rect.center().y()))
        hi_top = QColor(255, 255, 255, 28 if pal.dark else 110)
        hi_mid = QColor(255, 255, 255, 0)
        highlight.setColorAt(0.0, hi_top)
        highlight.setColorAt(1.0, hi_mid)
        p.fillPath(path, highlight)

        border = QColor(pal.border_strong)
        border.setAlpha(180 if pal.dark else 210)
        p.setPen(QPen(border, 1.0))
        p.drawPath(path)

        colors = {
            "recording": QColor(pal.danger),
            "processing": QColor(pal.accent),
            "done": QColor(pal.success),
            "error": QColor(pal.warning),
        }
        col = colors.get(self.state, QColor(pal.text_muted))
        cx, cy = 30.0, self.H / 2.0
        t = time.time()

        if self.state == "recording":
            pulse = 0.5 + 0.5 * math.sin(t * 6.0)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(col.red(), col.green(), col.blue(), int(55 + 75 * pulse)))
            p.drawEllipse(QPointF(cx, cy), 12.5, 12.5)
            p.setBrush(col)
            p.drawEllipse(QPointF(cx, cy), 6.0, 6.0)

            bw, gap = 4.0, 3.0
            x0 = 54.0
            bar_col = QColor(pal.text)
            bar_col.setAlpha(215)
            p.setBrush(bar_col)
            for i, lv in enumerate(self.levels):
                h = max(3.5, lv * (self.H - 24.0))
                p.drawRoundedRect(QRectF(x0 + i * (bw + gap), cy - h / 2.0, bw, h), 2.0, 2.0)

            elapsed = int(time.time() - self._t0)
            p.setPen(QColor(pal.text_muted))
            font = QFont(self.font())
            font.setPointSize(9)
            font.setWeight(QFont.DemiBold)
            p.setFont(font)
            p.drawText(
                QRectF(self.W - 56.0, 0.0, 42.0, float(self.H)),
                Qt.AlignVCenter | Qt.AlignRight,
                f"{elapsed // 60}:{elapsed % 60:02d}",
            )
        else:
            p.setPen(Qt.NoPen)
            if self.state == "processing":
                for i in range(3):
                    a = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(t * 7.0 - i * 0.9))
                    c = QColor(col)
                    c.setAlphaF(a)
                    p.setBrush(c)
                    p.drawEllipse(QPointF(cx - 8.0 + i * 8.0, cy), 3.4, 3.4)
            else:
                p.setBrush(col)
                p.drawEllipse(QPointF(cx, cy), 6.5, 6.5)

            p.setPen(QColor(pal.text))
            font = QFont(self.font())
            font.setPointSize(10)
            font.setWeight(QFont.Medium)
            p.setFont(font)
            text = self.message or {
                "processing": tr("Transcribing…"),
                "done": tr("Inserted"),
                "error": tr("Error"),
            }.get(self.state, "")
            metrics = p.fontMetrics()
            text = metrics.elidedText(text, Qt.ElideRight, self.W - 72)
            p.drawText(
                QRectF(54.0, 0.0, self.W - 70.0, float(self.H)),
                Qt.AlignVCenter | Qt.AlignLeft,
                text,
            )
        p.end()
