"""Run blocking work in a background thread and deliver results via Qt signals."""
from __future__ import annotations

import logging
import threading
import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal

log = logging.getLogger(__name__)
_running: set["Task"] = set()


class Task(QObject):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(object, object, str)

    def __init__(self, fn: Callable[..., Any], *args, with_progress: bool = False, **kwargs) -> None:
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.with_progress = with_progress
        self.cancel_event = threading.Event()
        # Release the reference on the GUI thread, after the result was delivered.
        self.done.connect(lambda _r: _running.discard(self))
        self.failed.connect(lambda _e: _running.discard(self))

    def start(self) -> "Task":
        _running.add(self)
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def _run(self) -> None:
        try:
            if self.with_progress:
                self.kwargs["progress"] = lambda a, b, c="": self.progress.emit(a, b, c)
                self.kwargs.setdefault("cancel_event", self.cancel_event)
            result = self.fn(*self.args, **self.kwargs)
            self.done.emit(result)
        except Exception as exc:  # noqa: BLE001
            log.debug("Task failed: %s", traceback.format_exc())
            self.failed.emit(str(exc) or type(exc).__name__)


def run_task(fn: Callable[..., Any], *args, on_done=None, on_error=None, on_progress=None,
             with_progress: bool = False, **kwargs) -> Task:
    t = Task(fn, *args, with_progress=with_progress, **kwargs)
    if on_done:
        t.done.connect(on_done)
    if on_error:
        t.failed.connect(on_error)
    if on_progress:
        t.progress.connect(on_progress)
    return t.start()
