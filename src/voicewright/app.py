"""Application controller: ties hotkeys, recording, transcription, cleanup and insertion together."""
from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap, QGuiApplication
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from voicewright import APP_NAME, inject
from voicewright.audio import SAMPLE_RATE, AudioError, Recorder, play_sound, trim_silence
from voicewright.cleanup import Cleaner, CleanupResult
from voicewright.config import Config
from voicewright.dictation import DictationMachine
from voicewright.history import History
from voicewright.hotkey import HotkeyManager, format_hotkey
from voicewright.i18n import tr
from voicewright.injector import Injector
from voicewright.models import downloaded_models, is_downloaded
from voicewright.paths import resource_path, session_type
from voicewright.stats import Stats
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
        self._transform_before = ""

        self.history = History(limit=int(config.get("history_limit", 200)))
        self.stats = Stats()
        self.transcriber = Transcriber(config)
        self.cleaner = Cleaner(config)

        self.machine = DictationMachine(
            mode=config.get("hotkey_mode", "hybrid"),
            tap_threshold_ms=int(config.get("tap_threshold_ms", 350)),
            min_hold_ms=int(config.get("min_hold_ms", 250)),
        )
        self.machine.on_start = self.start_recording
        self.machine.on_stop = self.stop_recording
        self.machine.on_cancel = self.cancel_recording

        self.bridge = _HotkeyBridge()
        self.bridge.activated.connect(self.on_hotkey_down)
        self.bridge.deactivated.connect(self.on_hotkey_up)
        self.bridge.escape.connect(self.on_escape)

        self.recorder = Recorder(level_callback=self.bridge.level.emit)
        self.hotkeys = HotkeyManager()
        self.hotkeys.detector.on_activate = self.bridge.activated.emit
        self.hotkeys.detector.on_deactivate = self.bridge.deactivated.emit
        self.hotkeys.detector.on_escape = self.bridge.escape.emit

        self.injector = Injector(config)
        self.injector.finished.connect(self._on_inserted)
        self.injector.permission_hint.connect(lambda msg: self.notify(msg, error=True))

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

        self.settings = SettingsWindow(config, self.history, self.stats, self.icons["idle"])
        self.settings.hotkeyConfigChanged.connect(self._on_hotkey_config_changed)
        self.settings.captureActive.connect(self._set_capture)
        self.settings.modelChanged.connect(self._on_model_changed)
        self.settings.cleanupChanged.connect(self._on_cleanup_changed)
        self.settings.outputChanged.connect(self._on_output_changed)
        self.settings.waylandPermissionRequested.connect(self.request_wayland_permission)
        self.settings.dictation_button.clicked.connect(self.toggle)

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
        self.act_mode_hybrid = QAction(tr("Tap or hold (recommended)"), mode_menu, checkable=True)
        self.act_mode_toggle = QAction(tr("Tap to start and stop"), mode_menu, checkable=True)
        self.act_mode_hold = QAction(tr("Hold to talk"), mode_menu, checkable=True)
        for a, m in ((self.act_mode_hybrid, "hybrid"), (self.act_mode_toggle, "toggle"),
                     (self.act_mode_hold, "hold")):
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
        self.machine.configure(mode=mode)
        self._sync_mode_actions()
        self.settings.sync_mode(mode)

    def _sync_mode_actions(self) -> None:
        mode = self.config.get("hotkey_mode", "hybrid")
        self.act_mode_hybrid.setChecked(mode == "hybrid")
        self.act_mode_hold.setChecked(mode == "hold")
        self.act_mode_toggle.setChecked(mode == "toggle")

    def _update_tray(self) -> None:
        self.tray.setIcon(self.icons.get(self.state, self.icons["idle"]))
        hk = format_hotkey(self.config.get("hotkey"))
        status = {"idle": tr("Ready"), "recording": tr("Recording…"),
                  "processing": tr("Processing…")}[self.state]
        self.tray.setToolTip(f"{APP_NAME} – {status} ({hk})")
        self.act_toggle.setText(tr("Stop dictation") if self.state == "recording"
                                else tr("Start dictation"))
        self.act_toggle.setEnabled(self.state != "processing")
        self.settings.dictation_button.setText(self.act_toggle.text())
        self.settings.dictation_button.setEnabled(self.act_toggle.isEnabled())

    def start(self, show_settings: bool = False) -> None:
        self.restart_hotkeys()
        if not downloaded_models():
            self.show_settings(tab=1)
            self.settings.set_status(
                tr("Welcome! Download a speech model to get started (recommended model is marked with ★)."))
        elif show_settings or not self.config.get("start_minimized", True):
            self.show_settings()
        if not self.config.get("first_run_done"):
            self.config.set("first_run_done", True)
            self.notify(tr("Voicewright is running in the system tray. Shortcut:") + " "
                        + format_hotkey(self.config.get("hotkey")))
        self._preload_model()

    def _preload_model(self) -> None:
        if is_downloaded(self.config.get("speech_model")) and self.config.get("keep_model_loaded", True):
            run_task(self.transcriber.load, on_error=lambda e: log.warning("Preload failed: %s", e))

    @Slot()
    def restart_hotkeys(self) -> None:
        try:
            used = self.hotkeys.start(
                self.config.get("hotkey"),
                self.config.get("hotkey_backend", "auto"),
                wayland=self.config.get("wayland_hotkey", "portal"),
            )
        except ValueError as exc:
            self.notify(tr("Invalid shortcut:") + f" {exc}", error=True)
            return
        msg = ""
        if used == "none" and session_type() == "wayland":
            if self.hotkeys.error == "PORTAL_UNAVAILABLE":
                msg = tr("The desktop portal is unavailable. Bind voicewright --toggle "
                         "in your desktop settings, or install a portal backend.")
            else:
                msg = tr("On Wayland, set a desktop shortcut for voicewright --toggle.")
        elif used == "none" and self.config.get("hotkey_backend") != "none":
            msg = tr("Global shortcut unavailable. Bind voicewright --toggle in your desktop settings.")
        self.settings.set_status(msg)
        self._update_tray()

    def _set_capture(self, active: bool) -> None:
        self.hotkeys_paused = active
        self.hotkeys.detector.reset()

    @Slot()
    def _on_hotkey_config_changed(self) -> None:
        self.machine.configure(
            mode=self.config.get("hotkey_mode", "hybrid"),
            tap_threshold_ms=int(self.config.get("tap_threshold_ms", 350)),
            min_hold_ms=int(self.config.get("min_hold_ms", 250)),
        )
        self._sync_mode_actions()
        self.restart_hotkeys()

    def _on_model_changed(self) -> None:
        if self.state == "idle":
            self.transcriber.unload()
            self._preload_model()
        self.settings.refresh_overview()

    def _on_cleanup_changed(self) -> None:
        self.cleaner = Cleaner(self.config, self.cleaner._runtime)

    def _on_output_changed(self) -> None:
        desc = self.injector.describe_method()
        self.settings.refresh_output(desc)
        self.settings.set_status(desc)

    def show_settings(self, tab: int | None = None) -> None:
        if tab is not None:
            self.settings.select_page(tab)
        self.settings.refresh_overview()
        self.settings.refresh_history()
        self.settings.refresh_stats()
        self.settings.refresh_output(self.injector.describe_method())
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def notify(self, text: str, error: bool = False) -> None:
        log.info("notify: %s", text)
        if self.settings.isVisible():
            self.settings.set_status(text, error=error)
        if self.tray.isVisible() and QSystemTrayIcon.supportsMessages():
            self.tray.showMessage(APP_NAME, text,
                                  QSystemTrayIcon.Warning if error else QSystemTrayIcon.Information,
                                  5000)

    def quit(self) -> None:
        self.hotkeys.stop()
        self.injector.portal.disconnect()
        try:
            self.cleaner.runtime().stop()
        except Exception:  # noqa: BLE001
            pass
        if self.recorder.recording:
            self.recorder.cancel()
        self.tray.hide()
        self.app.quit()

    # ------------------------------------------------------------------ hotkey events
    @Slot()
    def on_hotkey_down(self) -> None:
        if self.hotkeys_paused:
            return
        self.machine.key_down()

    @Slot()
    def on_hotkey_up(self) -> None:
        if self.hotkeys_paused:
            return
        self.machine.key_up()

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
        elif cmd == "transform":
            self.transform_selection()
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
        model_id = self.config.get("speech_model")
        if not is_downloaded(model_id):
            if self.config.get("sounds_enabled"):
                play_sound("error")
            self.notify(tr("No speech model downloaded. Please download one in the settings."),
                        error=True)
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
        run_task(self._process, audio, duration, on_done=self._on_processed,
                 on_error=self._on_failed)

    def _process(self, audio, duration: float) -> dict:
        raw, lang = self.transcriber.transcribe(audio, SAMPLE_RATE)
        result = CleanupResult(raw=raw, text=raw, provider="none")
        warn = ""
        if raw:
            try:
                result = self.cleaner.process(raw, lang)
            except Exception as exc:  # noqa: BLE001
                log.warning("Cleanup failed: %s", exc)
                warn = str(exc)
                from voicewright.cleanup import rules_cleanup
                result = CleanupResult(raw=raw, text=rules_cleanup(raw), provider="rules")
        if result.guarded:
            warn = "guard"
        return {"raw": raw, "text": result.text, "lang": lang, "duration": duration,
                "provider": result.provider, "warn": warn, "structure": result.structure}

    def _on_processed(self, res: dict) -> None:
        text = (res["text"] or "").strip()
        if not text:
            self._set_state("idle")
            if self.config.get("show_overlay"):
                self.overlay.show_state("error", tr("No speech detected"), auto_hide_ms=1500)
            return
        if res["warn"] and res["warn"] != "guard":
            w = res["warn"]
            if w.startswith("NO_KEY:"):
                w = tr("No API key set for") + " " + w.split(":", 1)[1]
            self.notify(tr("AI cleanup failed") + f": {w}", error=True)
        if self.config.get("history_enabled", False):
            self.history.add(res["raw"], text, res["lang"], res["duration"], res["provider"])
            if self.settings.isVisible():
                self.settings.refresh_history()
        if self.config.get("stats_enabled", True):
            self.stats.record(text, res["duration"])
            if self.settings.isVisible():
                self.settings.refresh_stats()
        self.injector.insert(text)

    def _on_inserted(self, ok: bool, msg: str) -> None:
        self._set_state("idle")
        if not self.config.get("show_overlay"):
            if msg == "CLIPBOARD_ONLY":
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
        elif msg == "SHERPA_MISSING":
            msg = tr("This model needs the sherpa-onnx package. Install the 'asr' extra "
                     "or choose a Whisper model.")
        log.error("Processing failed: %s", msg)
        if self.config.get("show_overlay"):
            self.overlay.show_state("error", tr("Error"), auto_hide_ms=2000)
        self.notify(tr("Transcription failed:") + f" {msg}", error=True)

    # ------------------------------------------------------------------ selection transform
    def transform_selection(self) -> None:
        """Rewrite the current selection, but only if it really changed."""
        if self.state != "idle":
            return
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return
        self._transform_before = clipboard.text()
        self._set_state("processing")
        if self.config.get("show_overlay"):
            self.overlay.show_state("processing", tr("Reading selection…"))
        inject.copy_selection(
            wayland=self.config.get("wayland_inject", "auto"),
            ydotool=bool(self.config.get("ydotool_enabled", False)),
            portal_paste=self.injector.portal.paste if self.injector.portal.connected else None,
        )
        QTimer.singleShot(220, self._after_copy_selection)

    def _after_copy_selection(self) -> None:
        clipboard = QGuiApplication.clipboard()
        selected = clipboard.text() if clipboard is not None else ""
        if not selected.strip() or selected == self._transform_before:
            self._set_state("idle")
            if self.config.get("show_overlay"):
                self.overlay.show_state("error", tr("No selection detected"), auto_hide_ms=1600)
            return
        run_task(self._transform, selected, on_done=self._on_transformed,
                 on_error=self._on_failed)

    def _transform(self, selected: str) -> dict:
        result = self.cleaner.process(selected, "")
        return {"text": result.text, "provider": result.provider}

    def _on_transformed(self, res: dict) -> None:
        text = (res.get("text") or "").strip()
        if not text:
            self._on_failed(tr("No text produced"))
            return
        self.injector.insert(text)

    # ------------------------------------------------------------------ permissions
    def request_wayland_permission(self) -> None:
        def done(ok: bool) -> None:
            if ok:
                self.config.set("wayland_consent", True)
                self.notify(tr("Keyboard control granted. Text is now inserted directly."))
            else:
                self.notify(tr("Keyboard control was not granted. Voicewright falls back to "
                               "wtype or the clipboard."), error=True)
            self.settings.refresh_output(self.injector.describe_method())

        run_task(self.injector.connect_portal, on_done=done,
                 on_error=lambda e: self.notify(str(e), error=True))
