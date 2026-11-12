"""Local history of dictations (JSON file, never leaves the machine)."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from voicewright.paths import data_dir


class History:
    def __init__(self, limit: int = 200, path: Path | None = None) -> None:
        self.path = path or (data_dir() / "history.json")
        self.limit = limit
        self._lock = threading.Lock()
        self.items: list[dict] = []
        if self.path.exists():
            try:
                self.items = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.items = []

    def add(self, raw: str, cleaned: str, language: str, duration: float, provider: str) -> dict:
        item = {"ts": time.time(), "raw": raw, "text": cleaned, "language": language,
                "duration": round(duration, 1), "provider": provider}
        with self._lock:
            self.items.insert(0, item)
            del self.items[self.limit:]
            self._save()
        return item

    def clear(self) -> None:
        with self._lock:
            self.items = []
            self._save()

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.items, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)
