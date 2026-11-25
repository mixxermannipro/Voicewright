"""Voicewright 2.0 settings window with sidebar navigation and liquid-glass cards."""
from __future__ import annotations

import datetime
import logging
import platform
import sys

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QFormLayout, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from voicewright import APP_NAME, __version__, autostart
from voicewright.audio import list_input_devices
from voicewright.cleanup import LANGUAGE_NAMES, PROVIDERS, PROVIDERS_BY_ID, Cleaner
from voicewright.config import Config
from voicewright.engines import cuda_available, sherpa_available
from voicewright.history import History
from voicewright.hotkey import format_hotkey
from voicewright.i18n import tr
from voicewright.keystore import get_api_key, set_api_key
from voicewright.models import (
    CATALOG, CATALOG_BY_ID, CLEANUP_CATALOG, CLEANUP_BY_ID, LLAMA_VERSION,
    delete_model, download_model, download_runtime, is_downloaded,
    recommended_model, runtime_asset, runtime_installed,
)
from voicewright.paths import IS_LINUX, config_dir, data_dir, logs_dir, models_dir, session_type
from voicewright.runtime import find_server_binary
from voicewright.stats import Stats
from voicewright.ui import theme, widgets
from voicewright.ui.hotkey_edit import HotkeyEdit
from voicewright.ui.tasks import run_task

log = logging.getLogger(__name__)

WHISPER_LANGS = [
    "auto", "de", "en", "fr", "es", "it", "pt", "nl", "pl", "tr", "ru", "uk",
    "cs", "sv", "da", "no", "fi", "el", "hu", "ro", "ar", "he", "hi", "ja",
    "ko", "zh", "vi", "id", "th",
]


def _lang_label(code: str) -> str:
    if code == "auto":
        return tr("Automatic detection")
    return f"{tr(LANGUAGE_NAMES.get(code, code))} ({code})"


def _scroll_page(content: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setWidget(content)
    return area


def _page_shell(heading: str, sub: str) -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    lay = QVBoxLayout(page)
    lay.setContentsMargins(28, 24, 28, 24)
    lay.setSpacing(16)
    lay.addWidget(widgets.title(heading))
    if sub:
        lay.addWidget(widgets.subtitle(sub))
    return page, lay


class SettingsWindow(QWidget):
    hotkeyConfigChanged = Signal()
    captureActive = Signal(bool)
    modelChanged = Signal()
    cleanupChanged = Signal()
    outputChanged = Signal()
    waylandPermissionRequested = Signal()

    def __init__(self, config: Config, history: History, stats: Stats, icon: QIcon) -> None:
        super().__init__()
        self.config = config
        self.history = history
        self.stats = stats
        self.cleaner = Cleaner(config)
        self._download_task = None
        self._cleanup_dl_task = None
        self._runtime_dl_task = None

        self.setObjectName("Root")
        self.setWindowTitle(f"{APP_NAME} – {tr('Settings')}")
        self.setWindowIcon(icon)
        self.resize(1040, 720)
        self.setMinimumSize(860, 600)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --- Left sidebar -------------------------------------------------
        sidebar = QFrame(self)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        s_lay = QVBoxLayout(sidebar)
        s_lay.setContentsMargins(16, 20, 16, 16)
        s_lay.setSpacing(14)

        brand = QLabel(APP_NAME)
        brand.setObjectName("Brand")
        brand_sub = QLabel(f"v{__version__}")
        brand_sub.setObjectName("BrandSub")
        s_lay.addWidget(brand)
        s_lay.addWidget(brand_sub)

        nav_items = [
            ("🎙", tr("Overview")),
            ("🧠", tr("Models")),
            ("✨", tr("Cleanup")),
            ("⚡", tr("Smart")),
            ("⌨", tr("Output")),
            ("🕘", tr("History")),
            ("ℹ", tr("About")),
        ]
        self.nav = widgets.NavList(nav_items, sidebar)
        s_lay.addWidget(self.nav, 1)

        self.sidebar_status = widgets.faint("")
        s_lay.addWidget(self.sidebar_status)
        outer.addWidget(sidebar)

        # --- Right content area -------------------------------------------
        right = QWidget(self)
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(0)

        self.status_banner = QLabel()
        self.status_banner.setWordWrap(True)
        self.status_banner.setVisible(False)
        self.status_banner.setContentsMargins(24, 10, 24, 10)
        r_lay.addWidget(self.status_banner)

        self.stack = QStackedWidget()
        r_lay.addWidget(self.stack, 1)

        self.stack.addWidget(_scroll_page(self._build_overview()))
        self.stack.addWidget(_scroll_page(self._build_models()))
        self.stack.addWidget(_scroll_page(self._build_cleanup()))
        self.stack.addWidget(_scroll_page(self._build_smart()))
        self.stack.addWidget(_scroll_page(self._build_output()))
        self.stack.addWidget(_scroll_page(self._build_history()))
        self.stack.addWidget(_scroll_page(self._build_about()))

        self.nav.selected.connect(self.stack.setCurrentIndex)
        outer.addWidget(right, 1)

        self.refresh_overview()
        self.refresh_stats()
        self.refresh_history()
        self.refresh_output("")

    # ======================================================================
    # Public API used by Controller
    # ======================================================================
    def select_page(self, index: int) -> None:
        self.nav.set_current(index)
        self.stack.setCurrentIndex(max(0, min(index, self.stack.count() - 1)))

    def set_status(self, text: str, error: bool = False) -> None:
        pal = theme.active()
        self.status_banner.setText(text)
        self.status_banner.setVisible(bool(text))
        if error:
            self.status_banner.setStyleSheet(
                f"background: {pal.card_alt}; color: {pal.danger};"
                f" border-bottom: 1px solid {pal.danger}; padding: 10px 24px; font-weight: 600;"
            )
        else:
            self.status_banner.setStyleSheet(
                f"background: {pal.accent_soft}; color: {pal.text};"
                f" border-bottom: 1px solid {pal.border}; padding: 10px 24px;"
            )
        self.sidebar_status.setText(text if not error else tr("Attention needed"))

    def sync_mode(self, mode: str) -> None:
        self.mode_seg.blockSignals(True)
        self.mode_seg.set_value(mode, emit=False)
        self.mode_seg.blockSignals(False)

    # ======================================================================
    # Binding helpers
    # ======================================================================
    def _bind_check(self, cb: QCheckBox, key: str, after=None) -> QCheckBox:
        cb.setChecked(bool(self.config.get(key)))
        cb.toggled.connect(lambda v: (self.config.set(key, bool(v)), after and after()))
        return cb

    def _bind_combo(self, combo: QComboBox, key: str, items: list[tuple[str, str]],
                    after=None) -> QComboBox:
        for value, label in items:
            combo.addItem(label, value)
        idx = combo.findData(self.config.get(key))
        combo.setCurrentIndex(max(0, idx))
        combo.currentIndexChanged.connect(
            lambda _i: (self.config.set(key, combo.currentData()), after and after())
        )
        return combo

    def _bind_spin(self, spin: QSpinBox, key: str, lo: int, hi: int, suffix: str = "",
                   after=None) -> QSpinBox:
        spin.setRange(lo, hi)
        spin.setValue(int(self.config.get(key, lo)))
        if suffix:
            spin.setSuffix(suffix)
        spin.valueChanged.connect(lambda v: (self.config.set(key, int(v)), after and after()))
        return spin

    # ======================================================================
    # Page 0: Overview
    # ======================================================================
    def _build_overview(self) -> QWidget:
        page, lay = _page_shell(
            tr("Dictation"),
            tr("Speak naturally. Tap the shortcut to toggle, or hold while speaking."),
        )

        # Hero card
        hero = widgets.Hero()
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        self.dictation_button = QPushButton(tr("Start dictation"))
        self.dictation_button.setObjectName("Primary")
        self.dictation_button.setCursor(Qt.PointingHandCursor)
        top_row.addWidget(self.dictation_button)
        top_row.addStretch(1)
        self.badge_model = widgets.Badge("", accent=True)
        self.badge_hotkey = widgets.Badge("", accent=False)
        top_row.addWidget(self.badge_model)
        top_row.addWidget(self.badge_hotkey)
        hero.body.addLayout(top_row)

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(28)
        self.metric_sessions = widgets.Metric("0", tr("Dictations"))
        self.metric_words = widgets.Metric("0", tr("Words"))
        self.metric_saved = widgets.Metric("0 min", tr("Time saved"))
        metrics_row.addWidget(self.metric_sessions)
        metrics_row.addWidget(self.metric_words)
        metrics_row.addWidget(self.metric_saved)
        metrics_row.addStretch(1)
        hero.body.addLayout(metrics_row)
        lay.addWidget(hero)

        # Shortcut card
        sc_card = widgets.Card()
        sc_card.add_title(tr("Shortcut"), tr("One shortcut for tapping and holding."))
        form = QFormLayout()
        form.setSpacing(10)

        self.hotkey_edit = HotkeyEdit(self.config.get("hotkey"))
        self.hotkey_edit.hotkeyChanged.connect(self._on_hotkey)
        self.hotkey_edit.error.connect(lambda m: QMessageBox.warning(self, APP_NAME, m))
        self.hotkey_edit.capturingChanged.connect(self.captureActive.emit)
        form.addRow(tr("Dictation shortcut:"), self.hotkey_edit)

        self.mode_seg = widgets.Segmented(
            [
                ("hybrid", tr("Hybrid")),
                ("toggle", tr("Toggle")),
                ("hold", tr("Hold")),
            ],
            current=self.config.get("hotkey_mode", "hybrid"),
        )
        self.mode_seg.changed.connect(self._on_mode_changed)
        form.addRow(tr("Mode:"), self.mode_seg)

        form.addRow(
            tr("Tap threshold:"),
            self._bind_spin(
                QSpinBox(), "tap_threshold_ms", 150, 900, " ms",
                after=self.hotkeyConfigChanged.emit,
            ),
        )
        form.addRow("", self._bind_check(QCheckBox(tr("Esc cancels a running recording")), "cancel_with_escape"))

        backends = [
            ("auto", tr("Automatic")),
            ("pynput", "pynput (Windows / macOS / X11)"),
            ("none", tr("None – use CLI/desktop shortcut")),
        ]
        form.addRow(
            tr("Hotkey backend:"),
            self._bind_combo(QComboBox(), "hotkey_backend", backends, self.hotkeyConfigChanged.emit),
        )
        if IS_LINUX and session_type() == "wayland":
            form.addRow(
                tr("Wayland shortcut:"),
                self._bind_combo(
                    QComboBox(),
                    "wayland_hotkey",
                    [
                        ("portal", tr("Desktop portal (recommended)")),
                        ("desktop", tr("System shortcut (voicewright --toggle)")),
                    ],
                    self.hotkeyConfigChanged.emit,
                ),
            )
        sc_card.body.addLayout(form)
        lay.addWidget(sc_card)

        # Microphone & Application card
        app_card = widgets.Card()
        app_card.add_title(tr("Microphone & Application"))
        af = QFormLayout()
        af.setSpacing(10)

        self.mic_combo = QComboBox()
        self._fill_mics()
        self.mic_combo.currentIndexChanged.connect(
            lambda _i: self.config.set("input_device", self.mic_combo.currentData())
        )
        mic_row = QHBoxLayout()
        mic_row.addWidget(self.mic_combo, 1)
        refresh_btn = QPushButton(tr("Refresh"))
        refresh_btn.clicked.connect(self._fill_mics)
        mic_row.addWidget(refresh_btn)
        af.addRow(tr("Input device:"), mic_row)

        af.addRow(
            tr("Max. recording length:"),
            self._bind_spin(QSpinBox(), "max_recording_seconds", 10, 3600, " s"),
        )
        af.addRow("", self._bind_check(QCheckBox(tr("Play start/stop sounds")), "sounds_enabled"))
        af.addRow("", self._bind_check(QCheckBox(tr("Trim leading and trailing silence")), "silence_trim"))
        af.addRow("", self._bind_check(QCheckBox(tr("Start minimized to tray")), "start_minimized"))

        self.autostart_cb = QCheckBox(tr("Launch at login"))
        self.autostart_cb.setChecked(autostart.is_enabled())
        self.autostart_cb.toggled.connect(self._on_autostart)
        af.addRow("", self.autostart_cb)

        af.addRow(
            tr("Appearance:"),
            self._bind_combo(
                QComboBox(),
                "theme",
                [("system", tr("System")), ("light", tr("Light")), ("dark", tr("Dark"))],
                after=self._apply_theme,
            ),
        )
        af.addRow(
            "",
            self._bind_check(
                QCheckBox(tr("Reduce motion")),
                "reduce_motion",
                after=lambda: widgets.set_motion(not bool(self.config.get("reduce_motion", False))),
            ),
        )
        af.addRow(
            tr("Interface language:"),
            self._bind_combo(
                QComboBox(),
                "ui_language",
                [("auto", tr("System")), ("de", "Deutsch"), ("en", "English")],
                after=lambda: self.set_status(tr("Restart Voicewright to apply the language.")),
            ),
        )
        app_card.body.addLayout(af)
        lay.addWidget(app_card)
        lay.addStretch(1)
        return page

    def refresh_overview(self) -> None:
        mid = self.config.get("speech_model", "parakeet-v3")
        model = CATALOG_BY_ID.get(mid)
        m_label = model.name if model else mid
        self.badge_model.setText(m_label)
        self.badge_hotkey.setText(format_hotkey(self.config.get("hotkey")) or tr("Not set"))

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
        self.refresh_overview()
        self.hotkeyConfigChanged.emit()

    def _on_mode_changed(self, mode: str) -> None:
        self.config.set("hotkey_mode", mode)
        self.hotkeyConfigChanged.emit()

    def _on_autostart(self, v: bool) -> None:
        try:
            autostart.set_enabled(v)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))

    def _apply_theme(self) -> None:
        pal = theme.resolve(self.config.get("theme", "system"))
        theme.set_active(pal)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(theme.qss(pal))

    # ======================================================================
    # Page 1: Models
    # ======================================================================
    def _build_models(self) -> QWidget:
        page, lay = _page_shell(
            tr("Speech models"),
            tr("All speech recognition runs locally on your computer. Download a model and select it."),
        )

        has_cuda = cuda_available()
        has_sherpa = sherpa_available()
        rec = recommended_model(cuda=has_cuda, sherpa=has_sherpa)
        hw = tr("NVIDIA GPU detected (CUDA).") if has_cuda else tr("No CUDA GPU detected – CPU mode.")
        sh = tr("sherpa-onnx ready (Parakeet & SenseVoice).") if has_sherpa else tr(
            "sherpa-onnx not installed – Whisper models are available."
        )
        banner = widgets.Card("alt")
        banner.body.addWidget(widgets.muted(f"{hw} {sh} {tr('Recommended for you:')} <b>{rec}</b>"))
        lay.addWidget(banner)

        cat_card = widgets.Card()
        cat_card.add_title(tr("Model catalog"))
        self.model_table = QTableWidget(len(CATALOG), 7)
        self.model_table.setHorizontalHeaderLabels([
            tr("Model"), tr("Engine"), tr("Size"), tr("Languages"),
            tr("Speed"), tr("Accuracy"), tr("Status"),
        ])
        self.model_table.verticalHeader().setVisible(False)
        self.model_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.model_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.model_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.model_table.setMinimumHeight(260)
        self.model_table.itemSelectionChanged.connect(self._update_model_buttons)
        cat_card.body.addWidget(self.model_table)

        self.model_note = widgets.muted("")
        cat_card.body.addWidget(self.model_note)

        btn_row = QHBoxLayout()
        self.btn_download = QPushButton(tr("Download"))
        self.btn_download.setObjectName("Primary")
        self.btn_use = QPushButton(tr("Use this model"))
        self.btn_delete = QPushButton(tr("Delete"))
        self.btn_delete.setObjectName("Danger")
        self.btn_cancel_dl = QPushButton(tr("Cancel download"))
        self.btn_download.clicked.connect(self._download_selected)
        self.btn_use.clicked.connect(self._use_selected)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_cancel_dl.clicked.connect(self._cancel_download)
        self.btn_cancel_dl.setVisible(False)
        for b in (self.btn_download, self.btn_use, self.btn_delete, self.btn_cancel_dl):
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        cat_card.body.addLayout(btn_row)

        self.dl_progress = QProgressBar()
        self.dl_progress.setVisible(False)
        cat_card.body.addWidget(self.dl_progress)
        lay.addWidget(cat_card)

        # Recognition & Advanced v1 settings
        rec_card = widgets.Card()
        rec_card.add_title(tr("Recognition & Advanced"))
        rf = QFormLayout()
        rf.setSpacing(10)
        rf.addRow(
            tr("Spoken language:"),
            self._bind_combo(QComboBox(), "language", [(c, _lang_label(c)) for c in WHISPER_LANGS]),
        )
        rf.addRow(
            tr("Task:"),
            self._bind_combo(
                QComboBox(),
                "whisper_task",
                [
                    ("transcribe", tr("Transcribe (keep language)")),
                    ("translate", tr("Translate to English (offline, Whisper)")),
                ],
            ),
        )
        rf.addRow(
            tr("Device:"),
            self._bind_combo(
                QComboBox(),
                "whisper_device",
                [("auto", tr("Automatic")), ("cpu", "CPU"), ("cuda", "NVIDIA CUDA")],
                after=self.modelChanged.emit,
            ),
        )
        rf.addRow(
            tr("Precision:"),
            self._bind_combo(
                QComboBox(),
                "whisper_compute_type",
                [
                    ("auto", tr("Automatic")),
                    ("int8", "int8"),
                    ("int8_float16", "int8_float16"),
                    ("float16", "float16"),
                    ("float32", "float32"),
                ],
                after=self.modelChanged.emit,
            ),
        )
        rf.addRow(
            tr("Beam size:"),
            self._bind_spin(QSpinBox(), "beam_size", 1, 10),
        )
        prompt = QLineEdit(self.config.get("initial_prompt"))
        prompt.setPlaceholderText(tr("Optional: names, jargon, style hints for Whisper"))
        prompt.editingFinished.connect(lambda: self.config.set("initial_prompt", prompt.text()))
        rf.addRow(tr("Vocabulary prompt:"), prompt)
        rf.addRow("", self._bind_check(QCheckBox(tr("Skip silence (VAD filter)")), "vad_filter"))
        rf.addRow("", self._bind_check(QCheckBox(tr("Keep model in memory (faster)")), "keep_model_loaded"))
        rec_card.body.addLayout(rf)
        lay.addWidget(rec_card)
        lay.addStretch(1)

        self._refresh_models()
        return page

    def _selected_model(self) -> str | None:
        rows = self.model_table.selectionModel().selectedRows()
        return CATALOG[rows[0].row()].id if rows else None

    def _refresh_models(self) -> None:
        active = self.config.get("speech_model")
        rec = recommended_model(cuda=cuda_available(), sherpa=sherpa_available())
        for r, m in enumerate(CATALOG):
            name = m.name + ("  ★ " + tr("recommended") if m.id == rec else "")
            size = f"{m.size_mb} MB" if m.size_mb < 1000 else f"{m.size_mb / 1000:.1f} GB"
            langs = tr("Multilingual") if m.languages == "99" else m.languages
            status = tr("Not downloaded")
            if is_downloaded(m.id):
                status = tr("Active") if m.id == active else tr("Downloaded")
            vals = [
                name,
                m.engine,
                size,
                langs,
                "●" * m.speed + "○" * (5 - m.speed),
                "●" * m.accuracy + "○" * (5 - m.accuracy),
                status,
            ]
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
        self.refresh_overview()

    def _update_model_buttons(self) -> None:
        mid = self._selected_model()
        downloading = self._download_task is not None
        dl = bool(mid and is_downloaded(mid))
        self.btn_download.setEnabled(bool(mid) and not dl and not downloading)
        self.btn_use.setEnabled(dl and mid != self.config.get("speech_model"))
        self.btn_delete.setEnabled(dl and not downloading)
        if mid:
            m = CATALOG_BY_ID[mid]
            extra = f" · {m.seconds}" if m.seconds else ""
            self.model_note.setText(f"<b>{m.name}</b> ({m.license}{extra}): {tr(m.note)}")

    def _download_selected(self) -> None:
        mid = self._selected_model()
        if not mid:
            return
        self.dl_progress.setVisible(True)
        self.dl_progress.setRange(0, 0)
        self.btn_cancel_dl.setVisible(True)

        def on_progress(done, total, name):
            if total <= 1:
                self.dl_progress.setRange(0, 0)
                return
            self.dl_progress.setRange(0, 1000)
            self.dl_progress.setValue(int(1000 * done / max(1, total)))
            self.dl_progress.setFormat(f"{mid}: {done / 1e6:.0f} / {total / 1e6:.0f} MB ({name})")

        def on_done(_r):
            self._download_task = None
            self.dl_progress.setVisible(False)
            self.btn_cancel_dl.setVisible(False)
            if not is_downloaded(self.config.get("speech_model")):
                self.config.set("speech_model", mid)
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

        self._download_task = run_task(
            download_model, mid, with_progress=True,
            on_done=on_done, on_error=on_error, on_progress=on_progress,
        )
        self._update_model_buttons()

    def _cancel_download(self) -> None:
        if self._download_task is not None:
            self._download_task.cancel_event.set()

    def _use_selected(self) -> None:
        mid = self._selected_model()
        if mid and is_downloaded(mid):
            self.config.set("speech_model", mid)
            self.modelChanged.emit()
            self._refresh_models()

    def _delete_selected(self) -> None:
        mid = self._selected_model()
        if not mid:
            return
        if QMessageBox.question(self, APP_NAME, tr("Delete model?") + f" {mid}") != QMessageBox.Yes:
            return
        if mid == self.config.get("speech_model"):
            self.modelChanged.emit()
        delete_model(mid)
        self._refresh_models()

    # ======================================================================
    # Page 2: Cleanup
    # ======================================================================
    def _build_cleanup(self) -> QWidget:
        page, lay = _page_shell(
            tr("Text cleanup"),
            tr("Clean up fillers, punctuation and grammar locally with rules or Qwen3, or opt in to a cloud provider."),
        )

        top_card = widgets.Card()
        top_card.add_title(tr("General cleanup"))
        top_card.body.addWidget(self._bind_check(
            QCheckBox(tr("Enable cleanup")), "cleanup_enabled", after=self._on_cleanup_setting_changed,
        ))
        top_card.body.addWidget(self._bind_check(
            QCheckBox(tr("Enable protection check (numbers, URLs, dictionary, negations)")),
            "guard_enabled",
            after=self._on_cleanup_setting_changed,
        ))

        pf = QFormLayout()
        pf.setSpacing(10)
        self.provider_combo = QComboBox()
        for p in PROVIDERS:
            label = tr(p.name) if p.kind in ("rules", "local") or p.id == "custom" else p.name
            self.provider_combo.addItem(label, p.id)
        self.provider_combo.setCurrentIndex(
            max(0, self.provider_combo.findData(self.config.get("cleanup_provider", "rules")))
        )
        self.provider_combo.currentIndexChanged.connect(self._on_provider)
        pf.addRow(tr("Provider:"), self.provider_combo)
        top_card.body.addLayout(pf)
        lay.addWidget(top_card)

        # Local llama.cpp & GGUF card
        self.local_card = widgets.Card()
        self.local_card.add_title(
            tr("Local AI model (llama.cpp)"),
            tr("Runs privately on 127.0.0.1. Falls back to offline rules if unavailable."),
        )
        lf = QFormLayout()
        lf.setSpacing(10)

        rt_row = QHBoxLayout()
        self.runtime_status = widgets.muted("")
        self.btn_download_runtime = QPushButton(tr("Download llama.cpp") + f" ({LLAMA_VERSION})")
        self.btn_download_runtime.clicked.connect(self._download_llama_runtime)
        rt_row.addWidget(self.runtime_status, 1)
        rt_row.addWidget(self.btn_download_runtime)
        lf.addRow(tr("Runtime:"), rt_row)

        lf.addRow(
            tr("Local backend:"),
            self._bind_combo(
                QComboBox(),
                "llm_runtime",
                [
                    ("auto", tr("Automatic (bundled llama.cpp)")),
                    ("bundled", tr("Bundled llama.cpp")),
                    ("ollama", "Ollama"),
                    ("lmstudio", "LM Studio"),
                    ("off", tr("Off (rules only)")),
                ],
                after=self._on_cleanup_setting_changed,
            ),
        )
        lf.addRow(
            tr("CPU threads (0 = auto):"),
            self._bind_spin(QSpinBox(), "llm_threads", 0, 64, after=self._on_cleanup_setting_changed),
        )
        self.local_card.body.addLayout(lf)

        self.local_model_table = QTableWidget(len(CLEANUP_CATALOG), 5)
        self.local_model_table.setHorizontalHeaderLabels([
            tr("Model"), tr("Size"), tr("Speed"), tr("Accuracy"), tr("Status"),
        ])
        self.local_model_table.verticalHeader().setVisible(False)
        self.local_model_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.local_model_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.local_model_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.local_model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.local_model_table.setMinimumHeight(140)
        self.local_model_table.itemSelectionChanged.connect(self._update_local_model_buttons)
        self.local_card.body.addWidget(self.local_model_table)

        l_btn_row = QHBoxLayout()
        self.btn_local_dl = QPushButton(tr("Download"))
        self.btn_local_dl.setObjectName("Primary")
        self.btn_local_use = QPushButton(tr("Use this model"))
        self.btn_local_del = QPushButton(tr("Delete"))
        self.btn_local_del.setObjectName("Danger")
        self.btn_local_cancel = QPushButton(tr("Cancel download"))
        self.btn_local_dl.clicked.connect(self._download_local_model)
        self.btn_local_use.clicked.connect(self._use_local_model)
        self.btn_local_del.clicked.connect(self._delete_local_model)
        self.btn_local_cancel.clicked.connect(self._cancel_local_download)
        self.btn_local_cancel.setVisible(False)
        for b in (self.btn_local_dl, self.btn_local_use, self.btn_local_del, self.btn_local_cancel):
            l_btn_row.addWidget(b)
        l_btn_row.addStretch(1)
        self.local_card.body.addLayout(l_btn_row)

        self.local_dl_progress = QProgressBar()
        self.local_dl_progress.setVisible(False)
        self.local_card.body.addWidget(self.local_dl_progress)
        lay.addWidget(self.local_card)

        # Cloud / Server URL / Test card
        self.remote_card = widgets.Card()
        self.remote_card.add_title(tr("Connection & Model"))
        cf = QFormLayout()
        cf.setSpacing(10)

        key_row = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText(tr("Paste your API key"))
        self.key_edit.editingFinished.connect(self._save_key)
        self.key_show = QPushButton(tr("Show"))
        self.key_show.setCheckable(True)
        self.key_show.toggled.connect(
            lambda v: self.key_edit.setEchoMode(QLineEdit.Normal if v else QLineEdit.Password)
        )
        self.key_link = QPushButton(tr("Get key"))
        self.key_link.clicked.connect(self._open_key_url)
        key_row.addWidget(self.key_edit, 1)
        key_row.addWidget(self.key_show)
        key_row.addWidget(self.key_link)
        self.key_label = QLabel(tr("API key:"))
        cf.addRow(self.key_label, key_row)

        self.url_edit = QLineEdit()
        self.url_edit.editingFinished.connect(self._save_url)
        self.url_label = QLabel(tr("Server URL:"))
        cf.addRow(self.url_label, self.url_edit)

        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(260)
        self.model_combo.currentTextChanged.connect(self._on_cleanup_model)
        self.btn_models = QPushButton(tr("Load models"))
        self.btn_models.clicked.connect(self._load_models)
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.btn_models)
        self.model_label = QLabel(tr("Model:"))
        cf.addRow(self.model_label, model_row)

        test_row = QHBoxLayout()
        self.btn_test = QPushButton(tr("Test connection"))
        self.btn_test.clicked.connect(self._test_cleanup)
        self.test_result = widgets.muted("")
        test_row.addWidget(self.btn_test)
        test_row.addWidget(self.test_result, 1)
        cf.addRow("", test_row)

        self.key_hint = widgets.muted("")
        cf.addRow("", self.key_hint)
        self.remote_card.body.addLayout(cf)
        lay.addWidget(self.remote_card)

        # Style & translation card
        st_card = widgets.Card()
        st_card.add_title(tr("Style and translation"))
        sf = QFormLayout()
        sf.setSpacing(10)
        sf.addRow(
            tr("Style:"),
            self._bind_combo(
                QComboBox(),
                "cleanup_style",
                [
                    ("clean", tr("Clean – remove fillers, fix grammar (recommended)")),
                    ("minimal", tr("Minimal – punctuation only")),
                    ("formal", tr("Formal – professional writing")),
                    ("casual", tr("Casual – chat style")),
                    ("notes", tr("Notes – heading and bullet points")),
                    ("email", tr("E-mail – greeting, body and closing")),
                ],
                after=self._on_cleanup_setting_changed,
            ),
        )
        sf.addRow(
            tr("Output language:"),
            self._bind_combo(
                QComboBox(),
                "output_language",
                [("same", tr("Same as spoken (no translation)"))]
                + [(c, _lang_label(c)) for c in WHISPER_LANGS if c != "auto"],
                after=self._on_cleanup_setting_changed,
            ),
        )
        self.instr_edit = QPlainTextEdit(self.config.get("custom_instructions"))
        self.instr_edit.setPlaceholderText(tr("e.g. Use British spelling. Write numbers as digits."))
        self.instr_edit.setMaximumHeight(74)
        self.instr_edit.textChanged.connect(
            lambda: (self.config.set("custom_instructions", self.instr_edit.toPlainText()),
                     self._on_cleanup_setting_changed())
        )
        sf.addRow(tr("Custom instructions:"), self.instr_edit)

        self.dict_edit = QLineEdit(", ".join(self.config.get("custom_dictionary", [])))
        self.dict_edit.setPlaceholderText(tr("Comma separated: Voicewright, Kubernetes, Dr. Müller"))
        self.dict_edit.editingFinished.connect(
            lambda: (
                self.config.set(
                    "custom_dictionary",
                    [x.strip() for x in self.dict_edit.text().split(",") if x.strip()],
                ),
                self._on_cleanup_setting_changed(),
            )
        )
        sf.addRow(tr("Dictionary:"), self.dict_edit)
        sf.addRow("", self._bind_check(
            QCheckBox(tr("Fall back to offline rules if the AI request fails")),
            "cleanup_fallback_rules",
        ))
        sf.addRow(tr("Timeout:"), self._bind_spin(QSpinBox(), "cleanup_timeout", 5, 180, " s"))
        st_card.body.addLayout(sf)
        lay.addWidget(st_card)
        lay.addStretch(1)

        self._refresh_local_models()
        self._update_provider_ui()
        return page

    def _provider(self):
        return PROVIDERS_BY_ID[self.provider_combo.currentData()]

    def _on_cleanup_setting_changed(self) -> None:
        self.cleanupChanged.emit()

    def _on_provider(self, _i) -> None:
        self.config.set("cleanup_provider", self.provider_combo.currentData())
        self.test_result.clear()
        self._update_provider_ui()
        self.cleanupChanged.emit()

    def _update_provider_ui(self) -> None:
        p = self._provider()
        is_local = p.kind == "local"
        is_rules = p.kind == "rules"
        has_url = p.id in ("ollama", "lmstudio", "custom")
        show_key = p.needs_key or p.id == "custom"

        self.local_card.setVisible(is_local)
        self.remote_card.setVisible(not is_local)

        for wdg in (self.key_label, self.key_edit, self.key_show):
            wdg.setVisible(show_key)
        self.key_link.setVisible(bool(p.key_url))
        self.url_label.setVisible(has_url)
        self.url_edit.setVisible(has_url)
        for wdg in (self.model_label, self.model_combo, self.btn_models):
            wdg.setVisible(not is_rules and not is_local)

        if show_key:
            self.key_edit.setText(get_api_key(p.id))
            self.key_edit.setPlaceholderText(
                tr("Optional API key") if not p.needs_key else tr("Paste your API key")
            )
        if has_url:
            self.url_edit.setText(self.config.get(f"{p.id}_base_url", ""))
        if not is_local:
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
        self._refresh_runtime_status()

    def _refresh_runtime_status(self) -> None:
        exe = find_server_binary()
        if exe is not None:
            self.runtime_status.setText(f"{tr('Ready')}: {exe}")
            self.btn_download_runtime.setEnabled(False)
        elif runtime_installed():
            self.runtime_status.setText(tr("Installed"))
            self.btn_download_runtime.setEnabled(False)
        elif runtime_asset() is not None:
            self.runtime_status.setText(tr("Not downloaded"))
            self.btn_download_runtime.setEnabled(self._runtime_dl_task is None)
        else:
            self.runtime_status.setText(tr("No prebuilt binary for this platform – use Ollama or system llama-server."))
            self.btn_download_runtime.setEnabled(False)

    def _download_llama_runtime(self) -> None:
        self.local_dl_progress.setVisible(True)
        self.local_dl_progress.setRange(0, 0)
        self.btn_download_runtime.setEnabled(False)

        def on_progress(done, total, name):
            if total <= 1:
                self.local_dl_progress.setRange(0, 0)
                return
            self.local_dl_progress.setRange(0, 1000)
            self.local_dl_progress.setValue(int(1000 * done / max(1, total)))
            self.local_dl_progress.setFormat(f"llama.cpp: {done / 1e6:.0f} / {total / 1e6:.0f} MB ({name})")

        def on_done(_p):
            self._runtime_dl_task = None
            self.local_dl_progress.setVisible(False)
            self._refresh_runtime_status()
            self.set_status(tr("llama.cpp runtime downloaded."))

        def on_error(msg):
            self._runtime_dl_task = None
            self.local_dl_progress.setVisible(False)
            self._refresh_runtime_status()
            if msg != "DownloadCancelled":
                QMessageBox.warning(self, APP_NAME, tr("Download failed:") + f"\n{msg}")

        self._runtime_dl_task = run_task(
            download_runtime, with_progress=True,
            on_done=on_done, on_error=on_error, on_progress=on_progress,
        )

    def _selected_local_model(self) -> str | None:
        rows = self.local_model_table.selectionModel().selectedRows()
        return CLEANUP_CATALOG[rows[0].row()].id if rows else None

    def _refresh_local_models(self) -> None:
        active = self.config.get("local_model", "qwen3-0.6b-q4")
        for r, m in enumerate(CLEANUP_CATALOG):
            size = f"{m.size_mb} MB" if m.size_mb < 1000 else f"{m.size_mb / 1000:.1f} GB"
            status = tr("Not downloaded")
            if is_downloaded(m.id):
                status = tr("Active") if m.id == active else tr("Downloaded")
            vals = [
                m.name,
                size,
                "●" * m.speed + "○" * (5 - m.speed),
                "●" * m.accuracy + "○" * (5 - m.accuracy),
                status,
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if m.id == active and is_downloaded(m.id):
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.local_model_table.setItem(r, c, item)
        self.local_model_table.resizeColumnsToContents()
        self.local_model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._update_local_model_buttons()

    def _update_local_model_buttons(self) -> None:
        mid = self._selected_local_model()
        downloading = self._cleanup_dl_task is not None
        dl = bool(mid and is_downloaded(mid))
        self.btn_local_dl.setEnabled(bool(mid) and not dl and not downloading)
        self.btn_local_use.setEnabled(dl and mid != self.config.get("local_model"))
        self.btn_local_del.setEnabled(dl and not downloading)

    def _download_local_model(self) -> None:
        mid = self._selected_local_model()
        if not mid:
            return
        self.local_dl_progress.setVisible(True)
        self.local_dl_progress.setRange(0, 0)
        self.btn_local_cancel.setVisible(True)

        def on_progress(done, total, name):
            if total <= 1:
                self.local_dl_progress.setRange(0, 0)
                return
            self.local_dl_progress.setRange(0, 1000)
            self.local_dl_progress.setValue(int(1000 * done / max(1, total)))
            self.local_dl_progress.setFormat(f"{mid}: {done / 1e6:.0f} / {total / 1e6:.0f} MB ({name})")

        def on_done(_r):
            self._cleanup_dl_task = None
            self.local_dl_progress.setVisible(False)
            self.btn_local_cancel.setVisible(False)
            self.config.set("local_model", mid)
            self._refresh_local_models()
            self.cleanupChanged.emit()
            self.set_status(tr("Model downloaded:") + f" {mid}")

        def on_error(msg):
            self._cleanup_dl_task = None
            self.local_dl_progress.setVisible(False)
            self.btn_local_cancel.setVisible(False)
            self._refresh_local_models()
            if msg != "DownloadCancelled":
                QMessageBox.warning(self, APP_NAME, tr("Download failed:") + f"\n{msg}")

        self._cleanup_dl_task = run_task(
            download_model, mid, with_progress=True,
            on_done=on_done, on_error=on_error, on_progress=on_progress,
        )
        self._update_local_model_buttons()

    def _cancel_local_download(self) -> None:
        if self._cleanup_dl_task is not None:
            self._cleanup_dl_task.cancel_event.set()

    def _use_local_model(self) -> None:
        mid = self._selected_local_model()
        if mid and is_downloaded(mid):
            self.config.set("local_model", mid)
            self._refresh_local_models()
            self.cleanupChanged.emit()

    def _delete_local_model(self) -> None:
        mid = self._selected_local_model()
        if not mid:
            return
        if QMessageBox.question(self, APP_NAME, tr("Delete model?") + f" {mid}") != QMessageBox.Yes:
            return
        delete_model(mid)
        self._refresh_local_models()

    def _save_key(self) -> None:
        p = self._provider()
        where = set_api_key(p.id, self.key_edit.text())
        if where == "unavailable":
            if self.key_edit.text().strip():
                self.set_status(tr("System keyring unavailable. API key was not saved."), error=True)
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
    # Page 3: Smart features
    # ======================================================================
    def _build_smart(self) -> QWidget:
        page, lay = _page_shell(
            tr("Smart features"),
            tr("Spoken punctuation, voice commands, snippets and word replacements run locally in milliseconds."),
        )

        feat_card = widgets.Card()
        feat_card.add_title(tr("Formatting & Commands"))
        ff = QFormLayout()
        ff.setSpacing(10)
        ff.addRow("", self._bind_check(QCheckBox(tr("Enable smart formatting")), "smart_formatting"))
        ff.addRow("", self._bind_check(QCheckBox(tr("Spoken punctuation (comma, period, new paragraph)")), "spoken_punctuation"))
        ff.addRow("", self._bind_check(QCheckBox(tr("Natural language commands (shorter, formal, translate)")), "command_mode"))
        ff.addRow("", self._bind_check(QCheckBox(tr("Allow emojis when explicitly requested")), "emoji_enabled"))
        ff.addRow(
            tr("Structure mode:"),
            self._bind_combo(
                QComboBox(),
                "structure_mode",
                [
                    ("auto", tr("Automatic (detect list / e-mail / notes)")),
                    ("off", tr("Off")),
                    ("list", tr("Always bullet list")),
                    ("email", tr("Always e-mail")),
                    ("notes", tr("Always notes")),
                ],
            ),
        )
        self.transform_edit = HotkeyEdit(self.config.get("transform_hotkey", "ctrl+alt+space"))
        self.transform_edit.hotkeyChanged.connect(lambda hk: self.config.set("transform_hotkey", hk))
        self.transform_edit.error.connect(lambda m: QMessageBox.warning(self, APP_NAME, m))
        self.transform_edit.capturingChanged.connect(self.captureActive.emit)
        ff.addRow(tr("Rewrite selection shortcut:"), self.transform_edit)
        feat_card.body.addLayout(ff)
        lay.addWidget(feat_card)

        # Snippets editor
        snip_card = widgets.Card()
        snip_card.add_title(
            tr("Text snippets"),
            tr("Say 'snippet <name>' or 'Textbaustein <name>' while dictating."),
        )
        self.snippets_table = QTableWidget(0, 2)
        self.snippets_table.setHorizontalHeaderLabels([tr("Name"), tr("Text")])
        self.snippets_table.verticalHeader().setVisible(False)
        self.snippets_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.snippets_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.snippets_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.snippets_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.snippets_table.setMinimumHeight(120)
        snip_card.body.addWidget(self.snippets_table)

        snip_form = QHBoxLayout()
        self.snip_name = QLineEdit()
        self.snip_name.setPlaceholderText(tr("Snippet name"))
        self.snip_text = QLineEdit()
        self.snip_text.setPlaceholderText(tr("Expanded text"))
        btn_add_snip = QPushButton(tr("Add"))
        btn_del_snip = QPushButton(tr("Remove"))
        btn_add_snip.clicked.connect(self._add_snippet)
        btn_del_snip.clicked.connect(self._remove_snippet)
        snip_form.addWidget(self.snip_name, 1)
        snip_form.addWidget(self.snip_text, 2)
        snip_form.addWidget(btn_add_snip)
        snip_form.addWidget(btn_del_snip)
        snip_card.body.addLayout(snip_form)
        lay.addWidget(snip_card)

        # Word replacements editor
        rep_card = widgets.Card()
        rep_card.add_title(
            tr("Word replacements"),
            tr("Automatically replace common mishearings."),
        )
        self.rep_table = QTableWidget(0, 2)
        self.rep_table.setHorizontalHeaderLabels([tr("Heard"), tr("Written")])
        self.rep_table.verticalHeader().setVisible(False)
        self.rep_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rep_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.rep_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rep_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.rep_table.setMinimumHeight(120)
        rep_card.body.addWidget(self.rep_table)

        rep_form = QHBoxLayout()
        self.rep_heard = QLineEdit()
        self.rep_heard.setPlaceholderText(tr("Heard phrase"))
        self.rep_written = QLineEdit()
        self.rep_written.setPlaceholderText(tr("Written replacement"))
        btn_add_rep = QPushButton(tr("Add"))
        btn_del_rep = QPushButton(tr("Remove"))
        btn_add_rep.clicked.connect(self._add_replacement)
        btn_del_rep.clicked.connect(self._remove_replacement)
        rep_form.addWidget(self.rep_heard, 1)
        rep_form.addWidget(self.rep_written, 2)
        rep_form.addWidget(btn_add_rep)
        rep_form.addWidget(btn_del_rep)
        rep_card.body.addLayout(rep_form)
        lay.addWidget(rep_card)
        lay.addStretch(1)

        self._refresh_snippets()
        self._refresh_replacements()
        return page

    def _refresh_snippets(self) -> None:
        snips = self.config.get("snippets", [])
        self.snippets_table.setRowCount(len(snips))
        for r, s in enumerate(snips):
            self.snippets_table.setItem(r, 0, QTableWidgetItem(str(s.get("name", ""))))
            self.snippets_table.setItem(r, 1, QTableWidgetItem(str(s.get("text", ""))))

    def _add_snippet(self) -> None:
        name = self.snip_name.text().strip()
        text = self.snip_text.text().strip()
        if not name or not text:
            return
        snips = [s for s in self.config.get("snippets", []) if s.get("name", "").lower() != name.lower()]
        snips.append({"name": name, "text": text})
        self.config.set("snippets", snips)
        self.snip_name.clear()
        self.snip_text.clear()
        self._refresh_snippets()

    def _remove_snippet(self) -> None:
        rows = self.snippets_table.selectionModel().selectedRows()
        if not rows:
            return
        snips = list(self.config.get("snippets", []))
        idx = rows[0].row()
        if 0 <= idx < len(snips):
            snips.pop(idx)
            self.config.set("snippets", snips)
            self._refresh_snippets()

    def _refresh_replacements(self) -> None:
        reps = list(self.config.get("replacements", {}).items())
        self.rep_table.setRowCount(len(reps))
        for r, (heard, written) in enumerate(reps):
            self.rep_table.setItem(r, 0, QTableWidgetItem(str(heard)))
            self.rep_table.setItem(r, 1, QTableWidgetItem(str(written)))

    def _add_replacement(self) -> None:
        heard = self.rep_heard.text().strip()
        written = self.rep_written.text().strip()
        if not heard or not written:
            return
        reps = dict(self.config.get("replacements", {}))
        reps[heard] = written
        self.config.set("replacements", reps)
        self.rep_heard.clear()
        self.rep_written.clear()
        self._refresh_replacements()

    def _remove_replacement(self) -> None:
        rows = self.rep_table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        reps = dict(self.config.get("replacements", {}))
        keys = list(reps.keys())
        if 0 <= idx < len(keys):
            reps.pop(keys[idx], None)
            self.config.set("replacements", reps)
            self._refresh_replacements()

    # ======================================================================
    # Page 4: Output
    # ======================================================================
    def _build_output(self) -> QWidget:
        page, lay = _page_shell(
            tr("Output & Insertion"),
            tr("Voicewright pastes or types finished dictations into the active window and always keeps the clipboard as a safety net."),
        )

        out_card = widgets.Card()
        out_card.add_title(tr("Text insertion"))
        of = QFormLayout()
        of.setSpacing(10)

        self.output_method_label = widgets.muted("")
        of.addRow(tr("Active method:"), self.output_method_label)
        of.addRow(
            tr("Method:"),
            self._bind_combo(
                QComboBox(),
                "insert_mode",
                [
                    ("auto", tr("Automatic (paste, else clipboard)")),
                    ("paste", tr("Paste via clipboard (fast, recommended)")),
                    ("type", tr("Simulate typing (slower, no clipboard)")),
                    ("clipboard", tr("Copy to clipboard only")),
                ],
                after=self.outputChanged.emit,
            ),
        )
        of.addRow(
            tr("Paste shortcut:"),
            self._bind_combo(
                QComboBox(),
                "paste_shortcut",
                [
                    ("auto", tr("Automatic (Ctrl+V / ⌘V)")),
                    ("ctrl_v", "Ctrl+V"),
                    ("ctrl_shift_v", tr("Ctrl+Shift+V (terminals)")),
                ],
                after=self.outputChanged.emit,
            ),
        )
        of.addRow("", self._bind_check(QCheckBox(tr("Restore previous clipboard content")), "restore_clipboard"))
        of.addRow(tr("Clipboard restore delay:"), self._bind_spin(QSpinBox(), "clipboard_restore_ms", 100, 3000, " ms"))
        of.addRow("", self._bind_check(QCheckBox(tr("Add a space after inserted text")), "add_trailing_space"))
        out_card.body.addLayout(of)
        lay.addWidget(out_card)

        ov_card = widgets.Card()
        ov_card.add_title(tr("Recording indicator"))
        ovf = QFormLayout()
        ovf.setSpacing(10)
        ovf.addRow("", self._bind_check(QCheckBox(tr("Show recording indicator")), "show_overlay"))
        ovf.addRow(
            tr("Indicator position:"),
            self._bind_combo(
                QComboBox(),
                "overlay_position",
                [("bottom", tr("Bottom")), ("top", tr("Top"))],
            ),
        )
        ov_card.body.addLayout(ovf)
        lay.addWidget(ov_card)

        wl_card = widgets.Card()
        wl_card.add_title(tr("Wayland"))
        wf = QFormLayout()
        wf.setSpacing(10)
        wf.addRow(
            tr("Wayland insertion:"),
            self._bind_combo(
                QComboBox(),
                "wayland_inject",
                [
                    ("portal", tr("Desktop portal (recommended)")),
                    ("wtype", "wtype (wlroots)"),
                    ("ydotool", "ydotool (opt-in)"),
                    ("clipboard", tr("Copy to clipboard only")),
                ],
                after=self.outputChanged.emit,
            ),
        )
        perm_row = QHBoxLayout()
        self.btn_wayland_perm = QPushButton(tr("Grant keyboard control"))
        self.btn_wayland_perm.clicked.connect(self.waylandPermissionRequested.emit)
        self.wayland_consent_badge = widgets.Badge("", accent=False)
        perm_row.addWidget(self.btn_wayland_perm)
        perm_row.addWidget(self.wayland_consent_badge)
        perm_row.addStretch(1)
        wf.addRow(tr("Portal permission:"), perm_row)

        wf.addRow(
            "",
            self._bind_check(
                QCheckBox(tr("Allow ydotool fallback (requires ydotoold / uinput)")),
                "ydotool_enabled",
                after=self.outputChanged.emit,
            ),
        )
        wl_card.body.addLayout(wf)
        lay.addWidget(wl_card)
        lay.addStretch(1)
        return page

    def refresh_output(self, method: str = "") -> None:
        if method:
            self.output_method_label.setText(method)
        consented = bool(self.config.get("wayland_consent", False))
        self.wayland_consent_badge.setText(tr("Granted") if consented else tr("Not granted"))
        self.wayland_consent_badge.set_accent(consented)

    # ======================================================================
    # Page 5: History & Stats
    # ======================================================================
    def _build_history(self) -> QWidget:
        page, lay = _page_shell(
            tr("History & Statistics"),
            tr("All history and statistics stay locally on your device. History is off by default."),
        )

        stats_card = widgets.Card()
        stats_card.add_title(tr("Local statistics"))
        self.stats_summary_label = widgets.muted("")
        stats_card.body.addWidget(self.stats_summary_label)
        s_row = QHBoxLayout()
        s_row.addWidget(self._bind_check(QCheckBox(tr("Record local statistics (no text)")), "stats_enabled"))
        s_row.addStretch(1)
        btn_reset_stats = QPushButton(tr("Reset statistics"))
        btn_reset_stats.setObjectName("Danger")
        btn_reset_stats.clicked.connect(self._reset_stats)
        s_row.addWidget(btn_reset_stats)
        stats_card.body.addLayout(s_row)
        lay.addWidget(stats_card)

        hist_card = widgets.Card()
        hist_card.add_title(tr("Dictation history"))
        hf = QFormLayout()
        hf.setSpacing(10)
        hf.addRow("", self._bind_check(QCheckBox(tr("Save history locally")), "history_enabled"))
        hf.addRow(tr("History limit:"), self._bind_spin(QSpinBox(), "history_limit", 0, 2000))
        hist_card.body.addLayout(hf)

        self.history_list = QListWidget()
        self.history_list.setWordWrap(True)
        self.history_list.setMinimumHeight(240)
        self.history_list.itemDoubleClicked.connect(self._copy_history_item)
        hist_card.body.addWidget(self.history_list)

        h_row = QHBoxLayout()
        copy_btn = QPushButton(tr("Copy"))
        copy_btn.clicked.connect(lambda: self._copy_history_item(self.history_list.currentItem()))
        copy_raw = QPushButton(tr("Copy raw transcript"))
        copy_raw.clicked.connect(lambda: self._copy_history_item(self.history_list.currentItem(), raw=True))
        clear_btn = QPushButton(tr("Clear history"))
        clear_btn.setObjectName("Danger")
        clear_btn.clicked.connect(self._clear_history)
        for b in (copy_btn, copy_raw, clear_btn):
            h_row.addWidget(b)
        h_row.addStretch(1)
        hist_card.body.addLayout(h_row)
        lay.addWidget(hist_card)
        lay.addStretch(1)
        return page

    def refresh_stats(self) -> None:
        self.metric_sessions.set_value(str(self.stats.sessions))
        self.metric_words.set_value(str(self.stats.words))
        saved_min = int(self.stats.seconds_saved() // 60)
        self.metric_saved.set_value(f"{saved_min} min")
        self.stats_summary_label.setText(self.stats.summary())

    def _reset_stats(self) -> None:
        if QMessageBox.question(self, APP_NAME, tr("Reset all local statistics?")) == QMessageBox.Yes:
            self.stats.reset()
            self.refresh_stats()

    def refresh_history(self) -> None:
        self.history_list.clear()
        for it in self.history.items:
            ts = datetime.datetime.fromtimestamp(it["ts"]).strftime("%Y-%m-%d %H:%M")
            item = QListWidgetItem(
                f"{ts} · {it.get('language', '')} · {it.get('duration', 0)} s\n{it['text']}"
            )
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
    # Page 6: About
    # ======================================================================
    def _build_about(self) -> QWidget:
        page, lay = _page_shell(
            f"{APP_NAME} {__version__}",
            tr("Local-first voice dictation with Parakeet, Whisper, SenseVoice and optional local AI cleanup."),
        )

        diag_card = widgets.Card()
        diag_card.add_title(tr("Diagnostics & Paths"))
        info = QPlainTextEdit()
        info.setReadOnly(True)
        info.setMinimumHeight(210)
        exe = find_server_binary()
        info.setPlainText("\n".join([
            f"Version: {__version__}",
            f"Python: {sys.version.split()[0]}",
            f"OS: {platform.platform()}",
            f"Session: {session_type() or '-'}",
            f"CUDA: {cuda_available()}",
            f"sherpa-onnx: {sherpa_available()}",
            f"llama.cpp: {exe or ('not installed')}",
            f"Config: {config_dir()}",
            f"Data: {data_dir()}",
            f"Models: {models_dir()}",
            f"Logs: {logs_dir()}",
        ]))
        diag_card.body.addWidget(info)

        row = QHBoxLayout()
        for label, path in (
            (tr("Open models folder"), models_dir()),
            (tr("Open logs folder"), logs_dir()),
            (tr("Open config folder"), config_dir()),
        ):
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, p=path: QDesktopServices.openUrl(QUrl.fromLocalFile(str(p))))
            row.addWidget(b)
        row.addStretch(1)
        diag_card.body.addLayout(row)
        diag_card.body.addWidget(widgets.muted(
            tr("Shortcut:") + " " + format_hotkey(self.config.get("hotkey"))
            + " · CLI: <code>voicewright --toggle | --start | --stop | --cancel | --transform</code>"
        ))
        lay.addWidget(diag_card)
        lay.addStretch(1)
        return page
