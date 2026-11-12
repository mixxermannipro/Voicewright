"""Persistent JSON configuration with defaults and forward-compatible merging."""
from __future__ import annotations

import copy
import json
import logging
import threading
from pathlib import Path
from typing import Any

from voicewright.paths import config_dir

log = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "ui_language": "auto",            # auto | de | en
    "first_run_done": False,
    # --- Hotkey -----------------------------------------------------------
    "hotkey": "ctrl+shift+space",
    "hotkey_mode": "toggle",          # toggle | hold
    "hotkey_backend": "auto",         # auto | pynput | none
    "cancel_with_escape": True,
    "min_hold_ms": 250,               # hold-mode: ignore taps shorter than this
    # --- Audio ------------------------------------------------------------
    "input_device": None,             # None = system default, else device name
    "sounds_enabled": True,
    "max_recording_seconds": 600,
    "silence_trim": True,
    # --- Transcription ----------------------------------------------------
    "whisper_model": "small",
    "whisper_device": "auto",         # auto | cpu | cuda
    "whisper_compute_type": "auto",   # auto | int8 | int8_float16 | float16 | float32
    "language": "auto",               # auto or ISO code
    "whisper_task": "transcribe",     # transcribe | translate (to English, offline)
    "initial_prompt": "",             # vocabulary hints for Whisper
    "vad_filter": True,
    "beam_size": 5,
    "keep_model_loaded": True,
    # --- Cleanup ----------------------------------------------------------
    "cleanup_enabled": False,
    "cleanup_provider": "rules",     # none | rules | gemini | openai | anthropic | groq |
                                      # openrouter | mistral | ollama | lmstudio | custom
    "cleanup_models": {               # selected model per provider
        "gemini": "gemini-2.5-flash",
        "openai": "gpt-4.1-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "groq": "llama-3.3-70b-versatile",
        "openrouter": "google/gemini-2.5-flash",
        "mistral": "mistral-small-latest",
        "ollama": "llama3.2",
        "lmstudio": "",
        "custom": "",
    },
    "custom_base_url": "http://localhost:8000/v1",
    "ollama_base_url": "http://localhost:11434/v1",
    "lmstudio_base_url": "http://localhost:1234/v1",
    "cleanup_style": "clean",         # clean | minimal | formal | casual
    "output_language": "same",        # same | ISO code -> AI translates into this language
    "custom_instructions": "",
    "cleanup_timeout": 30,
    "cleanup_fallback_rules": True,   # use rule-based cleanup if the API fails
    "custom_dictionary": [],          # words/names to preserve spelling of
    # --- Output -----------------------------------------------------------
    "add_trailing_space": True,
    # --- UI ---------------------------------------------------------------
    "show_overlay": True,
    "overlay_position": "bottom",     # bottom | top
    "start_minimized": True,
    "history_enabled": False,
    "history_limit": 200,
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (config_dir() / "config.json")
        self._lock = threading.RLock()
        self._data: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        with self._lock:
            if self.path.exists():
                try:
                    loaded = json.loads(self.path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        self._data = _deep_merge(DEFAULT_CONFIG, loaded)
                except Exception as exc:  # corrupt file -> keep defaults, back it up
                    log.error("Could not read config (%s); using defaults", exc)
                    try:
                        self.path.rename(self.path.with_suffix(".broken.json"))
                    except OSError:
                        pass

    def save(self) -> None:
        with self._lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return copy.deepcopy(self._data.get(key, default))

    def set(self, key: str, value: Any, save: bool = True) -> None:
        with self._lock:
            self._data[key] = value
            if save:
                self.save()

    def update(self, values: dict[str, Any]) -> None:
        with self._lock:
            self._data.update(values)
            self.save()

    def cleanup_model(self, provider: str) -> str:
        return self.get("cleanup_models", {}).get(provider, "")

    def set_cleanup_model(self, provider: str, model: str) -> None:
        with self._lock:
            self._data.setdefault("cleanup_models", {})[provider] = model
            self.save()

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data)
