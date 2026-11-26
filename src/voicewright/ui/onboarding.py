"""Four-step setup assistant: welcome, model, microphone, shortcut/insertion.

The assistant never downloads anything without a click. Every step is
optional: a user can skip a step or close the window and reopen it later from
the settings or the tray menu.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

import numpy as np
from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from voicewright import APP_NAME, autostart
from voicewright.audio import SAMPLE_RATE, device_index, list_input_devices
from voicewright.config import Config
from voicewright.engines import cuda_available, sherpa_available
from voicewright.hotkey import combos_conflict, parse_hotkey
from voicewright.i18n import tr
from voicewright.models import (
    CATALOG, CATALOG_BY_ID, download_model, is_downloaded, recommended_model,
)
from voicewright.ui import theme, widgets
from voicewright.ui.hotkey_edit import HotkeyEdit
from voicewright.ui.tasks import run_task

log = logging.getLogger(__name__)

# RMS values above this are comfortably loud speech on a normal microphone.
_FULL_SCALE_RMS = 0.12


def level_fraction(rms: float) -> float:
    """Map microphone RMS (0..~0.3) to a 0..1 bar value."""
    try:
        value = float(rms) / _FULL_SCALE_RMS
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value))


class LevelMeter(QWidget):
    """A small live level bar that works in light and dark mode."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._level = 0.0
        self.setMinimumHeight(18)
        self.setAccessibleName(tr("Microphone level"))

    @property
    def value(self) -> float:
        return self._level

    def set_level(self, rms: float) -> None:
        self._level = level_fraction(rms)
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(260, 18)

    def paintEvent(self, event) -> None:  # noqa: ARG002
        pal = theme.active()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 2, 0, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, 7, 7)
        p.fillPath(path, QColor(pal.card_alt))
        p.setPen(QPen(QColor(pal.border), 1))
        p.drawPath(path)
        if self._level > 0:
            filled = rect.adjusted(2, 2, -2, -2)
            filled.setWidth(max(2, int(filled.width() * self._level)))
            grad = QLinearGradient(filled.topLeft(), filled.topRight())
            grad.setColorAt(0.0, QColor(pal.accent))
            grad.setColorAt(1.0, QColor(pal.success))
            inner = QPainterPath()
            inner.addRoundedRect(filled, 5, 5)
            p.fillPath(inner, grad)
        p.end()


class MicrophoneTester(QObject):
    """Open an input stream and report its RMS level.

    ``stream_factory`` is injectable so the test suite can drive the level
    without PortAudio, a microphone or a real audio thread.
    """

    level = Signal(float)
    failed = Signal(str)

    def __init__(self, device_name: Optional[str] = None,
                 stream_factory: Optional[Callable] = None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.device_name = device_name
        self._factory = stream_factory
        self._stream = None
        self.running = False

    def _default_factory(self, device_name: Optional[str], callback: Callable):
        from voicewright import audio

        if audio.sd is None:
            raise RuntimeError(tr("PortAudio is not available"))
        dev = device_index(device_name)
        # Some microphones do not accept 16 kHz directly; fall back to the
        # device's own default rate, exactly like the recorder does.
        rate = SAMPLE_RATE
        try:
            audio.sd.check_input_settings(
                device=dev, samplerate=SAMPLE_RATE, channels=1, dtype="float32")
        except Exception:  # noqa: BLE001
            info = (audio.sd.query_devices(dev, "input") if dev is not None
                    else audio.sd.query_devices(kind="input"))
            rate = int(info["default_samplerate"])
        return audio.sd.InputStream(
            samplerate=rate,
            channels=1,
            dtype="float32",
            device=dev,
            blocksize=int(rate * 0.05),
            callback=callback,
        )

    def _on_audio(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        try:
            data = np.asarray(indata)
            mono = data[:, 0] if data.ndim > 1 else data
            self.level.emit(float(np.sqrt(np.mean(mono ** 2))))
        except Exception:  # noqa: BLE001
            pass

    def start(self) -> bool:
        if self.running:
            return True
        factory = self._factory or self._default_factory
        stream = None
        try:
            stream = factory(self.device_name, self._on_audio)
            stream.start()
            self._stream = stream
            self.running = True
            return True
        except Exception as exc:  # noqa: BLE001
            self.running = False
            self._stream = None
            if stream is not None:
                try:
                    stream.close()
                except Exception:  # noqa: BLE001
                    pass
            log.info("Microphone test failed: %s", exc)
            self.failed.emit(str(exc) or type(exc).__name__)
            return False

    def stop(self) -> None:
        stream, self._stream = self._stream, None
        self.running = False
        if stream is None:
            return
        try:
            stream.stop()
        except Exception:  # noqa: BLE001
            pass
        try:
            stream.close()
        except Exception:  # noqa: BLE001
            pass


class OnboardingWizard(QDialog):
    """Welcome → model → microphone → shortcut and insertion check."""

    completed = Signal()
    hotkeyChanged = Signal()
    insertionTestRequested = Signal(str)

    PAGE_COUNT = 4

    def __init__(self, config: Config, icon: Optional[QIcon] = None,
                 insert_method: str = "") -> None:
        super().__init__(None)
        self.config = config
        self._index = 0
        self._download_task = None
        self._tester: Optional[MicrophoneTester] = None
        self._insert_method = insert_method
        self.setObjectName("Root")
        self.setWindowTitle(f"{APP_NAME} – {tr('Setup assistant')}")
        if icon is not None:
            self.setWindowIcon(icon)
        self.resize(720, 580)
        self.setMinimumSize(640, 520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 24, 30, 22)
        outer.setSpacing(16)

        head = QHBoxLayout()
        brand = QLabel(APP_NAME)
        brand.setObjectName("Brand")
        self.step_label = widgets.faint("")
        self.dots = QLabel("")
        self.dots.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head.addWidget(brand)
        head.addStretch(1)
        head.addWidget(self.dots)
        head.addWidget(self.step_label)
        outer.addLayout(head)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_welcome())
        self.stack.addWidget(self._page_model())
        self.stack.addWidget(self._page_microphone())
        self.stack.addWidget(self._page_shortcut())
        outer.addWidget(self.stack, 1)

        self.status = widgets.muted("")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)

        footer = QHBoxLayout()
        self.back_btn = QPushButton(tr("Back"))
        self.skip_btn = QPushButton(tr("Skip for now"))
        self.next_btn = QPushButton(tr("Next"))
        self.next_btn.setObjectName("Primary")
        self.back_btn.clicked.connect(self._back)
        self.skip_btn.clicked.connect(self._skip)
        self.next_btn.clicked.connect(self._next)
        footer.addWidget(self.back_btn)
        footer.addWidget(self.skip_btn)
        footer.addStretch(1)
        footer.addWidget(self.next_btn)
        outer.addLayout(footer)

        self._sync()

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------
    def _page_shell(self, title: str, sub: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 6, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(widgets.title(title))
        if sub:
            label = widgets.subtitle(sub)
            label.setWordWrap(True)
            lay.addWidget(label)
        return page, lay

    def _page_welcome(self) -> QWidget:
        page, lay = self._page_shell(
            tr("Welcome to Voicewright"),
            tr("Local dictation for Fedora, Windows and macOS – no account, no cloud required."),
        )
        card = widgets.Card()
        for text in (
            tr("Speak naturally and let Voicewright type into the active window."),
            tr("Speech recognition runs entirely on this computer."),
            tr("One shortcut handles tap-to-toggle and hold-to-talk."),
            tr("Cloud cleanup and history are opt-in and off by default."),
        ):
            row = QLabel("•  " + text)
            row.setWordWrap(True)
            card.body.addWidget(row)
        lay.addWidget(card)
        note = widgets.muted(tr(
            "This assistant takes about two minutes. You can skip any step and reopen it later."))
        note.setWordWrap(True)
        lay.addWidget(note)
        lay.addStretch(1)
        return page

    def _page_model(self) -> QWidget:
        page, lay = self._page_shell(
            tr("Choose a speech model"),
            tr("Downloads start only when you click the button. Every file is checked by size and SHA-256."),
        )
        card = widgets.Card()
        form = QFormLayout()
        form.setSpacing(10)
        self.model_combo = QComboBox()
        for model in CATALOG:
            suffix = ""
            if model.engine == "sherpa-onnx" and not sherpa_available():
                suffix = " – " + tr("needs sherpa-onnx")
            self.model_combo.addItem(f"{model.name} · {model.size_mb} MB{suffix}", model.id)
        preferred = self.config.get("speech_model") or recommended_model(
            cuda=cuda_available(), sherpa=sherpa_available())
        index = self.model_combo.findData(preferred)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        form.addRow(tr("Model:"), self.model_combo)
        self.model_note = widgets.muted("")
        self.model_note.setWordWrap(True)
        form.addRow("", self.model_note)
        card.body.addLayout(form)

        row = QHBoxLayout()
        self.download_btn = QPushButton(tr("Download and use"))
        self.download_btn.setObjectName("Primary")
        self.download_btn.clicked.connect(self._download_or_use)
        self.dl_progress = QProgressBar()
        self.dl_progress.setVisible(False)
        row.addWidget(self.download_btn)
        row.addWidget(self.dl_progress, 1)
        card.body.addLayout(row)
        self.model_status = widgets.muted("")
        card.body.addWidget(self.model_status)
        lay.addWidget(card)

        rec = recommended_model(cuda=cuda_available(), sherpa=sherpa_available())
        rec_model = CATALOG_BY_ID.get(rec)
        rec_name = rec_model.name if rec_model is not None else rec
        hint = widgets.muted(tr("Recommended for this computer:") + f" <b>{rec_name}</b>")
        lay.addWidget(hint)
        lay.addStretch(1)

        self.model_combo.currentIndexChanged.connect(self._model_selected)
        self._model_selected()
        return page

    def _page_microphone(self) -> QWidget:
        page, lay = self._page_shell(
            tr("Test your microphone"),
            tr("Speak a sentence. The bar should move while you talk; nothing is recorded or uploaded."),
        )
        card = widgets.Card()
        form = QFormLayout()
        form.setSpacing(10)
        self.mic_combo = QComboBox()
        self._fill_mics()
        mic_row = QHBoxLayout()
        mic_row.addWidget(self.mic_combo, 1)
        refresh = QPushButton(tr("Refresh"))
        refresh.clicked.connect(self._fill_mics)
        mic_row.addWidget(refresh)
        form.addRow(tr("Input device:"), mic_row)
        card.body.addLayout(form)

        self.meter = LevelMeter()
        card.body.addWidget(self.meter)
        row = QHBoxLayout()
        self.mic_btn = QPushButton(tr("Start microphone test"))
        self.mic_btn.clicked.connect(self._toggle_mic)
        row.addWidget(self.mic_btn)
        row.addStretch(1)
        card.body.addLayout(row)
        self.mic_status = widgets.muted("")
        self.mic_status.setWordWrap(True)
        card.body.addWidget(self.mic_status)
        lay.addWidget(card)
        lay.addStretch(1)
        return page

    def _page_shortcut(self) -> QWidget:
        page, lay = self._page_shell(
            tr("Shortcut and insertion"),
            tr("Check the shortcut and paste a test sentence into the field below."),
        )
        card = widgets.Card()
        form = QFormLayout()
        form.setSpacing(10)
        self.hotkey_edit = HotkeyEdit(self.config.get("hotkey", "ctrl+shift+space"))
        self.hotkey_edit.hotkeyChanged.connect(self._save_hotkey)
        self.hotkey_edit.error.connect(lambda m: QMessageBox.warning(self, APP_NAME, m))
        form.addRow(tr("Dictation shortcut:"), self.hotkey_edit)
        self.transform_edit = HotkeyEdit(self.config.get("transform_hotkey", "ctrl+alt+space"))
        self.transform_edit.hotkeyChanged.connect(self._save_transform_hotkey)
        self.transform_edit.error.connect(lambda m: QMessageBox.warning(self, APP_NAME, m))
        form.addRow(tr("Rewrite selection shortcut:"), self.transform_edit)
        self.method_label = widgets.muted(self._insert_method or tr("Automatic"))
        form.addRow(tr("Insertion method:"), self.method_label)
        card.body.addLayout(form)

        test_row = QHBoxLayout()
        self.test_field = QLineEdit()
        self.test_field.setPlaceholderText(tr("The test text appears here"))
        self.test_btn = QPushButton(tr("Test insertion"))
        self.test_btn.clicked.connect(self._test_insertion)
        test_row.addWidget(self.test_field, 1)
        test_row.addWidget(self.test_btn)
        card.body.addLayout(test_row)
        self.test_status = widgets.muted("")
        card.body.addWidget(self.test_status)
        lay.addWidget(card)

        self.autostart_cb = QCheckBox(tr("Launch at login"))
        try:
            self.autostart_cb.setChecked(autostart.is_enabled())
        except Exception:  # noqa: BLE001
            self.autostart_cb.setEnabled(False)
        self.autostart_cb.toggled.connect(self._set_autostart)
        lay.addWidget(self.autostart_cb)
        lay.addStretch(1)
        return page

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    @property
    def current_index(self) -> int:
        return self._index

    def show_step(self, index: int) -> None:
        self._leave_page()
        self._index = max(0, min(int(index), self.PAGE_COUNT - 1))
        self._sync()

    def _sync(self) -> None:
        self.stack.setCurrentIndex(self._index)
        self.step_label.setText(tr("Step {n} of {total}").format(n=self._index + 1, total=self.PAGE_COUNT))
        self.dots.setText(" ".join("●" if i <= self._index else "○" for i in range(self.PAGE_COUNT)))
        self.back_btn.setEnabled(self._index > 0)
        self.skip_btn.setVisible(self._index in (1, 2))
        self.next_btn.setText(tr("Finish") if self._index == self.PAGE_COUNT - 1 else tr("Next"))
        if self._index == 2:
            self.status.setText(tr("Tip: speak normally at the distance you will use later."))
        else:
            self.status.setText("")

    def _leave_page(self) -> None:
        if self._index == 2:
            self._stop_mic()

    def _back(self) -> None:
        if self._index > 0:
            self._leave_page()
            self._index -= 1
            self._sync()

    def _skip(self) -> None:
        self._leave_page()
        self._index = min(self._index + 1, self.PAGE_COUNT - 1)
        self._sync()

    def _next(self) -> None:
        if self._index >= self.PAGE_COUNT - 1:
            self._finish()
            return
        self._leave_page()
        self._index += 1
        self._sync()

    def _finish(self) -> None:
        self._stop_mic()
        self.config.set("onboarding_done", True)
        self.config.set("first_run_done", True)
        self.completed.emit()
        self.accept()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_mic()
        if self._download_task is not None:
            self._download_task.cancel_event.set()
        # Closing is a deliberate skip; do not show the assistant on every
        # start. It stays reachable from the settings and the tray menu.
        self.config.set("onboarding_done", True)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Model step
    # ------------------------------------------------------------------
    def _model_selected(self, *_args) -> None:
        mid = self.model_combo.currentData()
        model = CATALOG_BY_ID.get(mid)
        if model is None:
            return
        runnable = model.engine != "sherpa-onnx" or sherpa_available()
        note = tr(model.note)
        if not runnable:
            note = tr("This model needs the sherpa-onnx package. Choose a Whisper model instead.")
        self.model_note.setText(f"<b>{model.name}</b> · {model.license}<br>{note}")
        downloaded = is_downloaded(mid)
        self.download_btn.setEnabled(runnable and self._download_task is None)
        self.download_btn.setText(tr("Use this model") if downloaded else tr("Download and use"))
        self.model_status.setText(tr("Already downloaded") if downloaded else "")

    def _download_or_use(self) -> None:
        mid = self.model_combo.currentData()
        model = CATALOG_BY_ID.get(mid)
        if model is None:
            return
        if model.engine == "sherpa-onnx" and not sherpa_available():
            QMessageBox.warning(self, APP_NAME, tr(
                "This model needs the sherpa-onnx package. Choose a Whisper model instead."))
            return
        if is_downloaded(mid):
            self.config.set("speech_model", mid)
            self.model_status.setText(tr("Active model:") + f" {model.name}")
            return

        self.download_btn.setEnabled(False)
        self.dl_progress.setVisible(True)
        self.dl_progress.setRange(0, 0)

        def on_progress(done, total, name):
            if total <= 1:
                self.dl_progress.setRange(0, 0)
                return
            self.dl_progress.setRange(0, 1000)
            self.dl_progress.setValue(int(1000 * done / max(1, total)))
            self.dl_progress.setFormat(f"{done / 1e6:.0f} / {total / 1e6:.0f} MB ({name})")

        def on_done(_result):
            self._download_task = None
            self.dl_progress.setVisible(False)
            self.config.set("speech_model", mid)
            self.model_status.setText(tr("Model downloaded and selected:") + f" {model.name}")
            self._model_selected()

        def on_error(message):
            self._download_task = None
            self.dl_progress.setVisible(False)
            self.download_btn.setEnabled(True)
            self.model_status.setText(tr("Download failed:") + f" {message}")

        self.model_status.setText(tr("Downloading…"))
        self._download_task = run_task(
            download_model, mid, with_progress=True,
            on_done=on_done, on_error=on_error, on_progress=on_progress,
        )

    # ------------------------------------------------------------------
    # Microphone step
    # ------------------------------------------------------------------
    def _fill_mics(self) -> None:
        self.mic_combo.blockSignals(True)
        self.mic_combo.clear()
        self.mic_combo.addItem(tr("System default"), None)
        for name in list_input_devices():
            self.mic_combo.addItem(name, name)
        self.mic_combo.blockSignals(False)

    def _toggle_mic(self) -> None:
        if self._tester is not None and self._tester.running:
            self._stop_mic()
        else:
            self._start_mic()

    def _start_mic(self) -> None:
        self._stop_mic()
        self._tester = MicrophoneTester(self.mic_combo.currentData())
        self._tester.level.connect(self.meter.set_level)
        self._tester.failed.connect(self._mic_failed)
        self.meter.set_level(0.0)
        if self._tester.start():
            self.mic_btn.setText(tr("Stop microphone test"))
            self.mic_status.setText(tr("Listening… speak now."))
        else:
            self.mic_btn.setText(tr("Start microphone test"))

    def _mic_failed(self, message: str) -> None:
        self.mic_btn.setText(tr("Start microphone test"))
        self.mic_status.setText(tr("Microphone unavailable:") + f" {message}")

    def _stop_mic(self) -> None:
        if self._tester is not None:
            self._tester.stop()
            self._tester.deleteLater()
            self._tester = None
        if hasattr(self, "mic_btn"):
            self.mic_btn.setText(tr("Start microphone test"))
        if hasattr(self, "meter"):
            self.meter.set_level(0.0)

    # ------------------------------------------------------------------
    # Shortcut step
    # ------------------------------------------------------------------
    def _save_hotkey(self, hotkey: str) -> None:
        self.config.set("hotkey", hotkey)
        if self._rewrite_overlaps():
            self.test_status.setText(
                tr("The rewrite shortcut overlaps dictation and stays off. Choose another one."))
        else:
            self.test_status.setText(tr("Shortcut saved."))
        self.hotkeyChanged.emit()

    def _save_transform_hotkey(self, hotkey: str) -> None:
        self.config.set("transform_hotkey", hotkey)
        self._save_hotkey(self.config.get("hotkey"))

    def _rewrite_overlaps(self) -> bool:
        try:
            return combos_conflict(
                parse_hotkey(self.config.get("transform_hotkey", "")),
                parse_hotkey(self.config.get("hotkey")),
            )
        except ValueError:
            return False

    def _test_insertion(self) -> None:
        self.test_field.clear()
        self.test_field.setFocus()
        self.test_status.setText(tr("Paste requested. The text should appear in the field."))
        self.insertionTestRequested.emit(tr("Voicewright insertion test"))

    def _set_autostart(self, enabled: bool) -> None:
        try:
            autostart.set_enabled(enabled)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, APP_NAME, str(exc))
