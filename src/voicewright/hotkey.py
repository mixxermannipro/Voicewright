"""Global hotkey handling with press/release detection (needed for hold-to-talk).

Backends:
  * pynput – Windows, macOS, Linux/X11 (and XWayland apps on Wayland)
  * evdev  – Linux, works on Wayland too (user must be in the `input` group)
  * none   – rely on CLI triggers (`voicewright --toggle`) bound to a DE shortcut
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Callable, Optional

from voicewright.paths import IS_LINUX, IS_MACOS, session_type

log = logging.getLogger(__name__)

MODIFIERS = ("ctrl", "shift", "alt", "cmd")
_ALIASES = {
    "control": "ctrl", "ctl": "ctrl", "strg": "ctrl",
    "option": "alt", "opt": "alt", "altgr": "alt", "alt_gr": "alt",
    "super": "cmd", "win": "cmd", "meta": "cmd", "command": "cmd", "windows": "cmd",
    "escape": "esc", "return": "enter", "spacebar": "space", " ": "space",
}
MOD_SYMBOLS_MAC = {"ctrl": "⌃", "shift": "⇧", "alt": "⌥", "cmd": "⌘"}


def normalize_name(name: str) -> str:
    n = name.strip().lower()
    return _ALIASES.get(n, n)


def parse_hotkey(text: str) -> frozenset[str]:
    keys = [normalize_name(p) for p in text.replace(" ", "").split("+") if p.strip()]
    if not keys:
        raise ValueError("empty hotkey")
    return frozenset(keys)


def format_hotkey(text: str) -> str:
    try:
        keys = parse_hotkey(text)
    except ValueError:
        return ""
    mods = [m for m in MODIFIERS if m in keys]
    rest = sorted(k for k in keys if k not in MODIFIERS)
    if IS_MACOS:
        return "".join(MOD_SYMBOLS_MAC[m] for m in mods) + "".join(k.upper() if len(k) == 1 else k.title() for k in rest)
    labels = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "cmd": "Super"}
    if os.name == "nt":
        labels["cmd"] = "Win"
    return " + ".join([labels[m] for m in mods] + [k.upper() if len(k) == 1 else k.title() for k in rest])


def serialize_hotkey(keys) -> str:
    mods = [m for m in MODIFIERS if m in keys]
    rest = sorted(k for k in keys if k not in MODIFIERS)
    return "+".join(mods + rest)


def validate_hotkey(keys: frozenset[str]) -> Optional[str]:
    """Return an error message (English key) or None if acceptable."""
    if not keys:
        return "Empty shortcut"
    non_mod = [k for k in keys if k not in MODIFIERS]
    mods = [k for k in keys if k in MODIFIERS]
    if not non_mod and len(mods) < 2:
        return "Use at least two modifiers or a modifier plus a key"
    if non_mod and not mods and not any(k.startswith("f") and k[1:].isdigit() for k in non_mod):
        return "Single keys are only allowed for function keys (F1–F24)"
    return None


class ComboDetector:
    """Turns raw key down/up events into activate/deactivate callbacks."""

    def __init__(self) -> None:
        self.combo: frozenset[str] = frozenset()
        self.pressed: set[str] = set()
        self.active = False
        self.on_activate: Optional[Callable[[], None]] = None
        self.on_deactivate: Optional[Callable[[], None]] = None
        self.on_escape: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()

    def set_combo(self, combo: frozenset[str]) -> None:
        with self._lock:
            self.combo = combo
            self.pressed.clear()
            self.active = False

    def press(self, name: Optional[str]) -> None:
        if not name:
            return
        fire = None
        with self._lock:
            self.pressed.add(name)
            if name == "esc" and self.on_escape:
                fire = self.on_escape
            elif (not self.active and self.combo and name in self.combo
                  and self.combo.issubset(self.pressed)
                  # extra modifiers -> different shortcut (e.g. ctrl+alt+shift+space)
                  and not ((self.pressed - self.combo) & set(MODIFIERS))):
                self.active = True
                fire = self.on_activate
        if fire:
            fire()

    def release(self, name: Optional[str]) -> None:
        if not name:
            return
        fire = None
        with self._lock:
            self.pressed.discard(name)
            if self.active and name in self.combo:
                self.active = False
                fire = self.on_deactivate
        if fire:
            fire()

    def modifiers_down(self) -> bool:
        with self._lock:
            return any(m in self.pressed for m in MODIFIERS)

    def reset(self) -> None:
        with self._lock:
            self.pressed.clear()
            self.active = False


# ---------------------------------------------------------------------------
# pynput backend
# ---------------------------------------------------------------------------
class PynputBackend:
    name = "pynput"

    def __init__(self, detector: ComboDetector) -> None:
        from pynput import keyboard  # type: ignore
        self._kb = keyboard
        self.detector = detector
        self._listener = None

    def _key_name(self, key) -> Optional[str]:
        kb = self._kb
        try:
            if self._listener is not None:
                key = self._listener.canonical(key)
        except Exception:
            pass
        if isinstance(key, kb.Key):
            n = key.name  # e.g. ctrl_l, shift_r, alt_gr, cmd, space, f5
            for m in MODIFIERS:
                if n == m or n.startswith(m + "_"):
                    return m
            if n == "alt_gr":
                return "alt"
            return normalize_name(n)
        if isinstance(key, kb.KeyCode):
            if key.char:
                c = key.char
                if len(c) == 1 and ord(c) < 32:  # ctrl+letter control characters
                    c = chr(ord(c) + 96)
                return c.lower()
            vk = getattr(key, "vk", None)
            if vk is not None:
                if os.name == "nt" and (48 <= vk <= 57 or 65 <= vk <= 90):
                    return chr(vk).lower()
                if 97 <= vk <= 122 or 48 <= vk <= 57:
                    return chr(vk)
                return f"vk{vk}"
        return None

    def start(self) -> None:
        self._listener = self._kb.Listener(
            on_press=lambda k: self.detector.press(self._key_name(k)),
            on_release=lambda k: self.detector.release(self._key_name(k)),
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None


class NullBackend:
    name = "none"

    def __init__(self, detector: ComboDetector) -> None:
        self.detector = detector

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


# ---------------------------------------------------------------------------
class HotkeyManager:
    def __init__(self) -> None:
        self.detector = ComboDetector()
        self.backend = None
        self.error = ""

    def start(self, hotkey: str, backend: str = "auto") -> str:
        """Start listening. Returns the backend name actually used."""
        self.stop()
        self.error = ""
        self.detector.set_combo(parse_hotkey(hotkey))
        self.backend = NullBackend(self.detector)
        if IS_LINUX and session_type() == "wayland":
            self.error = "WAYLAND_DESKTOP_SHORTCUT"
            return "none"
        if backend == "none":
            return "none"
        try:
            listener = PynputBackend(self.detector)
            listener.start()
        except Exception:
            self.error = "HOTKEY_UNAVAILABLE"
            log.warning("Global shortcut backend unavailable")
            return "none"
        self.backend = listener
        return "pynput"

    def update_combo(self, hotkey: str) -> None:
        self.detector.set_combo(parse_hotkey(hotkey))

    def stop(self) -> None:
        if self.backend is not None:
            try:
                self.backend.stop()
            except Exception:
                pass
            self.backend = None
