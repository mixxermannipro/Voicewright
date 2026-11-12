"""Application controller: ties hotkeys, recording, transcription, cleanup and insertion together."""
from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from voicewright import APP_NAME
from voicewright.audio import SAMPLE_RATE, AudioError, Recorder, play_sound, trim_silence
from voicewright.cleanup import PROVIDERS_BY_ID, Cleaner, rules_cleanup
from voicewright.config import Config
from voicewright.history import History
from voicewright.hotkey import HotkeyManager, format_hotkey
from voicewright.i18n import tr
from voicewright.injector import Injector
from voicewright.models import downloaded_models, is_downloaded
from voicewright.paths import resource_path
from voicewright.transcriber import Transcriber
from voicewright.ui.overlay import Overlay
from voicewright.ui.settings_window import SettingsWindow
from voicewright.ui.tasks import run_task

log = logging.getLogger(__name__)


class _HotkeyBridge(QObject):
    """Moves callbacks from the listener thread onto the Qt main thread."""
    activated = Signal()
    deactivated = Signal()
    escape = Signal()
    level = Signal(float)


def _make_icon(base: QIcon, dot: QColor | None) -> QIcon:
    pm = base.pixmap(64, 64)
    if pm.isNull():
        pm = QPixmap(64, 64)
        pm.fill(QColor("#5b5bf0"))
    if dot is not None:
        pm = QPixmap(pm)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(dot)
        p.setPen(QColor(255, 255, 255))
        p.drawEllipse(36, 36, 26, 26)
        p.end()
    return QIcon(pm)


class Controller(QObject):
    def __init__(self, app: QApplication, config: Config) -> None:
        super().__init__()
        self.app = app
        self.config = config
        self.state = "idle"            # idle | recording | processing
        self.hotkeys_paused = False
        self._rec_started = 0.0

        self.history = History(limit=int(config.get("history_limit", 200)))
        self.transcriber = Transcriber(config)
        self.cleaner = Cleaner(config)

        self.bridge = _HotkeyBridge()
        self.bridge.activated.connect(self.on_hotkey_down)
        self.bridge.deactivated.connect(self.on_hotkey_up)
        self.bridge.escape.connect(self.on_escape)

        self.recorder = Recorder(level_callback=self.bridge.level.emit)
        self.hotkeys = HotkeyManager()
        self.hotkeys.detector.on_activate = self.bridge.activated.emit
        self.hotkeys.detector.on_deactivate = self.bridge.deactivated.emit
        self.hotkeys.detector.on_escape = self.bridge.escape.emit

        self.injector = Injector(config, self.hotkeys.detector.modifiers_down)
        self.injector.finished.connect(self._on_inserted)

        self.overlay = Overlay()
        self.bridge.level.connect(self.overlay.set_level)

        self.max_timer = QTimer(self)
        self.max_timer.setSingleShot(True)
        self.max_timer.timeout.connect(self.stop_recording)

        base = QIcon(str(resource_path("icon.png")))
        self.icons = {"idle": _make_icon(base, None),
                      "recording": _make_icon(base, QColor("#ff4d5e")),
                      "processing": _make_icon(base, QColor("#7c8cff"))}
        app.setWindowIcon(self.icons["idle"])

        self.settings = SettingsWindow(config, self.history, self.icons["idle"])
        self.settings.hotkeyConfigChanged.connect(self.restart_hotkeys)
        self.settings.captureActive.connect(self._set_capture)
        self.settings.modelChanged.connect(self._on_model_changed)

        self._build_tray()

    # ------------------------------------------------------------------ setup
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.icons["idle"], self.app)
        menu = QMenu()
        self.act_toggle = QAction(tr("Start dictation"), menu)
        self.act_toggle.triggered.connect(self.toggle)
        menu.addAction(self.act_toggle)
        menu.addSeparator()
        mode_menu = menu.addMenu(tr("Mode"))
        grp = QActionGroup(mode_menu)
        self.act_mode_toggle = QAction(tr("Toggle (press – press)"), mode_menu, checkable=True)
        self.act_mode_hold = QAction(tr("Push-to-talk (hold)"), mode_menu, checkable=True)
        for a, m in ((self.act_mode_toggle, "toggle"), (self.act_mode_hold, "hold")):
            grp.addAction(a)
            mode_menu.addAction(a)
            a.triggered.connect(lambda _=False, mode=m: self._set_mode(mode))
        self._sync_mode_actions()
        act_settings = QAction(tr("Settings…"), menu)
        act_settings.triggered.connect(lambda: self.show_settings())
        menu.addAction(act_settings)
        menu.addSeparator()
        act_quit = QAction(tr("Quit"), menu)
        act_quit.triggered.connect(self.quit)
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self._update_tray()
        self.tray.show()
        self._menu = menu

    def _tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_settings()

    def _set_mode(self, mode: str) -> None:
        self.config.set("hotkey_mode", mode)
        self._sync_mode_actions()
        (self.settings.mode_hold if mode == "hold" else self.settings.mode_toggle).setChecked(True)

    def _sync_mode_actions(self) -> None:
        hold = self.config.get("hotkey_mode") == "hold"
        self.act_mode_hold.setChecked(hold)
        self.act_mode_toggle.setChecked(not hold)

    def _update_tray(self) -> None:
        self.tray.setIcon(self.icons.get(self.state, self.icons["idle"]))
        hk = format_hotkey(self.config.get("hotkey"))
        status = {"idle": tr("Ready"), "recording": tr("Recording…"), "processing": tr("Processing…")}[self.state]
        self.tray.setToolTip(f"{APP_NAME} – {status} ({hk})")
        self.act_toggle.setText(tr("Stop dictation") if self.state == "recording" else tr("Start dictation"))
        self.act_toggle.setEnabled(self.state != "processing")

    def start(self, show_settings: bool = False) -> None:
        self.restart_hotkeys()
        if not downloaded_models():
            self.show_settings(tab=1)
            self.settings.set_status(tr("Welcome! Download a speech model to get started (recommended model is marked with ★)."))
        elif show_settings or not self.config.get("start_minimized", True):
            self.show_settings()
        if not self.config.get("first_run_done"):
            self.config.set("first_run_done", True)
            self.notify(tr("Voicewright is running in the system tray. Shortcut:") + " "
                        + format_hotkey(self.config.get("hotkey")))
        self._preload_model()

    def _preload_model(self) -> None:
        if is_downloaded(self.config.get("whisper_model")) and self.config.get("keep_model_loaded", True):
            run_task(self.transcriber.load, on_error=lambda e: log.warning("Preload failed: %s", e))

    @Slot()
    def restart_hotkeys(self) -> None:
        try:
            used = self.hotkeys.start(self.config.get("hotkey"), self.config.get("hotkey_backend", "auto"))
        except ValueError as exc:
            self.notify(tr("Invalid shortcut:") + f" {exc}", error=True)
            return
        msg = ""
        if used == "none" and self.config.get("hotkey_backend") != "none":
            msg = tr("Global shortcut unavailable. Bind 'voicewright --toggle' to a desktop shortcut, "
                     "or on Linux add yourself to the 'input' group.")
        elif self.hotkeys.error == "WAYLAND_PYNPUT":
            msg = tr("Wayland: the shortcut only works while an X11/XWayland window is focused. "
                     "Use the evdev backend (input group) or bind 'voicewright --toggle' as desktop shortcut.")
        self.settings.set_status(msg)
        self._update_tray()

    def _set_capture(self, active: bool) -> None:
        self.hotkeys_paused = active
        self.hotkeys.detector.reset()

    def _on_model_changed(self) -> None:
        if self.state == "idle":
            self.transcriber.unload()
            self._preload_model()

    def show_settings(self, tab: int | None = None) -> None:
        if tab is not None:
            self.settings.tabs.setCurrentIndex(tab)
        self.settings.refresh_history()
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def notify(self, text: str, error: bool = False) -> None:
        log.info("notify: %s", text)
        if self.tray.isVisible() and QSystemTrayIcon.supportsMessages():
            self.tray.showMessage(APP_NAME, text,
                                  QSystemTrayIcon.Warning if error else QSystemTrayIcon.Information, 5000)

    def quit(self) -> None:
        self.hotkeys.stop()
        if self.recorder.recording:
            self.recorder.cancel()
        self.tray.hide()
        self.app.quit()

    # ------------------------------------------------------------------ hotkey events
    @Slot()
    def on_hotkey_down(self) -> None:
        if self.hotkeys_paused:
            return
        mode = self.config.get("hotkey_mode", "toggle")
        if self.state == "idle":
            self.start_recording()
        elif self.state == "recording" and mode == "toggle":
            self.stop_recording()

    @Slot()
    def on_hotkey_up(self) -> None:
        if self.hotkeys_paused or self.state != "recording":
            return
        if self.config.get("hotkey_mode") == "hold":
            held_ms = (time.time() - self._rec_started) * 1000
            if held_ms < int(self.config.get("min_hold_ms", 250)):
                self.cancel_recording(tr("Hold the shortcut while speaking"))
            else:
                self.stop_recording()

    @Slot()
    def on_escape(self) -> None:
        if self.state == "recording" and self.config.get("cancel_with_escape", True):
            self.cancel_recording()

    # ------------------------------------------------------------------ IPC commands
    def handle_command(self, cmd: str) -> None:
        log.info("IPC command: %s", cmd)
        if cmd == "toggle":
            self.toggle()
        elif cmd == "start" and self.state == "idle":
            self.start_recording()
        elif cmd == "stop" and self.state == "recording":
            self.stop_recording()
        elif cmd == "cancel" and self.state == "recording":
            self.cancel_recording()
        elif cmd == "show":
            self.show_settings()
        elif cmd == "quit":
            self.quit()

    def toggle(self) -> None:
        if self.state == "idle":
            self.start_recording()
        elif self.state == "recording":
            self.stop_recording()

    # ------------------------------------------------------------------ pipeline
    def _set_state(self, state: str) -> None:
        self.state = state
        self._update_tray()

    def start_recording(self) -> None:
        if self.state != "idle":
            return
        if not is_downloaded(self.config.get("whisper_model")):
            if self.config.get("sounds_enabled"):
                play_sound("error")
            self.notify(tr("No speech model downloaded. Please download one in the settings."), error=True)
            self.show_settings(tab=1)
            return
        try:
            self.recorder.start(self.config.get("input_device"))
        except AudioError as exc:
            if self.config.get("sounds_enabled"):
                play_sound("error")
            self.notify(tr("Microphone error:") + f" {exc}", error=True)
            return
        self._rec_started = time.time()
        if self.config.get("sounds_enabled"):
            play_sound("start")
        if self.config.get("show_overlay"):
            self.overlay.position = self.config.get("overlay_position", "bottom")
            self.overlay.show_state("recording")
        self.max_timer.start(int(self.config.get("max_recording_seconds", 600)) * 1000)
        self._set_state("recording")

    def cancel_recording(self, message: str = "") -> None:
        self.max_timer.stop()
        self.recorder.cancel()
        if self.config.get("sounds_enabled"):
            play_sound("cancel")
        self._set_state("idle")
        if self.config.get("show_overlay"):
            self.overlay.show_state("error", message or tr("Cancelled"), auto_hide_ms=1200)

    @Slot()
    def stop_recording(self) -> None:
        if self.state != "recording":
            return
        self.max_timer.stop()
        audio = self.recorder.stop()
        if self.config.get("sounds_enabled"):
            play_sound("stop")
        duration = audio.size / SAMPLE_RATE
        if self.config.get("silence_trim", True):
            audio = trim_silence(audio)
        if audio.size < SAMPLE_RATE * 0.3:
            self._set_state("idle")
            if self.config.get("show_overlay"):
                self.overlay.show_state("error", tr("No speech detected"), auto_hide_ms=1500)
            return
        self._set_state("processing")
        if self.config.get("show_overlay"):
            self.overlay.show_state("processing", tr("Transcribing…"))
        run_task(self._process, audio, duration, on_done=self._on_processed, on_error=self._on_failed)

    def _process(self, audio, duration: float) -> dict:
        raw, lang = self.transcriber.transcribe(audio, SAMPLE_RATE)
        text, provider, warn = raw, "none", ""
        if raw and self.config.get("cleanup_enabled", True):
            provider = self.config.get("cleanup_provider", "none")
            try:
                text = self.cleaner.clean(raw, lang)
            except Exception as exc:  # noqa: BLE001
                log.warning("Cleanup failed: %s", exc)
                warn = str(exc)
                if self.config.get("cleanup_fallback_rules", True):
                    text, provider = rules_cleanup(raw), "rules"
        return {"raw": raw, "text": text, "lang": lang, "duration": duration, "provider": provider, "warn": warn}

    def _on_processed(self, res: dict) -> None:
        text = (res["text"] or "").strip()
        if not text:
            self._set_state("idle")
            if self.config.get("show_overlay"):
                self.overlay.show_state("error", tr("No speech detected"), auto_hide_ms=1500)
            return
        if res["warn"]:
            w = res["warn"]
            if w.startswith("NO_KEY:"):
                w = tr("No API key set for") + " " + w.split(":", 1)[1]
            p = PROVIDERS_BY_ID.get(self.config.get("cleanup_provider"))
            self.notify(tr("AI cleanup failed") + (f" ({p.name})" if p else "") + f": {w}", error=True)
        if self.config.get("history_enabled", True):
            self.history.add(res["raw"], text, res["lang"], res["duration"], res["provider"])
            if self.settings.isVisible():
                self.settings.refresh_history()
        self._pending_text = text
        self.injector.insert(text)

    def _on_inserted(self, ok: bool, msg: str) -> None:
        self._set_state("idle")
        if not self.config.get("show_overlay"):
            if msg == "CLIPBOARD_ONLY" and not ok:
                self.notify(tr("Text copied to clipboard – paste it with Ctrl+V."))
            return
        if msg == "CLIPBOARD_ONLY":
            self.overlay.show_state("done", tr("Copied to clipboard"), auto_hide_ms=1800)
        elif ok:
            self.overlay.show_state("done", tr("Inserted"), auto_hide_ms=900)
        else:
            self.overlay.show_state("error", tr("Insert failed"), auto_hide_ms=1800)

    def _on_failed(self, msg: str) -> None:
        self._set_state("idle")
        if self.config.get("sounds_enabled"):
            play_sound("error")
        if msg.startswith("MODEL_MISSING:"):
            msg = tr("No speech model downloaded. Please download one in the settings.")
        log.error("Processing failed: %s", msg)
        if self.config.get("show_overlay"):
            self.overlay.show_state("error", tr("Error"), auto_hide_ms=2000)
        self.notify(tr("Transcription failed:") + f" {msg}", error=True)
