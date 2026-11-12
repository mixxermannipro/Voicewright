"""Insert text at the current cursor position of the focused application.

Strategy (configurable):
  * paste     – put text on the clipboard, simulate the paste shortcut, restore clipboard
  * type      – simulate typing every character
  * clipboard – only copy, user pastes manually

Runs on the Qt main thread and uses QTimer for delays so the UI never blocks.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QGuiApplication

from voicewright.config import Config
from voicewright.paths import IS_LINUX, IS_MACOS, session_type

log = logging.getLogger(__name__)

# Linux evdev key codes for ydotool
_YDO = {"ctrl": 29, "shift": 42, "v": 47, "insert": 110, "cmd": 125}


def _which(tool: str) -> Optional[str]:
    return shutil.which(tool)


def _run(cmd: list[str], data: Optional[str] = None, timeout: float = 3.0) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, input=data.encode("utf-8") if data is not None else None,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


class Injector(QObject):
    finished = Signal(bool, str)   # success, message key ("" | "CLIPBOARD_ONLY" | error)

    def __init__(self, config: Config, modifiers_down: Callable[[], bool]) -> None:
        super().__init__()
        self.config = config
        self.modifiers_down = modifiers_down
        self._controller = None
        self._saved_clipboard: Optional[str] = None

    # ------------------------------------------------------------------ clipboard
    def _wayland(self) -> bool:
        return IS_LINUX and session_type() == "wayland"

    def clipboard_get(self) -> str:
        if self._wayland() and _which("wl-paste"):
            try:
                r = _run(["wl-paste", "--no-newline"], timeout=1.5)
                if r.returncode == 0:
                    return r.stdout.decode("utf-8", "replace")
            except Exception:
                pass
        cb = QGuiApplication.clipboard()
        return cb.text() if cb else ""

    def clipboard_set(self, text: str) -> None:
        if self._wayland() and _which("wl-copy"):
            try:
                subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE).communicate(text.encode("utf-8"), timeout=2)
                return
            except Exception as exc:
                log.debug("wl-copy failed: %s", exc)
        cb = QGuiApplication.clipboard()
        if cb:
            cb.setText(text)

    # ------------------------------------------------------------------ key synthesis
    def _linux_tool(self) -> str:
        pref = self.config.get("linux_input_tool", "auto")
        if pref != "auto":
            return pref
        if self._wayland():
            if _which("ydotool"):
                return "ydotool"
            if _which("wtype"):
                return "wtype"
            return "pynput"  # works for XWayland windows only
        return "pynput" if self._pynput() else ("xdotool" if _which("xdotool") else "none")

    def _pynput(self):
        if self._controller is None:
            try:
                from pynput.keyboard import Controller  # type: ignore
                self._controller = Controller()
            except Exception as exc:
                log.warning("pynput controller unavailable: %s", exc)
                self._controller = False
        return self._controller or None

    def _paste_keys(self) -> list[str]:
        sc = self.config.get("paste_shortcut", "auto")
        if sc == "auto":
            return ["cmd", "v"] if IS_MACOS else ["ctrl", "v"]
        return sc.split("+")

    def send_paste(self) -> bool:
        keys = self._paste_keys()
        tool = self._linux_tool() if IS_LINUX else "pynput"
        try:
            if tool == "ydotool":
                seq = [f"{_YDO[k]}:1" for k in keys] + [f"{_YDO[k]}:0" for k in reversed(keys)]
                return _run(["ydotool", "key", *seq]).returncode == 0
            if tool == "wtype":
                mods = [k for k in keys if k in ("ctrl", "shift", "alt", "cmd")]
                key = [k for k in keys if k not in mods][0]
                wmods = {"cmd": "logo"}
                cmd = ["wtype"]
                for m in mods:
                    cmd += ["-M", wmods.get(m, m)]
                cmd += ["-k", "Insert" if key == "insert" else key]
                for m in reversed(mods):
                    cmd += ["-m", wmods.get(m, m)]
                return _run(cmd).returncode == 0
            if tool == "xdotool":
                xk = "+".join({"cmd": "super", "insert": "Insert"}.get(k, k) for k in keys)
                return _run(["xdotool", "key", "--clearmodifiers", xk]).returncode == 0
            ctl = self._pynput()
            if ctl is None:
                return False
            from pynput.keyboard import Key  # type: ignore
            kmap = {"ctrl": Key.ctrl, "shift": Key.shift, "alt": Key.alt, "cmd": Key.cmd, "insert": Key.insert}
            resolved = [kmap.get(k, k) for k in keys]
            for k in resolved:
                ctl.press(k)
            for k in reversed(resolved):
                ctl.release(k)
            return True
        except Exception as exc:
            log.error("Paste simulation failed (%s): %s", tool, exc)
            return False

    def type_text(self, text: str) -> bool:
        tool = self._linux_tool() if IS_LINUX else "pynput"
        try:
            if tool == "ydotool":
                return _run(["ydotool", "type", "--", text], timeout=30).returncode == 0
            if tool == "wtype":
                return _run(["wtype", "--", text], timeout=30).returncode == 0
            if tool == "xdotool":
                return _run(["xdotool", "type", "--clearmodifiers", "--", text], timeout=30).returncode == 0
            ctl = self._pynput()
            if ctl is None:
                return False
            ctl.type(text)
            return True
        except Exception as exc:
            log.error("Typing failed (%s): %s", tool, exc)
            return False

    # ------------------------------------------------------------------ public API
    def insert(self, text: str) -> None:
        if not text:
            self.finished.emit(False, "EMPTY")
            return
        if self.config.get("add_trailing_space", True) and not text.endswith((" ", "\n")):
            text += " "
        self._wait_for_modifiers(text, attempts=0)

    def _wait_for_modifiers(self, text: str, attempts: int) -> None:
        # Pasting while the user still holds Ctrl/Shift/Alt from the hotkey would
        # produce a different shortcut – wait (max ~2s) until they are released.
        if self.modifiers_down() and attempts < 40:
            QTimer.singleShot(50, lambda: self._wait_for_modifiers(text, attempts + 1))
            return
        method = self.config.get("insert_method", "paste")
        if method == "type":
            ok = self.type_text(text)
            if not ok:
                self.clipboard_set(text)
                self.finished.emit(False, "CLIPBOARD_ONLY")
            else:
                self.finished.emit(True, "")
            return
        if method == "clipboard":
            self.clipboard_set(text)
            self.finished.emit(True, "CLIPBOARD_ONLY")
            return
        # paste
        self._saved_clipboard = self.clipboard_get() if self.config.get("restore_clipboard", True) else None
        self.clipboard_set(text)
        delay = int(self.config.get("paste_delay_ms", 120))
        QTimer.singleShot(delay, lambda: self._do_paste(text))

    def _do_paste(self, text: str) -> None:
        ok = self.send_paste()
        if not ok:
            # Leave the text on the clipboard so nothing is lost.
            self.finished.emit(False, "CLIPBOARD_ONLY")
            return
        if self._saved_clipboard is not None:
            saved = self._saved_clipboard
            self._saved_clipboard = None
            QTimer.singleShot(600, lambda: self.clipboard_set(saved))
        self.finished.emit(True, "")
