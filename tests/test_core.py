"""Tests for the GUI-independent core (run: python -m pytest tests)."""
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
_tmp = tempfile.mkdtemp()
os.environ["VOICEWRIGHT_CONFIG_DIR"] = _tmp
os.environ["VOICEWRIGHT_DATA_DIR"] = _tmp

import numpy as np  # noqa: E402

from voicewright import cleanup  # noqa: E402
from voicewright.audio import SAMPLE_RATE, _resample, trim_silence  # noqa: E402
from voicewright.config import Config  # noqa: E402
from voicewright.hotkey import ComboDetector, parse_hotkey, serialize_hotkey, validate_hotkey  # noqa: E402


def test_parse_and_serialize():
    keys = parse_hotkey("Ctrl+Shift+Space")
    assert keys == frozenset({"ctrl", "shift", "space"})
    assert serialize_hotkey(keys) == "ctrl+shift+space"
    assert parse_hotkey("super+alt+d") == frozenset({"cmd", "alt", "d"})
    assert validate_hotkey(frozenset({"a"})) is not None
    assert validate_hotkey(frozenset({"f9"})) is None
    assert validate_hotkey(frozenset({"ctrl"})) is not None
    assert validate_hotkey(frozenset({"ctrl", "alt"})) is None


def test_combo_detector_hold_and_toggle():
    d = ComboDetector()
    d.set_combo(parse_hotkey("ctrl+shift+space"))
    events = []
    d.on_activate = lambda: events.append("down")
    d.on_deactivate = lambda: events.append("up")
    d.on_escape = lambda: events.append("esc")
    d.press("ctrl"); d.press("shift"); d.press("space")
    d.press("space")  # key repeat must not re-fire
    assert events == ["down"]
    d.release("space")
    assert events == ["down", "up"]
    d.release("shift"); d.release("ctrl")
    # extra modifier -> different shortcut, must not fire
    d.press("ctrl"); d.press("alt"); d.press("shift"); d.press("space")
    assert events == ["down", "up"]
    for k in ("space", "shift", "alt", "ctrl"):
        d.release(k)
    d.press("esc")
    assert events[-1] == "esc"
    # stuck non-modifier key does not block activation
    d.release("esc")
    d.pressed.add("x")
    d.press("ctrl"); d.press("shift"); d.press("space")
    assert events[-1] == "down"


def test_rules_cleanup():
    out = cleanup.rules_cleanup("ähm also das ist ist äh ein test , oder")
    assert "ähm" not in out and "äh " not in out
    assert "ist ist" not in out
    assert out[0].isupper()
    assert " ," not in out


def test_config_roundtrip():
    c = Config(Path(_tmp) / "cfg.json")
    c.set("hotkey", "ctrl+alt+d")
    c.set_cleanup_model("gemini", "gemini-x")
    c2 = Config(Path(_tmp) / "cfg.json")
    assert c2.get("hotkey") == "ctrl+alt+d"
    assert c2.cleanup_model("gemini") == "gemini-x"
    assert c2.cleanup_model("openai")  # defaults merged


def test_system_prompt_translation():
    c = Config(Path(_tmp) / "cfg2.json")
    c.set("output_language", "en")
    c.set("custom_dictionary", ["Voicewright"])
    p = cleanup.build_system_prompt(c)
    assert "Translate" in p and "English" in p and "Voicewright" in p


def test_audio_helpers():
    sig = np.concatenate([np.zeros(SAMPLE_RATE), 0.3 * np.ones(SAMPLE_RATE), np.zeros(SAMPLE_RATE)]).astype(np.float32)
    t = trim_silence(sig)
    assert SAMPLE_RATE <= t.size < 2 * SAMPLE_RATE
    r = _resample(np.ones(48000, dtype=np.float32), 48000)
    assert r.size == SAMPLE_RATE


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"data": [{"id": "model-a"}, {"id": "model-b"}]}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert req["messages"][0]["role"] == "system"
        txt = "<think>hmm</think>\"Hallo Welt.\""
        body = json.dumps({"choices": [{"message": {"content": txt}}]}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)


def test_openai_compatible_roundtrip():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    c = Config(Path(_tmp) / "cfg3.json")
    c.set("cleanup_provider", "custom")
    c.set("custom_base_url", f"http://127.0.0.1:{srv.server_port}/v1")
    c.set_cleanup_model("custom", "model-a")
    cl = cleanup.Cleaner(c)
    assert cl.list_models("custom") == ["model-a", "model-b"]
    assert cl.clean("hallo welt") == "Hallo Welt."
    srv.shutdown()


def test_missing_keyring_never_creates_a_plaintext_key(monkeypatch, tmp_path):
    from voicewright import keystore

    monkeypatch.setattr(keystore, "_keyring_usable", lambda: False)
    fallback = tmp_path / "keys.json"
    monkeypatch.delenv("VOICEWRIGHT_GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(keystore, "_FALLBACK", fallback, raising=False)
    assert keystore.set_api_key("gemini", "synthetic-test-key") == "unavailable"
    assert not fallback.exists()
    assert keystore.get_api_key("gemini") == ""


def test_wayland_uses_desktop_shortcut_without_raw_input(monkeypatch):
    from voicewright import hotkey

    def unexpected_backend(_):
        raise AssertionError("A Wayland session must use the desktop shortcut")

    monkeypatch.setattr(hotkey, "IS_LINUX", True)
    monkeypatch.setattr(hotkey, "session_type", lambda: "wayland")
    monkeypatch.setattr(hotkey, "PynputBackend", unexpected_backend)
    monkeypatch.setattr(hotkey, "EvdevBackend", unexpected_backend, raising=False)
    manager = hotkey.HotkeyManager()
    assert manager.start("ctrl+shift+space", "evdev") == "none"
    assert manager.error == "WAYLAND_DESKTOP_SHORTCUT"
