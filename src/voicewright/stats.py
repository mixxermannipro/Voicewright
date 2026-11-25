"""Local usage statistics. Never leaves the machine, no text is stored."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from voicewright.paths import data_dir


class Stats:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (data_dir() / "stats.json")
        self._lock = threading.Lock()
        self._data = {"sessions": 0, "words": 0, "characters": 0,
                      "audio_seconds": 0.0, "days": {}, "first_use": None}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self._data.update(loaded)
            except Exception:
                pass

    def record(self, text: str, audio_seconds: float = 0.0) -> None:
        words = len([w for w in text.split() if w.strip()])
        if words == 0 and not text.strip():
            return
        with self._lock:
            self._data["sessions"] = int(self._data.get("sessions", 0)) + 1
            self._data["words"] = int(self._data.get("words", 0)) + words
            self._data["characters"] = int(self._data.get("characters", 0)) + len(text)
            self._data["audio_seconds"] = round(
                float(self._data.get("audio_seconds", 0.0)) + max(0.0, audio_seconds), 1)
            if not self._data.get("first_use"):
                self._data["first_use"] = time.time()
            day = time.strftime("%Y-%m-%d")
            days = self._data.setdefault("days", {})
            entry = days.setdefault(day, {"sessions": 0, "words": 0})
            entry["sessions"] += 1
            entry["words"] += words
            self._save()

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=1, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    # ------------------------------------------------------------------
    @property
    def sessions(self) -> int:
        return int(self._data.get("sessions", 0))

    @property
    def words(self) -> int:
        return int(self._data.get("words", 0))

    @property
    def audio_seconds(self) -> float:
        return float(self._data.get("audio_seconds", 0.0))

    def seconds_saved(self, typing_speed: float = 40.0) -> float:
        """Rough estimate: words typed at ``typing_speed`` per minute."""
        minutes_typing = self.words / max(1.0, typing_speed)
        return max(0.0, minutes_typing * 60 - self.audio_seconds)

    def last_days(self, count: int = 7) -> list[tuple[str, int]]:
        days = self._data.get("days", {})
        out = []
        now = time.time()
        for i in range(count - 1, -1, -1):
            day = time.strftime("%Y-%m-%d", time.localtime(now - i * 86400))
            out.append((day, int(days.get(day, {}).get("words", 0))))
        return out

    def summary(self) -> str:
        saved = self.seconds_saved()
        hours, rest = divmod(int(saved), 3600)
        minutes = rest // 60
        if hours:
            saved_text = f"{hours} h {minutes} min"
        else:
            saved_text = f"{minutes} min"
        return f"{self.sessions} dictations · {self.words} words · about {saved_text} saved"

    def reset(self) -> None:
        with self._lock:
            self._data = {"sessions": 0, "words": 0, "characters": 0,
                          "audio_seconds": 0.0, "days": {}, "first_use": None}
            self._save()
