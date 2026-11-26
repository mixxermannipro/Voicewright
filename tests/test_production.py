"""Regression tests for the 2.0 production hardening.

They cover the parts that are easy to break and hard to see by clicking:
runnable model defaults, XDG shortcut names, the shared multi-shortcut
listener, Wayland token persistence, the Windows SendInput layout and the
setup assistant including its live level meter.
"""
import ctypes
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
_tmp = tempfile.mkdtemp()
os.environ.setdefault("VOICEWRIGHT_CONFIG_DIR", _tmp)
os.environ.setdefault("VOICEWRIGHT_DATA_DIR", _tmp)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from voicewright import hotkey, inject, models, portals, runtime  # noqa: E402
from voicewright.config import Config, migrate  # noqa: E402


# ---------------------------------------------------------------------------
# Runnable model default
# ---------------------------------------------------------------------------
def test_ensure_runnable_default_falls_back_without_sherpa(tmp_path, monkeypatch):
    cfg = Config(tmp_path / "cfg.json")

    # Fresh install, no model downloaded, no sherpa wheel -> Whisper Small can
    # run and is offered by the setup assistant.
    monkeypatch.setattr(models, "is_downloaded", lambda _mid: False)
    cfg.set("speech_model", "parakeet-v3")
    assert models.ensure_runnable_default(cfg, sherpa=False) == "whisper-small"
    assert cfg.get("speech_model") == "whisper-small"

    # An already downloaded, runnable Whisper model wins over a fresh download.
    monkeypatch.setattr(models, "is_downloaded", lambda mid: mid == "whisper-tiny")
    assert models.ensure_runnable_default(cfg, sherpa=False) == "whisper-tiny"

    # With sherpa installed the Parakeet default is kept when it is downloaded.
    monkeypatch.setattr(models, "is_downloaded", lambda mid: mid == "parakeet-v3")
    cfg.set("speech_model", "parakeet-v3")
    assert models.ensure_runnable_default(cfg, sherpa=True) == "parakeet-v3"

    assert models.is_runnable("parakeet-v3", sherpa=False) is False
    assert models.is_runnable("whisper-tiny", sherpa=False) is True


# ---------------------------------------------------------------------------
# Config migration and Wayland token
# ---------------------------------------------------------------------------
def test_config_onboarding_and_restore_token():
    fresh = migrate({})
    assert fresh["onboarding_done"] is False
    assert fresh["wayland_restore_token"] == ""

    old = migrate({"version": 1, "first_run_done": True, "wayland_restore_token": 42})
    assert old["onboarding_done"] is True
    assert old["wayland_restore_token"] == ""

    # A config from an early 2.0 build without the new key but with the old
    # first-run flag must not show the assistant again.
    early = migrate({"version": 2, "first_run_done": True})
    assert early["onboarding_done"] is True


# ---------------------------------------------------------------------------
# Global shortcuts
# ---------------------------------------------------------------------------
def test_portal_trigger_uses_xdg_names():
    assert hotkey.portal_trigger("ctrl+shift+space") == "CTRL+SHIFT+space"
    assert hotkey.portal_trigger("ctrl+alt+f5") == "CTRL+ALT+F5"
    assert hotkey.portal_trigger("cmd+enter") == "LOGO+Return"
    assert hotkey.portal_trigger("ctrl+shift+page_up") == "CTRL+SHIFT+Page_Up"


def test_hotkey_manager_binds_dictation_and_transform(monkeypatch):
    events = []
    monkeypatch.setattr(hotkey, "IS_LINUX", True)
    monkeypatch.setattr(hotkey, "session_type", lambda: "wayland")

    class FakePortal:
        name = "portal"
        error = ""

        def __init__(self, detectors):
            self.detectors = detectors
            self.shortcuts = None
            self.stopped = False

        def start(self, shortcuts):
            self.shortcuts = shortcuts
            return True

        def stop(self):
            self.stopped = True

    monkeypatch.setattr(hotkey, "PortalBackend", FakePortal)
    manager = hotkey.HotkeyManager()
    manager.detector.on_activate = lambda: events.append("dictate")
    manager.transform_detector.on_activate = lambda: events.append("transform")

    assert manager.start(
        "ctrl+shift+space", wayland="portal", transform_hotkey="ctrl+alt+space"
    ) == "portal"
    assert [s[0] for s in manager.backend.shortcuts] == ["dictate", "transform"]
    assert [s[2] for s in manager.backend.shortcuts] == [
        "CTRL+SHIFT+space", "CTRL+ALT+space"
    ]

    # Only the matching shortcut id fires its detector.
    manager.backend.detectors["transform"].press_portal()
    manager.backend.detectors["transform"].release_portal()
    assert events == ["transform"]

    # A duplicate combination is ignored instead of firing both actions.
    assert manager.start(
        "ctrl+shift+space", wayland="portal", transform_hotkey="ctrl+shift+space"
    ) == "portal"
    assert [s[0] for s in manager.backend.shortcuts] == ["dictate"]
    manager.stop()


def test_invalid_transform_shortcut_keeps_dictation(monkeypatch):
    monkeypatch.setattr(hotkey, "IS_LINUX", False)
    manager = hotkey.HotkeyManager()
    assert manager.start(
        "ctrl+shift+space", backend="none", transform_hotkey="+"
    ) == "none"
    assert manager.detector.combo == hotkey.parse_hotkey("ctrl+shift+space")
    assert manager.transform_detector.combo == frozenset()


def test_remote_desktop_persists_and_updates_token(monkeypatch):
    calls = []
    stored = []

    class FakeConn:
        unique_name = ":1.42"

        def close(self):
            pass

    def fake_imports():
        return (
            lambda *a, **k: None,
            lambda *a, **k: None,
            None,
            lambda *a, **k: None,
            lambda **k: FakeConn(),
        )

    def fake_request(conn, interface, method, signature, body, token, timeout=60.0):
        calls.append((method, body))
        if method == "CreateSession":
            return {"session_handle": "/org/freedesktop/portal/desktop/session/1"}
        if method == "Start":
            return {"restore_token": ("s", "fresh-token")}
        return {}

    monkeypatch.setattr(portals, "_imports", fake_imports)
    monkeypatch.setattr(portals, "_request", fake_request)

    portal = portals.RemoteDesktopPortal(on_restore_token=stored.append)
    assert portal.connect(restore_token="old-token")
    assert portal.connected
    assert stored == ["fresh-token"]
    assert portal.restore_token == "fresh-token"

    select = [body for method, body in calls if method == "SelectDevices"][0]
    options = select[1]
    assert options["types"] == ("u", 1)
    assert options["persist_mode"] == ("u", 2)
    assert options["restore_token"] == ("s", "old-token")
    portal.disconnect()
    assert not portal.connected


def test_remote_desktop_is_not_connected_during_permission_dialog(monkeypatch):
    seen = []
    holder = {}

    class FakeConn:
        unique_name = ":1.43"

        def close(self):
            pass

    def fake_imports():
        return (
            lambda *a, **k: None,
            lambda *a, **k: None,
            None,
            lambda *a, **k: None,
            lambda **k: FakeConn(),
        )

    def fake_request(conn, interface, method, signature, body, token, timeout=60.0):
        if method in ("SelectDevices", "Start"):
            seen.append(holder["portal"].connected)
        if method == "CreateSession":
            return {"session_handle": "/org/freedesktop/portal/desktop/session/1"}
        return {}

    monkeypatch.setattr(portals, "_imports", fake_imports)
    monkeypatch.setattr(portals, "_request", fake_request)

    portal = portals.RemoteDesktopPortal()
    holder["portal"] = portal
    assert portal.connect()
    # While the compositor shows its dialog the keyboard must not look usable;
    # otherwise the UI would block behind the permission prompt.
    assert seen == [False, False]
    assert portal.connected


def test_request_reports_dbus_error_instead_of_waiting(monkeypatch):
    jeepney = pytest.importorskip("jeepney")

    class Header:
        message_type = jeepney.MessageType.error

    class Reply:
        header = Header()
        body = ("org.freedesktop.portal.Error.InvalidArgument", "stale token")

    class Filter:
        def __enter__(self):
            return []

        def __exit__(self, *exc):
            return False

    class FakeConn:
        unique_name = ":1.77"

        def filter(self, rule):
            return Filter()

        def send_and_get_reply(self, msg, timeout=None):
            return Reply()

        def recv_until_filtered(self, queue, timeout=None):
            raise AssertionError("must not wait for a Response signal")

    with pytest.raises(portals.PortalError) as exc:
        portals._request(FakeConn(), portals.IFACE_REMOTE, "SelectDevices",
                         "oa{sv}", (), "tok", timeout=1.0)
    assert "InvalidArgument" in str(exc.value)


def test_request_reads_response_after_method_reply():
    jeepney = pytest.importorskip("jeepney")

    class Header:
        def __init__(self, kind):
            self.message_type = kind

    class Message:
        def __init__(self, kind, body):
            self.header = Header(kind)
            self.body = body

    class Filter:
        def __enter__(self):
            return []

        def __exit__(self, *exc):
            return False

    class FakeConn:
        unique_name = ":1.78"

        def filter(self, rule):
            return Filter()

        def send_and_get_reply(self, msg, timeout=None):
            return Message(jeepney.MessageType.method_return, ("/request/1",))

        def recv_until_filtered(self, queue, timeout=None):
            return Message(jeepney.MessageType.signal,
                           (0, {"session_handle": ("s", "/session/1")}))

    result = portals._request(FakeConn(), portals.IFACE_SHORTCUTS, "CreateSession",
                              "a{sv}", (), "tok", timeout=1.0)
    assert result == {"session_handle": "/session/1"}


def test_global_shortcut_dispatch_uses_member_field():
    jeepney = pytest.importorskip("jeepney")
    events = []

    class Header:
        fields = {jeepney.HeaderFields.member: "Activated"}

    class Message:
        header = Header()
        body = ("/session/1", "transform", 0, {})

    portal = portals.GlobalShortcutsPortal(
        on_press=lambda sid: events.append(("press", sid)),
        on_release=lambda sid: events.append(("release", sid)),
    )
    portal._dispatch(Message(), "/session/1", {"dictate", "transform"})
    assert events == [("press", "transform")]

    Header.fields = {jeepney.HeaderFields.member: "Deactivated"}
    portal._dispatch(Message(), "/session/1", {"dictate", "transform"})
    assert events[-1] == ("release", "transform")


def test_portal_key_reports_revoked_permission():
    jeepney = pytest.importorskip("jeepney")

    class Header:
        message_type = jeepney.MessageType.error

    class Reply:
        header = Header()
        body = ("org.freedesktop.portal.Error.NotAllowed", "revoked")

    class FakeConn:
        def send_and_get_reply(self, msg, timeout=None):
            return Reply()

    portal = portals.RemoteDesktopPortal()
    portal._conn = FakeConn()
    portal._session = "/session/1"
    assert portal.key(portals.KEY_LEFTCTRL, True) is False


def test_revoked_restore_token_does_not_open_a_new_dialog(monkeypatch):
    calls = []

    class FakeConn:
        unique_name = ":1.42"

        def close(self):
            pass

    def fake_imports():
        return (
            lambda *a, **k: None,
            lambda *a, **k: None,
            None,
            lambda *a, **k: None,
            lambda **k: FakeConn(),
        )

    def fake_request(conn, interface, method, signature, body, token, timeout=60.0):
        calls.append(method)
        if method == "CreateSession":
            return {"session_handle": "/org/freedesktop/portal/desktop/session/1"}
        if method == "SelectDevices":
            raise portals.PortalError("org.freedesktop.portal.Error.InvalidArgument")
        return {}

    monkeypatch.setattr(portals, "_imports", fake_imports)
    monkeypatch.setattr(portals, "_request", fake_request)

    portal = portals.RemoteDesktopPortal()
    assert not portal.connect(restore_token="stale")
    # Only the first SelectDevices call happened: no retry that would show a
    # fresh permission dialog at startup.
    assert calls == ["CreateSession", "SelectDevices"]
    assert portal.error
    assert not portal.connected


# ---------------------------------------------------------------------------
# Windows input and process spawning
# ---------------------------------------------------------------------------
def test_helper_command_failure_is_not_reported_as_success(monkeypatch):
    class Result:
        returncode = 1

    monkeypatch.setattr(inject.shutil, "which", lambda _name: "/usr/bin/tool")
    monkeypatch.setattr(inject.subprocess, "run", lambda *a, **k: Result())
    assert inject._run(["tool", "--version"]) is False

    Result.returncode = 0
    assert inject._run(["tool", "--version"]) is True


def test_windows_input_structs_match_win64():
    keybd, item = inject._windows_structs()
    assert ctypes.sizeof(keybd) == 24
    assert ctypes.sizeof(item) == 40
    assert inject._utf16_units("ä😀") == [0x00E4, 0xD83D, 0xDE00]


def test_windows_send_sets_flags_and_unicode(monkeypatch):
    sent = []

    class FakeUser32:
        def SendInput(self, count, pointer, size):
            item = ctypes.cast(pointer, ctypes.POINTER(inject._INPUT)).contents
            sent.append({
                "count": count,
                "size": size,
                "type": item.type,
                "vk": item.union.ki.wVk,
                "scan": item.union.ki.wScan,
                "flags": item.union.ki.dwFlags,
            })
            return count

    monkeypatch.setattr(inject, "_get_user32", lambda: FakeUser32())
    assert inject._windows_send(0x41, True)
    assert inject._windows_send(0x41, False)
    assert inject._windows_send(0, True, unicode_unit=0x00E4)

    assert sent[0]["type"] == inject.INPUT_KEYBOARD
    assert sent[0]["size"] == 40
    assert sent[0]["flags"] == 0
    assert sent[1]["flags"] & inject.KEYEVENTF_KEYUP
    assert sent[2]["vk"] == 0
    assert sent[2]["scan"] == 0x00E4
    assert sent[2]["flags"] & inject.KEYEVENTF_UNICODE


def test_windows_type_uses_utf16_units(monkeypatch):
    calls = []

    def fake_send(vk, down, scan=0, unicode_char=None, unicode_unit=None):
        calls.append((vk, down, scan, unicode_char, unicode_unit))
        return True

    monkeypatch.setattr(inject, "_windows_send", fake_send)
    assert inject._windows_type("ä")
    assert calls[0][4] == 0x00E4
    assert calls[1][1] is False

    # An emoji is a surrogate pair: both halves down, then both up again.
    calls.clear()
    assert inject._windows_type("😀")
    assert [(c[4], c[1]) for c in calls] == [
        (0xD83D, True), (0xDE00, True), (0xDE00, False), (0xD83D, False),
    ]


def test_spawn_options_hide_windows_console():
    win = runtime._spawn_options(windows=True)
    assert win["creationflags"] == 0x08000000
    posix = runtime._spawn_options(windows=False)
    assert posix["start_new_session"] is True
    assert "creationflags" not in posix


# ---------------------------------------------------------------------------
# Setup assistant and microphone test
# ---------------------------------------------------------------------------
def _qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_onboarding_wizard_headless(tmp_path):
    from voicewright.ui.onboarding import OnboardingWizard

    _qapp()
    cfg = Config(tmp_path / "onboarding.json")
    wizard = OnboardingWizard(cfg)
    assert wizard.stack.count() == 4
    assert wizard.current_index == 0
    assert wizard.next_btn.text() == "Next"

    for step in range(4):
        wizard.show_step(step)
        assert wizard.stack.currentIndex() == step
    assert wizard.next_btn.text() == "Finish"

    wizard._finish()
    assert cfg.get("onboarding_done") is True
    assert cfg.get("first_run_done") is True


def test_level_meter_and_microphone_tester():
    from voicewright.ui.onboarding import LevelMeter, MicrophoneTester, level_fraction

    _qapp()
    assert level_fraction(0.0) == 0.0
    assert 0.49 < level_fraction(0.06) < 0.51
    assert level_fraction(1.0) == 1.0
    assert level_fraction("bad") == 0.0

    meter = LevelMeter()
    meter.set_level(0.06)
    assert 0.49 < meter.value < 0.51

    class FakeStream:
        def __init__(self, callback):
            self.callback = callback
            self.started = False

        def start(self):
            self.started = True

        def stop(self):
            pass

        def close(self):
            pass

    stream = None

    def factory(_name, callback):
        nonlocal stream
        stream = FakeStream(callback)
        return stream

    tester = MicrophoneTester(stream_factory=factory)
    levels = []
    tester.level.connect(levels.append)
    assert tester.start()
    assert stream.started
    tester._on_audio(np.array([[0.2]], dtype=np.float32), 1, None, None)
    assert levels and levels[0] > 0.19
    tester.stop()
    assert not tester.running

    def broken(_name, _callback):
        raise RuntimeError("no microphone")

    failed = MicrophoneTester(stream_factory=broken)
    errors = []
    failed.failed.connect(errors.append)
    assert not failed.start()
    assert errors == ["no microphone"]


def test_transform_shortcut_must_not_overlap_dictation(monkeypatch):
    monkeypatch.setattr(hotkey, "IS_LINUX", False)
    manager = hotkey.HotkeyManager()
    manager.start("ctrl+alt+space", backend="none", transform_hotkey="ctrl+alt")
    # Holding the dictation prefix would otherwise fire the rewrite as well.
    assert manager.transform_detector.combo == frozenset()

    manager.start("ctrl+space", backend="none", transform_hotkey="ctrl+alt+space")
    assert manager.transform_detector.combo == frozenset()

    manager.start("ctrl+alt+space", backend="none", transform_hotkey="ctrl+alt+r")
    assert manager.transform_detector.combo == hotkey.parse_hotkey("ctrl+alt+r")

    manager.update_combo("ctrl+shift+space", "ctrl+shift")
    assert manager.transform_detector.combo == frozenset()
    manager.update_combo("ctrl+shift+space", "ctrl+alt+space")
    assert manager.transform_detector.combo == hotkey.parse_hotkey("ctrl+alt+space")


def test_microphone_tester_closes_stream_when_start_fails():
    from voicewright.ui.onboarding import MicrophoneTester

    _qapp()

    class BrokenStream:
        def __init__(self):
            self.closed = False

        def start(self):
            raise RuntimeError("device busy")

        def close(self):
            self.closed = True

    stream = BrokenStream()
    tester = MicrophoneTester(stream_factory=lambda _name, _cb: stream)
    errors = []
    tester.failed.connect(errors.append)
    assert not tester.start()
    assert stream.closed
    assert errors == ["device busy"]
    assert not tester.running


def test_clipboard_restore_keeps_user_content(tmp_path):
    from PySide6.QtGui import QGuiApplication

    from voicewright.injector import Injector

    _qapp()
    cfg = Config(tmp_path / "clip.json")
    injector = Injector(cfg)
    clipboard = QGuiApplication.clipboard()
    clipboard.setText("clipboard-probe")
    if clipboard.text() != "clipboard-probe":
        pytest.skip("This Qt platform plugin has no clipboard")

    clipboard.setText("before")
    injector._saved_clipboard = "before"
    injector._inserted_text = "dictated"
    clipboard.setText("dictated")
    injector._restore_clipboard()
    assert clipboard.text() == "before"

    # The user copied something while dictation was running: never overwrite.
    clipboard.setText("user copy")
    injector._saved_clipboard = "before"
    injector._inserted_text = "dictated"
    injector._restore_clipboard()
    assert clipboard.text() == "user copy"
    injector.deleteLater()


# ---------------------------------------------------------------------------
# Qt platform selection
# ---------------------------------------------------------------------------
def test_qt_platform_selection(monkeypatch):
    from voicewright.main import _qt_platform

    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    if not sys.platform.startswith("linux"):
        assert _qt_platform() == ""
        return

    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("DISPLAY", ":0")
    assert _qt_platform() == "wayland;xcb"

    monkeypatch.delenv("DISPLAY")
    assert _qt_platform() == "wayland"

    monkeypatch.delenv("WAYLAND_DISPLAY")
    monkeypatch.setenv("DISPLAY", ":0")
    assert _qt_platform() == "xcb"

    monkeypatch.delenv("DISPLAY")
    assert _qt_platform() == ""

    # An explicit choice (tests, smoke script, user override) always wins.
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    assert _qt_platform() == ""
