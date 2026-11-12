"""Small floating pill that shows recording / processing state without stealing focus."""
from __future__ import annotations

import math
import sys
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from voicewright.i18n import tr


class Overlay(QWidget):
    W, H = 260, 52

    def __init__(self) -> None:
        super().__init__(None)
        flags = (Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                 | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        if sys.platform == "darwin":
            self.setAttribute(Qt.WA_MacAlwaysShowToolWindow)
        self.resize(self.W, self.H)
        self.state = "idle"          # recording | processing | done | error
        self.message = ""
        self.levels = [0.0] * 22
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
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, self.W - 2, self.H - 2)
        path = QPainterPath()
        path.addRoundedRect(r, self.H / 2 - 1, self.H / 2 - 1)
        p.fillPath(path, QColor(20, 22, 30, 235))
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.drawPath(path)

        colors = {"recording": QColor("#ff4d5e"), "processing": QColor("#7c8cff"),
                  "done": QColor("#3ddc97"), "error": QColor("#ffb020")}
        col = colors.get(self.state, QColor("#888"))
        cx, cy = 26, self.H / 2
        t = time.time()
        if self.state == "recording":
            pulse = 0.5 + 0.5 * math.sin(t * 6)
            p.setBrush(QColor(col.red(), col.green(), col.blue(), int(70 + 80 * pulse)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, cy), 11, 11)
            p.setBrush(col)
            p.drawEllipse(QPointF(cx, cy), 6, 6)
            # waveform
            bw, gap = 4, 3
            x0 = 48
            p.setBrush(QColor(255, 255, 255, 220))
            for i, lv in enumerate(self.levels):
                h = max(3.0, lv * (self.H - 20))
                p.drawRoundedRect(QRectF(x0 + i * (bw + gap), cy - h / 2, bw, h), 2, 2)
            elapsed = int(time.time() - self._t0)
            p.setPen(QColor(255, 255, 255, 200))
            p.setFont(QFont(self.font().family(), 9))
            p.drawText(QRectF(self.W - 50, 0, 40, self.H), Qt.AlignVCenter | Qt.AlignRight,
                       f"{elapsed // 60}:{elapsed % 60:02d}")
        else:
            p.setPen(Qt.NoPen)
            if self.state == "processing":
                for i in range(3):
                    a = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(t * 7 - i * 0.9))
                    c = QColor(col)
                    c.setAlphaF(a)
                    p.setBrush(c)
                    p.drawEllipse(QPointF(cx - 8 + i * 8, cy), 3.2, 3.2)
            else:
                p.setBrush(col)
                p.drawEllipse(QPointF(cx, cy), 6, 6)
            p.setPen(QColor(255, 255, 255, 230))
            f = QFont(self.font().family(), 10)
            p.setFont(f)
            text = self.message or {"processing": tr("Transcribing…"), "done": tr("Inserted"),
                                    "error": tr("Error")}.get(self.state, "")
            metrics = p.fontMetrics()
            text = metrics.elidedText(text, Qt.ElideRight, self.W - 64)
            p.drawText(QRectF(48, 0, self.W - 60, self.H), Qt.AlignVCenter | Qt.AlignLeft, text)
        p.end()
