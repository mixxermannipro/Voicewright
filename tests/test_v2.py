"""Tests for Voicewright 2.0 features, migration, safety guards and UI."""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
_tmp = tempfile.mkdtemp()
os.environ.setdefault("VOICEWRIGHT_CONFIG_DIR", _tmp)
os.environ.setdefault("VOICEWRIGHT_DATA_DIR", _tmp)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from voicewright import guard, inject, models, portals, smart  # noqa: E402
from voicewright.config import DEFAULT_CONFIG, V1_KEYS, Config, migrate  # noqa: E402
from voicewright.dictation import CANCEL, NONE, START, STOP, DictationMachine  # noqa: E402
from voicewright.history import History  # noqa: E402
from voicewright.stats import Stats  # noqa: E402


class _FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# ---------------------------------------------------------------------------
# Hybrid dictation state machine
# ---------------------------------------------------------------------------
def test_dictation_hybrid_tap_and_hold():
    clk = _FakeClock()
    events: list[str] = []
    m = DictationMachine(mode="hybrid", tap_threshold_ms=350, min_hold_ms=250, clock=clk)
    m.on_start = lambda: events.append("start")
    m.on_stop = lambda: events.append("stop")
    m.on_cancel = lambda: events.append("cancel")

    # Tap (< 350 ms) keeps recording until next press
    assert m.key_down() == START
    assert m.recording
    clk.advance(0.12)
    assert m.key_up() == NONE
    assert m.recording and m.tapped
    clk.advance(0.50)
    assert m.key_down() == STOP
    assert not m.recording

    # Hold (>= 350 ms) stops on release
    assert m.key_down() == START
    assert m.key_down() == NONE  # key repeat ignored
    clk.advance(0.50)
    assert m.key_up() == STOP
    assert not m.recording

    # Escape cancels active recording
    assert m.key_down() == START
    assert m.escape() == CANCEL
    assert not m.recording
    assert m.escape() == NONE
    assert events == ["start", "stop", "start", "stop", "start", "cancel"]


def test_dictation_toggle_and_hold_modes():
    clk = _FakeClock()
    m = DictationMachine(mode="toggle", clock=clk)
    assert m.key_down() == START
    clk.advance(0.8)
    assert m.key_up() == NONE
    assert m.recording
    assert m.key_down() == STOP

    m.configure(mode="hold", min_hold_ms=250)
    assert m.key_down() == START
    clk.advance(0.10)  # accidental brush < min_hold_ms
    assert m.key_up() == CANCEL
    assert not m.recording

    assert m.key_down() == START
    clk.advance(0.40)
    assert m.key_up() == STOP


# ---------------------------------------------------------------------------
# Guard validation
# ---------------------------------------------------------------------------
def test_guard_strict_and_transform_modes():
    assert not guard.validate("hello", "").ok
    assert guard.validate("Hallo Welt.", "Hallo Welt.").ok

    # Protocol leakage & assistant preambles
    assert not guard.validate("hallo", "<|im_start|>Hallo").ok
    assert not guard.validate("hallo", "Hier ist der korrigierte Text: Hallo").ok
    assert not guard.validate("hallo", "Sure, here is the text: Hallo").ok

    # Growth / shrinkage limits
    assert not guard.validate("kurz", "x" * 50).ok
    assert not guard.validate("das ist ein sehr langer diktierter satz", "ok", mode="strict").ok

    # Protected facts: numbers, URLs, e-mail, code, dictionary
    assert not guard.validate("Treffen um 14:30 Uhr", "Treffen um 15:30 Uhr").ok
    assert guard.validate("3,5 Prozent", "3.5 Prozent").ok
    assert not guard.validate("Siehe https://example.org/docs", "Siehe example").ok
    assert not guard.validate("Mail an foo@bar.de", "Mail an foo").ok
    assert not guard.validate("Nutze `run_task()` hier", "Nutze hier").ok
    assert not guard.validate("Voicewright rockt", "voice rockt", dictionary=("Voicewright",)).ok

    # Negation guard in strict vs transform mode
    assert not guard.validate("Ich komme nicht mit.", "Ich komme mit.", language="de", mode="strict").ok
    assert guard.validate(
        "Wir treffen uns am 12. Mai.",
        "Termin: 12. Mai.",
        language="de",
        mode="transform",
    ).ok

    cleaned = guard.clean_protocol("```text\n<think>ok</think>Assistant: Hallo Welt.\n```")
    assert cleaned == "Hallo Welt."


# ---------------------------------------------------------------------------
# Smart formatting, commands, snippets, replacements
# ---------------------------------------------------------------------------
def test_smart_features():
    spoken = smart.apply_spoken_punctuation(
        "hallo komma wie geht es dir fragezeichen literalmodus an komma literalmodus aus punkt"
    )
    assert smart.tidy_punctuation(spoken) == "hallo, wie geht es dir? komma."

    mode, rest = smart.detect_structure("Milch, Brot, und Butter als stichpunkte")
    assert mode == "list"
    assert smart.apply_structure(rest, mode) == "- Milch\n- Brot\n- Butter"

    mode_e, rest_e = smart.detect_structure("als e-mail Wir sehen uns morgen.")
    assert mode_e == "email"
    assert "Hallo," in smart.apply_structure(rest_e, mode_e)

    mode_n, rest_n = smart.detect_structure("Projektplan. Budget prüfen. Team fragen. als notizen")
    assert mode_n == "notes"
    assert "- Budget prüfen" in smart.apply_structure(rest_n, mode_n)

    cmd = smart.detect_command("Das ist ein sehr langer Text. mach das kürzer")
    assert cmd.kind == "shorter"
    assert cmd.rest == "Das ist ein sehr langer Text"

    cmd_tr = smart.detect_command("Guten Tag übersetze auf Englisch")
    assert cmd_tr.kind == "translate"
    assert cmd_tr.argument == "en"
    assert cmd_tr.rest == "Guten Tag"

    expanded = smart.expand_snippets(
        "Bitte senden mit Textbaustein Signatur",
        [{"name": "Signatur", "text": "Viele Grüße, Max"}],
    )
    assert expanded == "Bitte senden mit Viele Grüße, Max"

    replaced = smart.apply_replacements("Wir nutzen voice right heute", {"voice right": "Voicewright"})
    assert replaced == "Wir nutzen Voicewright heute"


# ---------------------------------------------------------------------------
# Config v1 -> v2 migration & resilience
# ---------------------------------------------------------------------------
def test_config_v1_migration_and_corruption(tmp_path):
    cfg_file = tmp_path / "v1_config.json"
    cfg_file.write_text(
        json.dumps({"whisper_model": "tiny", "hotkey_mode": "toggle", "custom_extra": 42}),
        encoding="utf-8",
    )
    cfg = Config(cfg_file)
    assert cfg.get("version") == 2
    assert cfg.get("speech_model") == "whisper-tiny"
    assert cfg.get("whisper_model") == "whisper-tiny"
    assert cfg.get("hotkey_mode") == "toggle"
    assert cfg.get("cleanup_enabled") is False
    assert cfg.get("custom_extra") == 42

    cfg.set("whisper_model", "small")
    assert cfg.get("speech_model") == "whisper-small"

    for key in V1_KEYS:
        assert key in DEFAULT_CONFIG

    # Corrupt file is backed up, defaults remain usable
    bad_file = tmp_path / "broken.json"
    bad_file.write_text("{not valid json", encoding="utf-8")
    cfg_bad = Config(bad_file)
    assert cfg_bad.get("version") == 2
    assert bad_file.with_suffix(".broken.json").exists()

    rep = migrate({"version": 1, "tap_threshold_ms": 99999, "snippets": "bad", "replacements": []})
    assert rep["tap_threshold_ms"] == 900
    assert rep["snippets"] == []
    assert rep["replacements"] == {}


# ---------------------------------------------------------------------------
# Model catalog integrity
# ---------------------------------------------------------------------------
def test_model_catalog_hashes_and_ids():
    all_m = models.ALL_MODELS
    ids = [m.id for m in all_m]
    assert len(ids) == len(set(ids))
    for m in all_m:
        assert m.files
        for f in m.files:
            assert f.size > 0
            assert len(f.sha256) == 64
            int(f.sha256, 16)
    assert models.recommended_model(cuda=False, sherpa=True) == "parakeet-v3"
    assert models.recommended_model(cuda=True, sherpa=False) == "whisper-large-v3-turbo"
    assert models.recommended_model(cuda=False, sherpa=False) == "whisper-small"


# ---------------------------------------------------------------------------
# Platform injection order & Wayland portals
# ---------------------------------------------------------------------------
def test_inject_platform_order(monkeypatch):
    monkeypatch.setattr(inject, "IS_WINDOWS", False)
    monkeypatch.setattr(inject, "IS_MACOS", False)
    monkeypatch.setattr(inject, "IS_LINUX", True)
    monkeypatch.setattr(inject, "session_type", lambda: "wayland")
    monkeypatch.setattr(inject, "_wtype_paste", lambda *a: False)
    monkeypatch.setattr(inject, "_ydotool_paste", lambda *a: True)
    monkeypatch.setattr(inject, "_x11_paste", lambda *a: False)

    # ydotool disabled -> must NOT be used
    assert inject.paste(wayland="auto", ydotool=False, portal_paste=lambda *a: False) is None
    # ydotool enabled -> used when portal & wtype fail
    assert inject.paste(wayland="auto", ydotool=True, portal_paste=lambda *a: False) == "ydotool"
    # portal wins first
    assert inject.paste(wayland="auto", ydotool=True, portal_paste=lambda *a: True) == "portal"

    # Windows and macOS paths
    monkeypatch.setattr(inject, "IS_WINDOWS", True)
    monkeypatch.setattr(inject, "_windows_paste", lambda *a: True)
    assert inject.paste() == "sendinput"

    monkeypatch.setattr(inject, "IS_WINDOWS", False)
    monkeypatch.setattr(inject, "IS_MACOS", True)
    monkeypatch.setattr(inject, "_macos_paste", lambda *a: True)
    assert inject.paste() == "cgevent"


def test_portals_helpers():
    assert (
        portals.predict_request_path(":1.42", "tok_1")
        == "/org/freedesktop/portal/desktop/request/1_42/tok_1"
    )
    assert portals._unwrap(("s", "hello")) == "hello"
    assert portals._unwrap({"a": ("u", 7), "b": [("s", "x")]}) == {"a": 7, "b": ["x"]}

    class _Msg:
        body = (0, {"session_handle": ("o", "/org/freedesktop/portal/session/1")})

    assert portals._results(_Msg()) == {"session_handle": "/org/freedesktop/portal/session/1"}


# ---------------------------------------------------------------------------
# Local statistics (no dictated text stored)
# ---------------------------------------------------------------------------
def test_stats_no_text_stored(tmp_path):
    sp = tmp_path / "stats.json"
    st = Stats(sp)
    st.record("Geheimer Diktattext mit vier Wörtern", audio_seconds=2.5)
    assert st.sessions == 1
    assert st.words == 5
    assert st.seconds_saved() >= 0.0
    assert len(st.last_days(7)) == 7
    assert "1 dictations" in st.summary()
    raw_disk = sp.read_text(encoding="utf-8")
    assert "Geheimer" not in raw_disk
    st.reset()
    assert st.sessions == 0


# ---------------------------------------------------------------------------
# Headless Qt UI smoke test
# ---------------------------------------------------------------------------
def test_ui_windows_headless(tmp_path):
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from voicewright.ui import theme, widgets
    from voicewright.ui.overlay import Overlay
    from voicewright.ui.settings_window import SettingsWindow

    app = QApplication.instance() or QApplication([])
    pal = theme.resolve("dark")
    theme.set_active(pal)
    app.setStyleSheet(theme.qss(pal))
    widgets.set_motion(False)

    cfg = Config(tmp_path / "ui_cfg.json")
    hist = History(path=tmp_path / "hist.json")
    hist.add("raw", "clean", "de", 1.2, "rules")
    st = Stats(tmp_path / "ui_stats.json")
    st.record("Hallo Welt", 1.0)

    win = SettingsWindow(cfg, hist, st, QIcon())
    assert win.stack.count() == 7
    for idx in range(7):
        win.select_page(idx)
        assert win.stack.currentIndex() == idx
    win.sync_mode("hold")
    assert win.mode_seg.value() == "hold"
    win.refresh_history()
    assert win.history_list.count() == 1
    win.refresh_stats()
    win.refresh_output("Wayland portal")
    win.set_status("Ready")
    win.set_status("Error", error=True)
    win.close()

    ov = Overlay()
    for state in ("recording", "processing", "done", "error"):
        ov.show_state(state, state)
        ov.set_level(0.5)
        ov.repaint()
    ov.hide()
