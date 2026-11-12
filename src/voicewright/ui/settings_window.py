"""Main settings window."""
from __future__ import annotations

import datetime
import logging
import platform
import sys

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QRadioButton, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget,
)

from voicewright import APP_NAME, __version__, autostart
from voicewright.audio import list_input_devices
from voicewright.cleanup import LANGUAGE_NAMES, PROVIDERS, PROVIDERS_BY_ID, Cleaner
from voicewright.config import Config
from voicewright.history import History
from voicewright.hotkey import format_hotkey
from voicewright.i18n import tr
from voicewright.keystore import get_api_key, set_api_key
from voicewright.models import (
    CATALOG, delete_model, download_model, is_downloaded, recommended_model,
)
from voicewright.paths import IS_LINUX, config_dir, data_dir, logs_dir, models_dir, session_type
from voicewright.transcriber import cuda_available
from voicewright.ui.hotkey_edit import HotkeyEdit
from voicewright.ui.tasks import run_task

log = logging.getLogger(__name__)

WHISPER_LANGS = ["auto", "de", "en", "fr", "es", "it", "pt", "nl", "pl", "tr", "ru", "uk", "cs", "sv",
                 "da", "no", "fi", "el", "hu", "ro", "ar", "he", "hi", "ja", "ko", "zh", "vi", "id", "th"]


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setOpenExternalLinks(True)
    lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
    lbl.setStyleSheet("color: #6b7280; font-size: 11px;")
    return lbl


def _lang_label(code: str) -> str:
    if code == "auto":
        return tr("Automatic detection")
    return f"{tr(LANGUAGE_NAMES.get(code, code))} ({code})"


class SettingsWindow(QWidget):
    hotkeyConfigChanged = Signal()
    captureActive = Signal(bool)
    modelChanged = Signal()

    def __init__(self, config: Config, history: History, icon: QIcon) -> None:
        super().__init__()
        self.config = config
        self.history = history
        self.cleaner = Cleaner(config)
        self.setWindowTitle(f"{APP_NAME} – {tr('Settings')}")
        self.setWindowIcon(icon)
        self.resize(820, 640)
        self._download_task = None

        root = QVBoxLayout(self)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding:8px;border-radius:6px;background:palette(alternate-base);")
        root.addWidget(self.status_label)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.tabs.addTab(self._build_general(), tr("General"))
        self.tabs.addTab(self._build_models(), tr("Speech model"))
        self.tabs.addTab(self._build_cleanup(), tr("AI cleanup"))
        self.tabs.addTab(self._build_output(), tr("Output"))
        self.tabs.addTab(self._build_history(), tr("History"))
        self.tabs.addTab(self._build_about(), tr("About"))

        bottom = QHBoxLayout()
        self.dictation_button = QPushButton(tr("Start dictation"))
        bottom.addWidget(self.dictation_button)
        bottom.addStretch(1)
        close = QPushButton(tr("Close"))
        close.clicked.connect(self.hide)
        bottom.addWidget(close)
        root.addLayout(bottom)

    # ======================================================================
    # helpers
    def _bind_check(self, cb: QCheckBox, key: str, after=None) -> QCheckBox:
        cb.setChecked(bool(self.config.get(key)))
        cb.toggled.connect(lambda v: (self.config.set(key, bool(v)), after and after()))
        return cb

    def _bind_combo(self, combo: QComboBox, key: str, items: list[tuple[str, str]], after=None) -> QComboBox:
        for value, label in items:
            combo.addItem(label, value)
        idx = combo.findData(self.config.get(key))
        combo.setCurrentIndex(max(0, idx))
        combo.currentIndexChanged.connect(
            lambda _i: (self.config.set(key, combo.currentData()), after and after()))
        return combo

    def _bind_spin(self, spin: QSpinBox, key: str, lo: int, hi: int, suffix: str = "") -> QSpinBox:
        spin.setRange(lo, hi)
        spin.setValue(int(self.config.get(key)))
        if suffix:
            spin.setSuffix(suffix)
        spin.valueChanged.connect(lambda v: self.config.set(key, int(v)))
        return spin

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self.status_label.setVisible(bool(text))

    # ======================================================================
    # General
    def _build_general(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        g = QGroupBox(tr("Shortcut"))
        f = QFormLayout(g)
        self.hotkey_edit = HotkeyEdit(self.config.get("hotkey"))
        self.hotkey_edit.hotkeyChanged.connect(self._on_hotkey)
        self.hotkey_edit.error.connect(lambda m: QMessageBox.warning(self, APP_NAME, m))
        self.hotkey_edit.capturingChanged.connect(self.captureActive.emit)
        f.addRow(tr("Dictation shortcut:"), self.hotkey_edit)

        mode_box = QWidget()
        ml = QVBoxLayout(mode_box)
        ml.setContentsMargins(0, 0, 0, 0)
        self.mode_toggle = QRadioButton(tr("Toggle – press once to start, press again to finish"))
        self.mode_hold = QRadioButton(tr("Push-to-talk – hold while speaking, release to finish"))
        grp = QButtonGroup(self)
        grp.addButton(self.mode_toggle)
        grp.addButton(self.mode_hold)
        (self.mode_hold if self.config.get("hotkey_mode") == "hold" else self.mode_toggle).setChecked(True)
        self.mode_toggle.toggled.connect(
            lambda v: self.config.set("hotkey_mode", "toggle" if v else "hold"))
        ml.addWidget(self.mode_toggle)
        ml.addWidget(self.mode_hold)
        f.addRow(tr("Mode:"), mode_box)

        f.addRow("", self._bind_check(QCheckBox(tr("Esc cancels a running recording")), "cancel_with_escape"))
        backends = [("auto", tr("Automatic")), ("pynput", "pynput (Windows / macOS / X11)")]
        backends.append(("none", tr("None – use CLI/desktop shortcut")))
        f.addRow(tr("Hotkey backend:"),
                 self._bind_combo(QComboBox(), "hotkey_backend", backends, self.hotkeyConfigChanged.emit))
        if IS_LINUX and session_type() == "wayland":
            f.addRow("", _hint(tr(
                "On Wayland, set a desktop shortcut for voicewright --toggle.")))
        lay.addWidget(g)

        g = QGroupBox(tr("Microphone"))
        f = QFormLayout(g)
        self.mic_combo = QComboBox()
        self._fill_mics()
        self.mic_combo.currentIndexChanged.connect(
            lambda _i: self.config.set("input_device", self.mic_combo.currentData()))
        row = QHBoxLayout()
        row.addWidget(self.mic_combo, 1)
        refresh = QPushButton(tr("Refresh"))
        refresh.clicked.connect(self._fill_mics)
        row.addWidget(refresh)
        f.addRow(tr("Input device:"), row)
        f.addRow(tr("Max. recording length:"),
                 self._bind_spin(QSpinBox(), "max_recording_seconds", 10, 3600, " s"))
        f.addRow("", self._bind_check(QCheckBox(tr("Play start/stop sounds")), "sounds_enabled"))
        lay.addWidget(g)

        g = QGroupBox(tr("Application"))
        f = QFormLayout(g)
        f.addRow("", self._bind_check(QCheckBox(tr("Show recording indicator")), "show_overlay"))
        f.addRow(tr("Indicator position:"), self._bind_combo(
            QComboBox(), "overlay_position", [("bottom", tr("Bottom")), ("top", tr("Top"))]))
        f.addRow("", self._bind_check(QCheckBox(tr("Start minimized to tray")), "start_minimized"))
        self.autostart_cb = QCheckBox(tr("Launch at login"))
        self.autostart_cb.setChecked(autostart.is_enabled())
        self.autostart_cb.toggled.connect(self._on_autostart)
        f.addRow("", self.autostart_cb)
        f.addRow(tr("Interface language:"), self._bind_combo(
            QComboBox(), "ui_language", [("auto", tr("System")), ("de", "Deutsch"), ("en", "English")],
            lambda: self.set_status(tr("Restart Voicewright to apply the language."))))
        lay.addWidget(g)
        lay.addStretch(1)
        return w

    def _fill_mics(self) -> None:
        self.mic_combo.blockSignals(True)
        self.mic_combo.clear()
        self.mic_combo.addItem(tr("System default"), None)
        for name in list_input_devices():
            self.mic_combo.addItem(name, name)
        idx = self.mic_combo.findData(self.config.get("input_device"))
        self.mic_combo.setCurrentIndex(max(0, idx))
        self.mic_combo.blockSignals(False)

    def _on_hotkey(self, hk: str) -> None:
        self.config.set("hotkey", hk)
        self.hotkeyConfigChanged.emit()

    def _on_autostart(self, v: bool) -> None:
        try:
            autostart.set_enabled(v)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))

    # ======================================================================
    # Models
    def _build_models(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        rec = recommended_model()
        hw = tr("NVIDIA GPU detected (CUDA).") if cuda_available() else tr("No CUDA GPU detected – CPU mode.")
        lay.addWidget(_hint(tr("All speech recognition runs locally on your computer. "
                               "Download a model and select it.") + " " + hw + " "
                            + tr("Recommended for you:") + f" <b>{rec}</b>"))

        self.model_table = QTableWidget(len(CATALOG), 6)
        self.model_table.setHorizontalHeaderLabels(
            [tr("Model"), tr("Size"), tr("Languages"), tr("Speed"), tr("Accuracy"), tr("Status")])
        self.model_table.verticalHeader().setVisible(False)
        self.model_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.model_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.model_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.model_table.itemSelectionChanged.connect(self._update_model_buttons)
        lay.addWidget(self.model_table, 1)
        self.model_note = _hint("")
        lay.addWidget(self.model_note)

        row = QHBoxLayout()
        self.btn_download = QPushButton(tr("Download"))
        self.btn_use = QPushButton(tr("Use this model"))
        self.btn_delete = QPushButton(tr("Delete"))
        self.btn_cancel_dl = QPushButton(tr("Cancel download"))
        self.btn_download.clicked.connect(self._download_selected)
        self.btn_use.clicked.connect(self._use_selected)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_cancel_dl.clicked.connect(self._cancel_download)
        self.btn_cancel_dl.setVisible(False)
        for b in (self.btn_download, self.btn_use, self.btn_delete, self.btn_cancel_dl):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.dl_progress = QProgressBar()
        self.dl_progress.setVisible(False)
        lay.addWidget(self.dl_progress)

        g = QGroupBox(tr("Recognition"))
        f = QFormLayout(g)
        f.addRow(tr("Spoken language:"), self._bind_combo(
            QComboBox(), "language", [(c, _lang_label(c)) for c in WHISPER_LANGS]))
        f.addRow(tr("Task:"), self._bind_combo(QComboBox(), "whisper_task", [
            ("transcribe", tr("Transcribe (keep language)")),
            ("translate", tr("Translate to English (offline, Whisper)"))]))
        f.addRow(tr("Device:"), self._bind_combo(QComboBox(), "whisper_device", [
            ("auto", tr("Automatic")), ("cpu", "CPU"), ("cuda", "NVIDIA CUDA")], self.modelChanged.emit))
        f.addRow(tr("Precision:"), self._bind_combo(QComboBox(), "whisper_compute_type", [
            ("auto", tr("Automatic")), ("int8", "int8"), ("int8_float16", "int8_float16"),
            ("float16", "float16"), ("float32", "float32")], self.modelChanged.emit))
        prompt = QLineEdit(self.config.get("initial_prompt"))
        prompt.setPlaceholderText(tr("Optional: names, jargon, style hints for Whisper"))
        prompt.editingFinished.connect(lambda: self.config.set("initial_prompt", prompt.text()))
        f.addRow(tr("Vocabulary prompt:"), prompt)
        f.addRow("", self._bind_check(QCheckBox(tr("Skip silence (VAD filter)")), "vad_filter"))
        f.addRow("", self._bind_check(QCheckBox(tr("Keep model in memory (faster)")), "keep_model_loaded"))
        lay.addWidget(g)
        self._refresh_models()
        return w

    def _selected_model(self) -> str | None:
        rows = self.model_table.selectionModel().selectedRows()
        return CATALOG[rows[0].row()].id if rows else None

    def _refresh_models(self) -> None:
        active = self.config.get("whisper_model")
        rec = recommended_model()
        for r, m in enumerate(CATALOG):
            name = m.id + ("  ★ " + tr("recommended") if m.id == rec else "")
            if m.recommended and m.id != rec:
                name += f"  ({tr('recommended for')} {m.recommended.upper()})"
            status = tr("Not downloaded")
            if is_downloaded(m.id):
                status = tr("Active") if m.id == active else tr("Downloaded")
            vals = [name, f"{m.size_mb} MB" if m.size_mb < 1000 else f"{m.size_mb / 1000:.1f} GB",
                    tr("Multilingual") if m.languages == "multi" else tr("English only"),
                    "●" * m.speed + "○" * (5 - m.speed), "●" * m.accuracy + "○" * (5 - m.accuracy), status]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if m.id == active and is_downloaded(m.id):
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.model_table.setItem(r, c, item)
        self.model_table.resizeColumnsToContents()
        self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._update_model_buttons()

    def _update_model_buttons(self) -> None:
        mid = self._selected_model()
        downloading = self._download_task is not None
        dl = bool(mid and is_downloaded(mid))
        self.btn_download.setEnabled(bool(mid) and not dl and not downloading)
        self.btn_use.setEnabled(dl and mid != self.config.get("whisper_model"))
        self.btn_delete.setEnabled(dl and not downloading)
        if mid:
            m = next(x for x in CATALOG if x.id == mid)
            self.model_note.setText(f"<b>{m.id}</b>: {tr(m.note)}")

    def _download_selected(self) -> None:
        mid = self._selected_model()
        if not mid:
            return
        self.dl_progress.setVisible(True)
        self.dl_progress.setRange(0, 0)
        self.btn_cancel_dl.setVisible(True)

        def on_progress(done, total, name):
            if total <= 1:  # size unknown
                self.dl_progress.setRange(0, 0)
                return
            self.dl_progress.setRange(0, 1000)
            self.dl_progress.setValue(int(1000 * done / max(1, total)))
            self.dl_progress.setFormat(f"{mid}: {done / 1e6:.0f} / {total / 1e6:.0f} MB  ({name})")

        def on_done(_r):
            self._download_task = None
            self.dl_progress.setVisible(False)
            self.btn_cancel_dl.setVisible(False)
            if not is_downloaded(self.config.get("whisper_model")):
                self.config.set("whisper_model", mid)
                self.modelChanged.emit()
            self._refresh_models()
            self.set_status(tr("Model downloaded:") + f" {mid}")

        def on_error(msg):
            self._download_task = None
            self.dl_progress.setVisible(False)
            self.btn_cancel_dl.setVisible(False)
            self._refresh_models()
            if msg != "DownloadCancelled":
                QMessageBox.warning(self, APP_NAME, tr("Download failed:") + f"\n{msg}")

        self._download_task = run_task(download_model, mid, with_progress=True, on_done=on_done,
                                       on_error=on_error, on_progress=on_progress)
        self._update_model_buttons()

    def _cancel_download(self) -> None:
        if self._download_task is not None:
            self._download_task.cancel_event.set()

    def _use_selected(self) -> None:
        mid = self._selected_model()
        if mid and is_downloaded(mid):
            self.config.set("whisper_model", mid)
            self.modelChanged.emit()
            self._refresh_models()

    def _delete_selected(self) -> None:
        mid = self._selected_model()
        if not mid:
            return
        if QMessageBox.question(self, APP_NAME, tr("Delete model?") + f" {mid}") != QMessageBox.Yes:
            return
        if mid == self.config.get("whisper_model"):
            self.modelChanged.emit()
        delete_model(mid)
        self._refresh_models()

    # ======================================================================
    # Cleanup
    def _build_cleanup(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(_hint(tr(
            "After transcription the raw text can be cleaned up (filler words, punctuation, "
            "self-corrections) and optionally translated. Bring your own API key, or use a local "
            "model via Ollama / LM Studio, or the offline rules.")))
        lay.addWidget(self._bind_check(QCheckBox(tr("Enable cleanup")), "cleanup_enabled",
                                       self._update_provider_ui))

        g = QGroupBox(tr("Provider"))
        f = QFormLayout(g)
        self.provider_combo = QComboBox()
        for p in PROVIDERS:
            label = tr(p.name) if p.kind == "rules" or p.id == "custom" else p.name
            self.provider_combo.addItem(label, p.id)
        self.provider_combo.setCurrentIndex(max(0, self.provider_combo.findData(self.config.get("cleanup_provider"))))
        self.provider_combo.currentIndexChanged.connect(self._on_provider)
        f.addRow(tr("Provider:"), self.provider_combo)

        key_row = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText(tr("Paste your API key"))
        self.key_edit.editingFinished.connect(self._save_key)
        self.key_show = QPushButton(tr("Show"))
        self.key_show.setCheckable(True)
        self.key_show.toggled.connect(
            lambda v: self.key_edit.setEchoMode(QLineEdit.Normal if v else QLineEdit.Password))
        self.key_link = QPushButton(tr("Get key"))
        self.key_link.clicked.connect(self._open_key_url)
        key_row.addWidget(self.key_edit, 1)
        key_row.addWidget(self.key_show)
        key_row.addWidget(self.key_link)
        self.key_label = QLabel(tr("API key:"))
        f.addRow(self.key_label, key_row)

        self.url_edit = QLineEdit()
        self.url_edit.editingFinished.connect(self._save_url)
        self.url_label = QLabel(tr("Server URL:"))
        f.addRow(self.url_label, self.url_edit)

        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(280)
        self.model_combo.currentTextChanged.connect(self._on_cleanup_model)
        self.btn_models = QPushButton(tr("Load models"))
        self.btn_models.clicked.connect(self._load_models)
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.btn_models)
        self.model_label = QLabel(tr("Model:"))
        f.addRow(self.model_label, model_row)

        test_row = QHBoxLayout()
        self.btn_test = QPushButton(tr("Test connection"))
        self.btn_test.clicked.connect(self._test_cleanup)
        self.test_result = QLabel()
        self.test_result.setWordWrap(True)
        test_row.addWidget(self.btn_test)
        test_row.addWidget(self.test_result, 1)
        f.addRow("", test_row)
        self.key_hint = _hint("")
        f.addRow("", self.key_hint)
        lay.addWidget(g)

        g = QGroupBox(tr("Style and translation"))
        f = QFormLayout(g)
        f.addRow(tr("Style:"), self._bind_combo(QComboBox(), "cleanup_style", [
            ("clean", tr("Clean – remove fillers, fix grammar (recommended)")),
            ("minimal", tr("Minimal – punctuation only")),
            ("formal", tr("Formal – professional writing")),
            ("casual", tr("Casual – chat style"))]))
        f.addRow(tr("Output language:"), self._bind_combo(QComboBox(), "output_language",
                 [("same", tr("Same as spoken (no translation)"))]
                 + [(c, _lang_label(c)) for c in WHISPER_LANGS if c != "auto"]))
        self.instr_edit = QPlainTextEdit(self.config.get("custom_instructions"))
        self.instr_edit.setPlaceholderText(tr("e.g. Use British spelling. Write numbers as digits."))
        self.instr_edit.setMaximumHeight(70)
        self.instr_edit.textChanged.connect(
            lambda: self.config.set("custom_instructions", self.instr_edit.toPlainText()))
        f.addRow(tr("Custom instructions:"), self.instr_edit)
        self.dict_edit = QLineEdit(", ".join(self.config.get("custom_dictionary")))
        self.dict_edit.setPlaceholderText(tr("Comma separated: Voicewright, Kubernetes, Dr. Müller"))
        self.dict_edit.editingFinished.connect(lambda: self.config.set(
            "custom_dictionary", [x.strip() for x in self.dict_edit.text().split(",") if x.strip()]))
        f.addRow(tr("Dictionary:"), self.dict_edit)
        f.addRow("", self._bind_check(QCheckBox(tr("Fall back to offline rules if the AI request fails")),
                                      "cleanup_fallback_rules"))
        f.addRow(tr("Timeout:"), self._bind_spin(QSpinBox(), "cleanup_timeout", 5, 180, " s"))
        lay.addWidget(g)
        lay.addStretch(1)
        self._update_provider_ui()
        return w

    def _provider(self):
        return PROVIDERS_BY_ID[self.provider_combo.currentData()]

    def _on_provider(self, _i) -> None:
        self.config.set("cleanup_provider", self.provider_combo.currentData())
        self.test_result.clear()
        self._update_provider_ui()

    def _update_provider_ui(self) -> None:
        p = self._provider()
        is_rules = p.kind == "rules"
        has_url = p.id in ("ollama", "lmstudio", "custom")
        show_key = p.needs_key or p.id == "custom"
        for wdg in (self.key_label, self.key_edit, self.key_show):
            wdg.setVisible(show_key)
        self.key_link.setVisible(bool(p.key_url))
        self.url_label.setVisible(has_url)
        self.url_edit.setVisible(has_url)
        for wdg in (self.model_label, self.model_combo, self.btn_models):
            wdg.setVisible(not is_rules)
        if show_key:
            self.key_edit.setText(get_api_key(p.id))
            self.key_edit.setPlaceholderText(tr("Optional API key") if not p.needs_key else tr("Paste your API key"))
        if has_url:
            self.url_edit.setText(self.config.get(f"{p.id}_base_url"))
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(list(p.suggested))
        current = self.config.cleanup_model(p.id)
        if current and self.model_combo.findText(current) < 0:
            self.model_combo.insertItem(0, current)
        self.model_combo.setCurrentText(current)
        self.model_combo.blockSignals(False)
        hints = {
            "gemini": tr("Free API keys are available in Google AI Studio. Recommended: gemini-2.5-flash or gemini-2.5-flash-lite."),
            "ollama": tr("Runs fully local. Install Ollama, then e.g. <code>ollama pull llama3.2</code>."),
            "lmstudio": tr("Start the local server in LM Studio (Developer tab) and load a model."),
            "custom": tr("Any OpenAI-compatible endpoint (vLLM, LocalAI, llama.cpp server, …)."),
            "rules": tr("Removes filler words and repetitions without any AI. Works offline, no translation."),
        }
        self.key_hint.setText(hints.get(p.id, tr("Your key is stored in the system keychain.")))

    def _save_key(self) -> None:
        p = self._provider()
        where = set_api_key(p.id, self.key_edit.text())
        if where == "unavailable":
            if self.key_edit.text().strip():
                self.set_status(tr("System keyring unavailable. API key was not saved."))
        elif self.key_edit.text().strip():
            self.set_status(tr("Your key is stored in the system keychain."))

    def _save_url(self) -> None:
        p = self._provider()
        if p.id in ("ollama", "lmstudio", "custom"):
            self.config.set(f"{p.id}_base_url", self.url_edit.text().strip())

    def _on_cleanup_model(self, text: str) -> None:
        self.config.set_cleanup_model(self._provider().id, text.strip())

    def _open_key_url(self) -> None:
        url = self._provider().key_url
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _load_models(self) -> None:
        p = self._provider()
        self._save_key()
        self._save_url()
        self.btn_models.setEnabled(False)
        self.btn_models.setText(tr("Loading…"))

        def done(models):
            self.btn_models.setEnabled(True)
            self.btn_models.setText(tr("Load models"))
            if self._provider().id != p.id:
                return
            current = self.model_combo.currentText()
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            self.model_combo.addItems(models or list(p.suggested))
            self.model_combo.setCurrentText(current)
            self.model_combo.blockSignals(False)
            self.test_result.setText(tr("Found models:") + f" {len(models)}")

        def fail(msg):
            self.btn_models.setEnabled(True)
            self.btn_models.setText(tr("Load models"))
            self.test_result.setText("❌ " + self._err(msg))

        run_task(self.cleaner.list_models, p.id, on_done=done, on_error=fail)

    def _err(self, msg: str) -> str:
        if msg.startswith("NO_KEY:"):
            return tr("Please enter an API key first.")
        return msg

    def _test_cleanup(self) -> None:
        self._save_key()
        self._save_url()
        self.btn_test.setEnabled(False)
        self.test_result.setText(tr("Testing…"))

        def done(text):
            self.btn_test.setEnabled(True)
            self.test_result.setText("✅ " + text)

        def fail(msg):
            self.btn_test.setEnabled(True)
            self.test_result.setText("❌ " + self._err(msg))

        run_task(self.cleaner.test, self._provider().id, on_done=done, on_error=fail)

    # ======================================================================
    # Output
    def _build_output(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        g = QGroupBox(tr("Text insertion"))
        f = QFormLayout(g)
        f.addRow("", _hint(tr("Voicewright copies finished dictations to the clipboard.")))
        f.addRow("", self._bind_check(QCheckBox(tr("Add a space after copied text")), "add_trailing_space"))
        lay.addWidget(g)
        lay.addStretch(1)
        return w

    # ======================================================================
    # History
    def _build_history(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self._bind_check(QCheckBox(tr("Save history locally")), "history_enabled"))
        self.history_list = QListWidget()
        self.history_list.setWordWrap(True)
        self.history_list.itemDoubleClicked.connect(self._copy_history_item)
        lay.addWidget(self.history_list, 1)
        row = QHBoxLayout()
        copy = QPushButton(tr("Copy"))
        copy.clicked.connect(lambda: self._copy_history_item(self.history_list.currentItem()))
        copy_raw = QPushButton(tr("Copy raw transcript"))
        copy_raw.clicked.connect(lambda: self._copy_history_item(self.history_list.currentItem(), raw=True))
        clear = QPushButton(tr("Clear history"))
        clear.clicked.connect(self._clear_history)
        for b in (copy, copy_raw, clear):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.refresh_history()
        return w

    def refresh_history(self) -> None:
        self.history_list.clear()
        for it in self.history.items:
            ts = datetime.datetime.fromtimestamp(it["ts"]).strftime("%Y-%m-%d %H:%M")
            item = QListWidgetItem(f"{ts} · {it.get('language', '')} · {it.get('duration', 0)} s\n{it['text']}")
            item.setData(Qt.UserRole, it)
            self.history_list.addItem(item)

    def _copy_history_item(self, item, raw: bool = False) -> None:
        if item is None:
            return
        data = item.data(Qt.UserRole)
        QGuiApplication.clipboard().setText(data["raw"] if raw else data["text"])
        self.set_status(tr("Copied to clipboard."))

    def _clear_history(self) -> None:
        if QMessageBox.question(self, APP_NAME, tr("Delete the entire history?")) == QMessageBox.Yes:
            self.history.clear()
            self.refresh_history()

    # ======================================================================
    # About
    def _build_about(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        title = QLabel(f"<h2>{APP_NAME} {__version__}</h2>")
        lay.addWidget(title)
        lay.addWidget(_hint(tr("Local-first voice dictation. Speech recognition runs offline with "
                               "faster-whisper; cleanup uses your own API key or a local model.")))
        info = QPlainTextEdit()
        info.setReadOnly(True)
        info.setPlainText("\n".join([
            f"Version: {__version__}",
            f"Python: {sys.version.split()[0]}",
            f"OS: {platform.platform()}",
            f"Session: {session_type() or '-'}",
            f"CUDA: {cuda_available()}",
            f"Config: {config_dir()}",
            f"Data: {data_dir()}",
            f"Models: {models_dir()}",
            f"Logs: {logs_dir()}",
        ]))
        lay.addWidget(info, 1)
        row = QHBoxLayout()
        for label, path in ((tr("Open models folder"), models_dir()), (tr("Open logs folder"), logs_dir()),
                            (tr("Open config folder"), config_dir())):
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, p=path: QDesktopServices.openUrl(QUrl.fromLocalFile(str(p))))
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addWidget(_hint(tr("Shortcut:") + " " + format_hotkey(self.config.get("hotkey"))
                            + " · CLI: <code>voicewright --toggle | --start | --stop | --cancel</code>"))
        return w
