"""Copy a finished dictation on the Qt main thread."""
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication

from voicewright.config import Config


class Injector(QObject):
    finished = Signal(bool, str)

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

    def insert(self, text: str) -> None:
        clipboard = QGuiApplication.clipboard()
        if not text or clipboard is None:
            self.finished.emit(False, "COPY_FAILED")
            return
        if self.config.get("add_trailing_space", True) and not text.endswith((" ", "\n")):
            text += " "
        clipboard.setText(text)
        self.finished.emit(True, "CLIPBOARD_ONLY")
