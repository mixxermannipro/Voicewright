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
        self.portal = RemoteDesktopPortal(on_restore_token=self._store_restore_token)
        self._saved_clipboard: str | None = None
        self._inserted_text: str | None = None
        self._restore_timer = QTimer(self)
        self._restore_timer.setSingleShot(True)
        self._restore_timer.timeout.connect(self._restore_clipboard)

    def _store_restore_token(self, token: str) -> None:
        self.config.set("wayland_restore_token", token)

    # ------------------------------------------------------------------
    def _wants_portal(self) -> bool:
        if not IS_LINUX or session_type() != "wayland":
            return False
        return self.config.get("wayland_inject", "portal") == "portal"

    def _paste_shortcut(self) -> bool:
        return self.config.get("paste_shortcut", "auto") == "ctrl_shift_v"

    def _delay_ms(self) -> int:
        # A short delay lets the clipboard owner publish the new content before
        # the target application reads it. Windows and X11 need more time than
        # macOS because the clipboard hand-off goes through the OS.
        if IS_MACOS:
            return 40
        return 120 if IS_WINDOWS else 80

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
        # Finish a pending restore first; otherwise the new insert would save
        # the previous dictation as "previous clipboard" and lose the content
        # the user had before either dictation.
        if self._restore_timer.isActive():
            self._restore_timer.stop()
            self._restore_clipboard()
        self._saved_clipboard = clipboard.text()
        self._inserted_text = text
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
        saved, inserted = self._saved_clipboard, self._inserted_text
        self._saved_clipboard = None
        self._inserted_text = None
        if clipboard is None or saved is None:
            return
        current = clipboard.text()
        if inserted is not None and current != inserted:
            # The user copied something in the meantime: never overwrite it.
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

    def restore_portal(self, timeout: float = 8.0) -> bool:
        """Reconnect with the stored restore token at startup.

        A valid token restores the session without another consent dialog.
        The portal contract says a revoked token is ignored and the compositor
        may ask again; if that dialog is declined or times out, the stale token
        is cleared so the next start does not keep retrying it.
        """
        if not self._wants_portal():
            return False
        token = str(self.config.get("wayland_restore_token", "") or "")
        if not token:
            return False
        ok = self.portal.connect(timeout, restore_token=token)
        if ok:
            self.config.set("wayland_consent", True)
        else:
            log.info("Stored Wayland permission is no longer valid; clearing token")
            self.config.set("wayland_restore_token", "")
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
