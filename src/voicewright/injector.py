"""Insert a finished dictation into the focused window.

Runs on the Qt main thread. The clipboard is saved, used for the paste and
restored afterwards, but only if the user has not changed it in the meantime.

Failure is never fatal: the text stays in the clipboard and the UI says so.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QGuiApplication

from voicewright import inject
from voicewright.config import Config
from voicewright.paths import IS_LINUX, IS_MACOS, IS_WINDOWS, session_type
from voicewright.portals import RemoteDesktopPortal

log = logging.getLogger(__name__)


class Injector(QObject):
    finished = Signal(bool, str)          # ok, method or error code
    permission_hint = Signal(str)

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.portal = RemoteDesktopPortal()
        self._saved_clipboard: str | None = None
        self._restore_timer = QTimer(self)
        self._restore_timer.setSingleShot(True)
        self._restore_timer.timeout.connect(self._restore_clipboard)

    # ------------------------------------------------------------------
    def _wants_portal(self) -> bool:
        if not IS_LINUX or session_type() != "wayland":
            return False
        return self.config.get("wayland_inject", "portal") == "portal"

    def _paste_shortcut(self) -> bool:
        return self.config.get("paste_shortcut", "auto") == "ctrl_shift_v"

    def _delay_ms(self) -> int:
        # A short delay lets the clipboard owner publish the new content before
        # the target application reads it.
        return 70 if IS_LINUX else 40

    # ------------------------------------------------------------------
    def insert(self, text: str) -> None:
        if not text:
            self.finished.emit(False, "EMPTY")
            return
        if self.config.get("add_trailing_space", True) and not text.endswith((" ", "\n")):
            text += " "

        mode = self.config.get("insert_mode", "auto")
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            self.finished.emit(False, "COPY_FAILED")
            return

        if mode == "clipboard":
            clipboard.setText(text)
            self.finished.emit(True, "CLIPBOARD_ONLY")
            return

        if mode == "type":
            method = inject.type_text(
                text,
                wayland=self.config.get("wayland_inject", "auto"),
                ydotool=bool(self.config.get("ydotool_enabled", False)),
            )
            if method:
                self.finished.emit(True, method)
            else:
                clipboard.setText(text)
                self.finished.emit(True, "CLIPBOARD_ONLY")
            return

        # Paste path: clipboard + simulated shortcut.
        self._saved_clipboard = clipboard.text()
        clipboard.setText(text)
        QTimer.singleShot(self._delay_ms(), lambda: self._do_paste(text))

    def _do_paste(self, text: str) -> None:
        ctrl_shift = self._paste_shortcut()
        portal_paste = None
        if self._wants_portal():
            if self.portal.connected:
                portal_paste = self.portal.paste
            else:
                log.info("Wayland portal not connected; using helper or clipboard")

        method = inject.paste(
            ctrl_shift=ctrl_shift,
            wayland=self.config.get("wayland_inject", "auto"),
            ydotool=bool(self.config.get("ydotool_enabled", False)),
            portal_paste=portal_paste,
        )

        if method:
            if self.config.get("restore_clipboard", True):
                self._restore_timer.start(int(self.config.get("clipboard_restore_ms", 400)))
            self.finished.emit(True, method)
            return

        # Nothing worked: keep the text in the clipboard.
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
        self.finished.emit(True, "CLIPBOARD_ONLY")
        if IS_MACOS:
            self.permission_hint.emit(inject.accessibility_hint())

    def _restore_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return
        current = clipboard.text()
        saved = self._saved_clipboard
        self._saved_clipboard = None
        if saved is None or current != saved:
            # The user copied something in the meantime: never overwrite it.
            if saved is not None and current.rstrip() == saved.rstrip():
                pass
            else:
                return
        clipboard.setText(saved)

    # ------------------------------------------------------------------
    def connect_portal(self, timeout: float = 90.0) -> bool:
        """Ask the compositor for keyboard control (shows a system dialog)."""
        ok = self.portal.connect(timeout)
        if not ok:
            self.permission_hint.emit(
                "Wayland keyboard control was not granted. Voicewright will use "
                "wtype or the clipboard instead.")
        return ok

    def describe_method(self) -> str:
        if IS_WINDOWS:
            return "Windows SendInput"
        if IS_MACOS:
            return "macOS CGEvent"
        if IS_LINUX and session_type() == "wayland":
            if self.portal.connected:
                return "Wayland portal"
            if inject.wayland_tool("wtype"):
                return "wtype"
            return "Clipboard (install wtype or grant the portal)"
        return "X11 XTEST"
