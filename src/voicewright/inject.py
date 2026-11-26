"""Platform keyboard injection: paste a clipboard payload or type text directly.

Every backend is optional. A failure never raises into the UI: the caller gets
``False`` and falls back to the next method, ending at the clipboard.

Platforms
---------
* Windows  – ``SendInput`` (no extra dependency)
* macOS    – ``CGEventPost`` (needs Accessibility permission)
* X11      – XTEST via ``python-xlib``, else ``xdotool``
* Wayland  – portal (see ``portals.py``), ``wtype``, opt-in ``ydotool``
"""
from __future__ import annotations

import ctypes
import ctypes.util
import logging
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

from voicewright.paths import session_type

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


class InjectionError(Exception):
    """Raised only by low-level helpers; public entry points return bool."""


@dataclass(frozen=True)
class Method:
    id: str
    label: str
    needs_clipboard: bool = True


def _run(cmd: list[str], text: Optional[str] = None, timeout: float = 8.0) -> bool:
    if not shutil.which(cmd[0]):
        return False
    try:
        result = subprocess.run(
            cmd,
            input=text.encode("utf-8") if text is not None else None,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            log.debug("Command %s exited with %s", cmd[0], result.returncode)
            return False
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        log.debug("Command %s failed: %s", cmd[0], exc)
        return False


# ---------------------------------------------------------------------------
# Windows – SendInput
# ---------------------------------------------------------------------------
# Win32 types with fixed widths. ``ctypes.wintypes`` maps LONG/DWORD to the
# host C types, which are 64-bit on Linux; building the structures with
# explicit 16/32/64-bit fields keeps the layout correct on every host and
# makes the size testable without Windows.
_WORD = ctypes.c_uint16
_DWORD = ctypes.c_uint32
_LONG = ctypes.c_int32
_ULONG_PTR = ctypes.c_uint64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_uint32

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", _LONG),
        ("dy", _LONG),
        ("mouseData", _DWORD),
        ("dwFlags", _DWORD),
        ("time", _DWORD),
        ("dwExtraInfo", _ULONG_PTR),
    ]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", _WORD),
        ("wScan", _WORD),
        ("dwFlags", _DWORD),
        ("time", _DWORD),
        ("dwExtraInfo", _ULONG_PTR),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", _DWORD),
        ("wParamL", _WORD),
        ("wParamH", _WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", _DWORD), ("union", _INPUTUNION)]


def _windows_structs():
    """Expose the structures for the size/layout regression test."""
    return _KEYBDINPUT, _INPUT


_user32 = None


def _get_user32():
    global _user32
    if _user32 is None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)  # type: ignore[attr-defined]
        user32.SendInput.argtypes = (ctypes.c_uint, ctypes.POINTER(_INPUT), ctypes.c_int)
        user32.SendInput.restype = ctypes.c_uint
        _user32 = user32
    return _user32


def _utf16_units(text: str) -> list[int]:
    """UTF-16 code units, so emoji and other astral characters work."""
    raw = text.encode("utf-16-le")
    return [int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw), 2)]


def _windows_send(vk: int, down: bool, scan: int = 0, unicode_char: Optional[str] = None,
                  unicode_unit: Optional[int] = None) -> bool:
    flags = 0 if down else KEYEVENTF_KEYUP
    if unicode_char is not None or unicode_unit is not None:
        flags |= KEYEVENTF_UNICODE
        vk = 0
        scan = unicode_unit if unicode_unit is not None else ord(unicode_char or "")
    item = _INPUT(type=INPUT_KEYBOARD)
    item.union.ki = _KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
    sent = _get_user32().SendInput(1, ctypes.byref(item), ctypes.sizeof(_INPUT))
    if sent != 1:
        raise OSError(ctypes.get_last_error(), "SendInput failed")
    return True


def _windows_paste(ctrl_shift: bool = False, key: str = "v") -> bool:
    VK_CONTROL, VK_SHIFT = 0x11, 0x10
    VK_KEY = ord(key.upper())
    pressed: list[int] = []
    try:
        _windows_send(VK_CONTROL, True)
        pressed.append(VK_CONTROL)
        time.sleep(0.01)
        if ctrl_shift:
            _windows_send(VK_SHIFT, True)
            pressed.append(VK_SHIFT)
            time.sleep(0.01)
        _windows_send(VK_KEY, True)
        pressed.append(VK_KEY)
        time.sleep(0.01)
        _windows_send(VK_KEY, False)
        pressed.remove(VK_KEY)
        if ctrl_shift:
            _windows_send(VK_SHIFT, False)
            pressed.remove(VK_SHIFT)
        _windows_send(VK_CONTROL, False)
        pressed.remove(VK_CONTROL)
        return True
    except Exception as exc:  # noqa: BLE001
        log.debug("SendInput paste failed: %s", exc)
        # Never leave Ctrl or Shift held down after a partial sequence.
        for vk in reversed(pressed):
            try:
                _windows_send(vk, False)
            except Exception:  # noqa: BLE001
                pass
        return False


def _windows_type(text: str) -> bool:
    try:
        for ch in text:
            if ch == "\n":
                _windows_send(0x0D, True)
                _windows_send(0x0D, False)
            elif ch == "\t":
                _windows_send(0x09, True)
                _windows_send(0x09, False)
            else:
                # A surrogate pair (emoji, rare scripts) must go down as one
                # pair and up again; keyup between the halves produces garbage.
                units = _utf16_units(ch)
                for unit in units:
                    _windows_send(0, True, unicode_unit=unit)
                for unit in reversed(units):
                    _windows_send(0, False, unicode_unit=unit)
        return True
    except Exception as exc:  # noqa: BLE001
        log.debug("SendInput type failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# macOS – CGEvent
# ---------------------------------------------------------------------------
_CG = None


def _cg():
    global _CG
    if _CG is None:
        try:
            _CG = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
            )
        except OSError:
            _CG = False
    return _CG


_MAC_KEYCODES = {"v": 9, "c": 8, "x": 7, "a": 0}


def _macos_paste(ctrl_shift: bool = False, key: str = "v") -> bool:
    cg = _cg()
    if not cg:
        return False
    try:
        kCGHIDEventTap = 0
        kCGEventFlagMaskCommand = 1 << 20
        kCGEventFlagMaskShift = 1 << 17
        key_v = _MAC_KEYCODES.get(key.lower(), 9)
        for down in (True, False):
            ev = cg.CGEventCreateKeyboardEvent(None, key_v, down)
            if not ev:
                return False
            flags = kCGEventFlagMaskCommand
            if ctrl_shift:
                flags |= kCGEventFlagMaskShift
            cg.CGEventSetFlags(ev, flags)
            cg.CGEventPost(kCGHIDEventTap, ev)
            cg.CFRelease(ev)
        return True
    except Exception as exc:  # noqa: BLE001
        log.debug("CGEvent paste failed: %s", exc)
        return False


def _macos_type(text: str) -> bool:
    cg = _cg()
    if not cg:
        return False
    try:
        kCGHIDEventTap = 0
        for ch in text:
            for down in (True, False):
                ev = cg.CGEventCreateKeyboardEvent(None, 0, down)
                if not ev:
                    return False
                buf = ctypes.create_string_buffer(ch.encode("utf-16-le"))
                cg.CGEventKeyboardSetUnicodeString(ev, len(ch.encode("utf-16-le")) // 2, buf)
                cg.CGEventPost(kCGHIDEventTap, ev)
                cg.CFRelease(ev)
        return True
    except Exception as exc:  # noqa: BLE001
        log.debug("CGEvent type failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# X11 – XTEST (python-xlib) or xdotool
# ---------------------------------------------------------------------------
def _x11_paste(ctrl_shift: bool = False, key: str = "v") -> bool:
    try:
        from Xlib import X, XK, display  # type: ignore
        from Xlib.ext import xtest  # type: ignore
    except Exception:
        return _run(["xdotool", "key", ("ctrl+shift+" if ctrl_shift else "ctrl+") + key])

    try:
        d = display.Display()
        try:
            ctrl = d.keysym_to_keycode(XK.string_to_keysym("Control_L"))
            shift = d.keysym_to_keycode(XK.string_to_keysym("Shift_L"))
            v = d.keysym_to_keycode(XK.string_to_keysym(key))
            xtest.fake_input(d, X.KeyPress, ctrl)
            if ctrl_shift:
                xtest.fake_input(d, X.KeyPress, shift)
            xtest.fake_input(d, X.KeyPress, v)
            xtest.fake_input(d, X.KeyRelease, v)
            if ctrl_shift:
                xtest.fake_input(d, X.KeyRelease, shift)
            xtest.fake_input(d, X.KeyRelease, ctrl)
            d.sync()
            return True
        finally:
            d.close()
    except Exception as exc:  # noqa: BLE001
        log.debug("XTEST paste failed (%s); trying xdotool", exc)
        return _run(["xdotool", "key", ("ctrl+shift+" if ctrl_shift else "ctrl+") + key])


def _x11_type(text: str) -> bool:
    if shutil.which("xdotool"):
        return _run(["xdotool", "type", "--clearmodifiers", "--", text])
    try:
        from Xlib import X, XK, display  # type: ignore
        from Xlib.ext import xtest  # type: ignore
    except Exception:
        return False
    try:
        d = display.Display()
        try:
            shift = d.keysym_to_keycode(XK.string_to_keysym("Shift_L"))
            for ch in text:
                if ch == "\n":
                    code = d.keysym_to_keycode(XK.string_to_keysym("Return"))
                    shift_needed = False
                elif ch == "\t":
                    code = d.keysym_to_keycode(XK.string_to_keysym("Tab"))
                    shift_needed = False
                else:
                    sym = XK.string_to_keysym(_x11_keysym_name(ch))
                    code = d.keysym_to_keycode(sym) if sym else 0
                    shift_needed = ch.isupper()
                if not code:
                    continue
                if shift_needed:
                    xtest.fake_input(d, X.KeyPress, shift)
                xtest.fake_input(d, X.KeyPress, code)
                xtest.fake_input(d, X.KeyRelease, code)
                if shift_needed:
                    xtest.fake_input(d, X.KeyRelease, shift)
            d.sync()
            return True
        finally:
            d.close()
    except Exception as exc:  # noqa: BLE001
        log.debug("XTEST type failed: %s", exc)
        return False


def _x11_keysym_name(ch: str) -> str:
    """Best-effort keysym name for common characters."""
    special = {
        " ": "space", ".": "period", ",": "comma", ";": "semicolon", ":": "colon",
        "!": "exclam", "?": "question", "-": "minus", "_": "underscore", "'": "apostrophe",
        '"': "quotedbl", "/": "slash", "\\": "backslash", "(": "parenleft",
        ")": "parenright", "[": "bracketleft", "]": "bracketright", "{": "braceleft",
        "}": "braceright", "@": "at", "#": "numbersign", "$": "dollar", "%": "percent",
        "&": "ampersand", "*": "asterisk", "+": "plus", "=": "equal", "<": "less",
        ">": "greater", "|": "bar", "~": "asciitilde", "^": "asciicircum", "`": "grave",
        "ä": "adiaeresis", "ö": "odiaeresis", "ü": "udiaeresis", "ß": "ssharp",
        "Ä": "Adiaeresis", "Ö": "Odiaeresis", "Ü": "Udiaeresis",
    }
    if ch in special:
        return special[ch]
    if ch.isalnum():
        return ch
    return ""


# ---------------------------------------------------------------------------
# Wayland helpers
# ---------------------------------------------------------------------------
def wayland_tool(name: str) -> bool:
    return shutil.which(name) is not None


def _wtype_paste(ctrl_shift: bool = False, key: str = "v") -> bool:
    if ctrl_shift:
        return _run(["wtype", "-M", "ctrl", "-M", "shift", "-k", key, "-m", "shift", "-m", "ctrl"])
    return _run(["wtype", "-M", "ctrl", "-k", key, "-m", "ctrl"])


def _wtype_type(text: str) -> bool:
    return _run(["wtype", "-"], text=text, timeout=20)


_EVDEV = {"v": 47, "c": 46, "x": 45, "a": 30}


def _ydotool_paste(ctrl_shift: bool = False, key: str = "v") -> bool:
    # 29 = KEY_LEFTCTRL, 42 = KEY_LEFTSHIFT
    code = _EVDEV.get(key.lower(), 47)
    if ctrl_shift:
        keys = f"29:1 42:1 {code}:1 {code}:0 42:0 29:0"
    else:
        keys = f"29:1 {code}:1 {code}:0 29:0"
    return _run(["ydotool", "key", *keys.split()])


def _ydotool_type(text: str) -> bool:
    return _run(["ydotool", "type", "--", text], timeout=20)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def paste(ctrl_shift: bool = False, wayland: str = "auto", ydotool: bool = False,
          portal_paste=None, key: str = "v") -> Optional[str]:
    """Send the paste shortcut. Returns the method that worked, else None.

    ``portal_paste`` is an optional callable provided by the Wayland portal
    backend; it receives ``ctrl_shift`` and returns bool.
    """
    if IS_WINDOWS:
        return "sendinput" if _windows_paste(ctrl_shift, key) else None
    if IS_MACOS:
        return "cgevent" if _macos_paste(ctrl_shift, key) else None
    if not IS_LINUX:
        return None

    if session_type() == "wayland":
        order = [wayland] if wayland != "auto" else ["portal", "wtype", "ydotool"]
        for method in order:
            if method == "portal" and portal_paste is not None:
                try:
                    if portal_paste(ctrl_shift, key):
                        return "portal"
                except Exception as exc:  # noqa: BLE001
                    log.debug("Portal paste failed: %s", exc)
            elif method == "wtype" and _wtype_paste(ctrl_shift, key):
                return "wtype"
            elif method == "ydotool" and ydotool and _ydotool_paste(ctrl_shift, key):
                return "ydotool"
        # XWayland still exposes XTEST for X11 clients.
        if _x11_paste(ctrl_shift, key):
            return "xtest"
        return None

    return "xtest" if _x11_paste(ctrl_shift, key) else None


def copy_selection(wayland: str = "auto", ydotool: bool = False,
                   portal_paste=None) -> Optional[str]:
    """Send the copy shortcut so the current selection lands in the clipboard."""
    if IS_MACOS:
        return paste(wayland=wayland, ydotool=ydotool, portal_paste=portal_paste, key="c")
    return paste(wayland=wayland, ydotool=ydotool, portal_paste=portal_paste, key="c")


def type_text(text: str, wayland: str = "auto", ydotool: bool = False) -> Optional[str]:
    """Type text directly, without touching the clipboard."""
    if IS_WINDOWS:
        return "sendinput" if _windows_type(text) else None
    if IS_MACOS:
        return "cgevent" if _macos_type(text) else None
    if not IS_LINUX:
        return None

    if session_type() == "wayland":
        order = [wayland] if wayland != "auto" else ["wtype", "ydotool"]
        for method in order:
            if method == "wtype" and _wtype_type(text):
                return "wtype"
            if method == "ydotool" and ydotool and _ydotool_type(text):
                return "ydotool"
        if _x11_type(text):
            return "xtest"
        return None

    return "xtest" if _x11_type(text) else None


def available_methods(wayland: str = "auto", ydotool: bool = False) -> list[Method]:
    """Describe the insertion chain for the settings UI."""
    if IS_WINDOWS:
        return [Method("sendinput", "Windows SendInput"), Method("clipboard", "Clipboard only")]
    if IS_MACOS:
        return [Method("cgevent", "macOS CGEvent (Accessibility)"),
                Method("clipboard", "Clipboard only")]
    if not IS_LINUX:
        return [Method("clipboard", "Clipboard only")]
    if session_type() == "wayland":
        out = [Method("portal", "Desktop portal (recommended)")]
        if wayland_tool("wtype"):
            out.append(Method("wtype", "wtype (wlroots compositors)"))
        if ydotool and wayland_tool("ydotool"):
            out.append(Method("ydotool", "ydotool (needs /dev/uinput)"))
        out.append(Method("clipboard", "Clipboard only"))
        return out
    out = [Method("xtest", "X11 XTEST")]
    if shutil.which("xdotool"):
        out.append(Method("xdotool", "xdotool"))
    out.append(Method("clipboard", "Clipboard only"))
    return out


def accessibility_hint() -> str:
    """Explain the permission a platform needs, or return an empty string."""
    if IS_MACOS:
        return ("System Settings → Privacy & Security → Accessibility: allow Voicewright, "
                "otherwise macOS silently drops simulated keystrokes.")
    return ""
