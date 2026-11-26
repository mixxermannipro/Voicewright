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

    # Portal events are already combo-level: the compositor decided that the
    # shortcut was pressed. No key names are involved.
    def press_portal(self) -> None:
        fire = None
        with self._lock:
            if not self.active:
                self.active = True
                fire = self.on_activate
        if fire:
            fire()

    def release_portal(self) -> None:
        fire = None
        with self._lock:
            if self.active:
                self.active = False
                fire = self.on_deactivate
        if fire:
            fire()

    def reset(self) -> None:
        with self._lock:
            self.pressed.clear()
            self.active = False


# ---------------------------------------------------------------------------
# pynput backend
# ---------------------------------------------------------------------------
class PynputBackend:
    name = "pynput"

    def __init__(self, detector: ComboDetector | list[ComboDetector]) -> None:
        from pynput import keyboard  # type: ignore
        self._kb = keyboard
        # One listener feeds every detector (dictation and transform). Each
        # detector ignores shortcuts that carry extra modifiers, so the two
        # combinations cannot fire each other.
        self.detectors = detector if isinstance(detector, list) else [detector]
        self.detector = self.detectors[0]
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
        def press(key) -> None:
            name = self._key_name(key)
            for detector in self.detectors:
                detector.press(name)

        def release(key) -> None:
            name = self._key_name(key)
            for detector in self.detectors:
                detector.release(name)

        self._listener = self._kb.Listener(on_press=press, on_release=release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None


class NullBackend:
    name = "none"

    def __init__(self, detector: ComboDetector | list[ComboDetector]) -> None:
        self.detectors = detector if isinstance(detector, list) else [detector]
        self.detector = self.detectors[0]

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Wayland portal backend
# ---------------------------------------------------------------------------
_XDG_KEYS = {
    "space": "space", "enter": "Return", "tab": "Tab", "esc": "Escape",
    "backspace": "BackSpace", "insert": "Insert", "delete": "Delete",
    "home": "Home", "end": "End", "page_up": "Page_Up", "page_down": "Page_Down",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "pause": "Pause", "scroll_lock": "Scroll_Lock", "caps_lock": "Caps_Lock",
    "print_screen": "Print",
}


def portal_trigger(hotkey: str) -> str:
    """Convert 'ctrl+shift+space' into the XDG shortcuts accelerator.

    The GlobalShortcuts portal parses ``preferred_trigger`` with the XDG
    shortcuts specification: modifiers are upper case (``CTRL``, ``SHIFT``,
    ``ALT``, ``LOGO``), keys keep their XKB names (``a``, ``space``,
    ``Return``, ``F5``). Sending ``SPACE`` instead makes GTK reject the
    trigger and the compositor silently picks another shortcut.
    """
    keys = parse_hotkey(hotkey)
    order = [m for m in MODIFIERS if m in keys]
    rest = sorted(k for k in keys if k not in MODIFIERS)
    names = {"ctrl": "CTRL", "shift": "SHIFT", "alt": "ALT", "cmd": "LOGO"}
    rendered = [_XDG_KEYS.get(k, k.upper() if k.startswith("f") and k[1:].isdigit()
                              else k) for k in rest]
    return "+".join([names[m] for m in order] + rendered)


class PortalBackend:
    """Global shortcuts through org.freedesktop.portal.GlobalShortcuts.

    One portal session carries both the dictation and the rewrite shortcut.
    Opening two sessions would ask the user twice and is rejected by some
    compositors.
    """

    name = "portal"

    def __init__(self, detector: ComboDetector | dict[str, ComboDetector]) -> None:
        from voicewright.portals import GlobalShortcutsPortal
        if isinstance(detector, dict):
            self.detectors = detector
        else:
            self.detectors = {"dictate": detector}
        self.detector = next(iter(self.detectors.values()))
        self._portal = GlobalShortcutsPortal(
            on_press=self._press,
            on_release=self._release,
        )

    def _press(self, shortcut_id: str) -> None:
        detector = self.detectors.get(shortcut_id)
        if detector is not None:
            detector.press_portal()

    def _release(self, shortcut_id: str) -> None:
        detector = self.detectors.get(shortcut_id)
        if detector is not None:
            detector.release_portal()

    def start(self, shortcuts) -> bool:
        if isinstance(shortcuts, str):
            shortcuts = [("dictate", "Dictate", shortcuts)]
        return self._portal.start(shortcuts)

    def stop(self) -> None:
        self._portal.stop()

    @property
    def error(self) -> str:
        return self._portal.error


# ---------------------------------------------------------------------------
def combos_conflict(a: frozenset[str], b: frozenset[str]) -> bool:
    """True if two combinations can fire at the same moment.

    The detector fires a combo as soon as all its keys are held. If one combo
    is a subset or superset of the other, pressing the larger one also fires
    the smaller one — e.g. a modifier-only rewrite shortcut would fire while
    the user holds the dictation prefix.
    """
    return bool(a) and bool(b) and (a <= b or b <= a)


class HotkeyManager:
    def __init__(self) -> None:
        self.detector = ComboDetector()
        self.transform_detector = ComboDetector()
        self.backend = None
        self.error = ""

    def start(self, hotkey: str, backend: str = "auto", wayland: str = "portal",
              transform_hotkey: str = "") -> str:
        """Start listening. Returns the backend name actually used.

        ``transform_hotkey`` is optional. When set, both shortcuts share one
        listener (pynput) or one portal session (Wayland).
        """
        self.stop()
        self.error = ""
        self.detector.set_combo(parse_hotkey(hotkey))
        try:
            transform = parse_hotkey(transform_hotkey) if transform_hotkey else frozenset()
        except ValueError as exc:
            # A broken rewrite shortcut must never disable dictation.
            log.warning("Ignoring invalid transform shortcut %r: %s", transform_hotkey, exc)
            transform = frozenset()
        if combos_conflict(transform, self.detector.combo):
            # Two overlapping combinations cannot mean two things: pressing
            # the larger one would fire both actions. Keep the rewrite
            # shortcut off instead.
            log.warning("Transform shortcut overlaps the dictation shortcut; disabled")
            transform = frozenset()
        self.transform_detector.set_combo(transform)

        detectors = {"dictate": self.detector, "transform": self.transform_detector}

        if IS_LINUX and session_type() == "wayland":
            if wayland == "portal" and backend != "none":
                shortcuts = [("dictate", "Dictate", portal_trigger(hotkey))]
                if transform:
                    shortcuts.append(("transform", "Rewrite selection",
                                       portal_trigger(transform_hotkey)))
                portal = PortalBackend(detectors)
                if portal.start(shortcuts):
                    self.backend = portal
                    return "portal"
                self.error = "PORTAL_UNAVAILABLE"
                log.info("GlobalShortcuts portal unavailable: %s", portal.error)
            else:
                self.error = "WAYLAND_DESKTOP_SHORTCUT"
            self.backend = NullBackend(list(detectors.values()))
            return "none"

        if backend == "none":
            self.backend = NullBackend(list(detectors.values()))
            return "none"
        try:
            listener = PynputBackend(list(detectors.values()))
            listener.start()
        except Exception:
            self.error = "HOTKEY_UNAVAILABLE"
            log.warning("Global shortcut backend unavailable")
            self.backend = NullBackend(list(detectors.values()))
            return "none"
        self.backend = listener
        return "pynput"

    def update_combo(self, hotkey: str, transform_hotkey: str = "") -> None:
        self.detector.set_combo(parse_hotkey(hotkey))
        try:
            transform = parse_hotkey(transform_hotkey) if transform_hotkey else frozenset()
        except ValueError:
            transform = frozenset()
        self.transform_detector.set_combo(
            frozenset() if combos_conflict(transform, self.detector.combo) else transform)

    def stop(self) -> None:
        if self.backend is not None:
            try:
                self.backend.stop()
            except Exception:
                pass
            self.backend = None
