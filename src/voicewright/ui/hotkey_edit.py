"""A button that records a keyboard shortcut when clicked."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QPushButton

from voicewright.hotkey import format_hotkey, serialize_hotkey, validate_hotkey
from voicewright.i18n import tr
from voicewright.paths import IS_MACOS

_QT_KEYS = {
    Qt.Key_Space: "space", Qt.Key_Return: "enter", Qt.Key_Enter: "enter", Qt.Key_Tab: "tab",
    Qt.Key_Backspace: "backspace", Qt.Key_Insert: "insert", Qt.Key_Delete: "delete",
    Qt.Key_Home: "home", Qt.Key_End: "end", Qt.Key_PageUp: "page_up", Qt.Key_PageDown: "page_down",
    Qt.Key_Up: "up", Qt.Key_Down: "down", Qt.Key_Left: "left", Qt.Key_Right: "right",
    Qt.Key_Pause: "pause", Qt.Key_ScrollLock: "scroll_lock", Qt.Key_CapsLock: "caps_lock",
    Qt.Key_Print: "print_screen",
}
_MOD_KEYS = {Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_AltGr, Qt.Key_Super_L, Qt.Key_Super_R}


def _mods(modifiers) -> set[str]:
    out = set()
    ctrl, meta = ("cmd", "ctrl") if IS_MACOS else ("ctrl", "cmd")
    if modifiers & Qt.ControlModifier:
        out.add(ctrl)
    if modifiers & Qt.MetaModifier:
        out.add(meta)
    if modifiers & Qt.ShiftModifier:
        out.add("shift")
    if modifiers & Qt.AltModifier:
        out.add("alt")
    return out


def _mod_from_key(key) -> str:
    if key == Qt.Key_Control:
        return "cmd" if IS_MACOS else "ctrl"
    if key in (Qt.Key_Meta, Qt.Key_Super_L, Qt.Key_Super_R):
        return "ctrl" if IS_MACOS else "cmd"
    if key == Qt.Key_Shift:
        return "shift"
    return "alt"


class HotkeyEdit(QPushButton):
    hotkeyChanged = Signal(str)
    error = Signal(str)
    capturingChanged = Signal(bool)

    def __init__(self, hotkey: str, parent=None) -> None:
        super().__init__(parent)
        self.hotkey = hotkey
        self.capturing = False
        self._held: set[str] = set()
        self._peak: set[str] = set()
        self.setMinimumWidth(220)
        self.setFocusPolicy(Qt.StrongFocus)
        self.clicked.connect(self._begin)
        self._refresh()

    def _refresh(self) -> None:
        if self.capturing:
            self.setText(tr("Press shortcut…  (Esc = cancel)"))
        else:
            self.setText(format_hotkey(self.hotkey) or tr("Not set"))

    def set_hotkey(self, hotkey: str) -> None:
        self.hotkey = hotkey
        self._refresh()

    def _begin(self) -> None:
        self.capturing = True
        self._held.clear()
        self._peak.clear()
        self.grabKeyboard()
        self.capturingChanged.emit(True)
        self._refresh()

    def _end(self, combo: set[str] | None) -> None:
        self.capturing = False
        self.releaseKeyboard()
        self.capturingChanged.emit(False)
        if combo:
            err = validate_hotkey(frozenset(combo))
            if err:
                self.error.emit(tr(err))
            else:
                self.hotkey = serialize_hotkey(combo)
                self.hotkeyChanged.emit(self.hotkey)
        self._refresh()

    def keyPressEvent(self, e) -> None:  # noqa: N802
        if not self.capturing:
            return super().keyPressEvent(e)
        if e.isAutoRepeat():
            return
        key = e.key()
        if key == Qt.Key_Escape and not e.modifiers():
            self._end(None)
            return
        if key in _MOD_KEYS:
            self._held.add(_mod_from_key(key))
            self._peak = set(self._held) | _mods(e.modifiers())
            return
        name = _QT_KEYS.get(key)
        if name is None and Qt.Key_F1 <= key <= Qt.Key_F35:
            name = f"f{key - Qt.Key_F1 + 1}"
        if name is None:
            # Use the unshifted key for letters/digits
            if Qt.Key_A <= key <= Qt.Key_Z or Qt.Key_0 <= key <= Qt.Key_9:
                name = chr(key).lower()
            else:
                txt = e.text().lower()
                name = txt if txt and txt.isprintable() and txt.strip() else None
        if name is None:
            return
        self._end(_mods(e.modifiers()) | {name})

    def keyReleaseEvent(self, e) -> None:  # noqa: N802
        if not self.capturing:
            return super().keyReleaseEvent(e)
        if e.isAutoRepeat():
            return
        if e.key() in _MOD_KEYS:
            self._held.discard(_mod_from_key(e.key()))
            if not self._held and len(self._peak) >= 2:
                self._end(set(self._peak))   # modifier-only shortcut, e.g. Ctrl+Alt
            elif not self._held:
                self._peak.clear()

    def focusOutEvent(self, e) -> None:  # noqa: N802
        if self.capturing:
            self._end(None)
        super().focusOutEvent(e)
