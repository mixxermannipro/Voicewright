"""Persistent JSON configuration with defaults, migration and forward-compatible merging.

Schema version 2 adds the hybrid hotkey, cross-platform insertion, local speech
engines and local cleanup models. Version 1 files are migrated without losing
keys: unknown keys are preserved, `whisper_model` is mirrored to `speech_model`,
and nothing is downloaded or rewritten silently.
"""
from __future__ import annotations

import copy
import json
import logging
import threading
from pathlib import Path
from typing import Any

from voicewright.paths import config_dir

log = logging.getLogger(__name__)

SCHEMA_VERSION = 2

DEFAULT_CONFIG: dict[str, Any] = {
    "version": SCHEMA_VERSION,
    "ui_language": "auto",            # auto | de | en
    "first_run_done": False,
    "onboarding_done": False,         # four-step setup assistant completed
    # --- Hotkey -----------------------------------------------------------
    "hotkey": "ctrl+shift+space",
    "hotkey_mode": "hybrid",          # hybrid | toggle | hold
    "hotkey_backend": "auto",         # auto | pynput | portal | none
    "tap_threshold_ms": 350,          # hybrid: release before this keeps recording
    "cancel_with_escape": True,
    "min_hold_ms": 250,               # hold mode: ignore taps shorter than this
    "transform_hotkey": "ctrl+alt+space",
    "wayland_hotkey": "portal",       # portal | desktop
    # --- Audio ------------------------------------------------------------
    "input_device": None,             # None = system default, else device name
    "sounds_enabled": True,
    "max_recording_seconds": 600,
    "silence_trim": True,
    # --- Transcription ----------------------------------------------------
    "speech_model": "parakeet-v3",    # id from voicewright.models.CATALOG
    "speech_engine": "auto",          # auto | whisper | sherpa
    "whisper_model": "small",         # legacy alias, kept in sync
    "whisper_device": "auto",         # auto | cpu | cuda
    "whisper_compute_type": "auto",   # auto | int8 | int8_float16 | float16 | float32
    "language": "auto",               # auto or ISO code
    "whisper_task": "transcribe",     # transcribe | translate (to English, offline)
    "initial_prompt": "",             # vocabulary hints for Whisper
    "vad_filter": True,
    "beam_size": 5,
    "keep_model_loaded": True,
    # --- Cleanup ----------------------------------------------------------
    "cleanup_enabled": True,
    "cleanup_provider": "rules",     # none | rules | local | gemini | openai | anthropic |
                                      # groq | openrouter | mistral | ollama | lmstudio | custom
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
    "cleanup_style": "clean",         # clean | minimal | formal | casual | notes | email
    "output_language": "same",        # same | ISO code -> AI translates into this language
    "custom_instructions": "",
    "cleanup_timeout": 30,
    "cleanup_fallback_rules": True,   # use rule-based cleanup if the API fails
    "custom_dictionary": [],          # words/names to preserve spelling of
    # --- Local cleanup model ----------------------------------------------
    "local_model": "qwen3-0.6b-q4",   # id from voicewright.models.CLEANUP_CATALOG
    "llm_runtime": "auto",            # auto | bundled | ollama | lmstudio | off
    "llm_model": "",                  # model name for Ollama / LM Studio
    "llm_threads": 0,                 # 0 = auto
    "llm_context": 2048,
    "guard_enabled": True,            # protection check after the local model
    # --- Smart formatting --------------------------------------------------
    "smart_formatting": True,
    "spoken_punctuation": True,
    "structure_mode": "auto",         # auto | off | list | email | notes
    "command_mode": True,
    "snippets": [],                   # [{"name": ..., "text": ...}]
    "replacements": {},               # {"heard": "written"}
    "emoji_enabled": False,
    # --- Output -----------------------------------------------------------
    "insert_mode": "auto",            # auto | paste | type | clipboard
    "paste_shortcut": "auto",         # auto | ctrl_v | ctrl_shift_v
    "restore_clipboard": True,
    "clipboard_restore_ms": 400,
    "add_trailing_space": True,
    "wayland_inject": "portal",       # portal | wtype | ydotool | clipboard
    "ydotool_enabled": False,         # explicit opt-in only
    # --- UI ---------------------------------------------------------------
    "theme": "system",                # system | light | dark
    "reduce_motion": False,
    "show_overlay": True,
    "overlay_position": "bottom",     # bottom | top
    "start_minimized": True,
    "history_enabled": False,
    "history_limit": 200,
    "stats_enabled": True,
    # --- Consent ----------------------------------------------------------
    "wayland_consent": False,         # user agreed to portal keyboard control
    # Restore token returned by RemoteDesktop.Start(). It lets the portal
    # re-open the keyboard session without another dialog. The portal
    # invalidates a token after one use and returns a fresh one.
    "wayland_restore_token": "",
}

# Keys that exist in v1 but must keep a place in the v2 UI. Kept as a documented
# list so a future cleanup cannot silently drop them.
V1_KEYS = (
    "whisper_device", "whisper_compute_type", "beam_size", "initial_prompt",
    "vad_filter", "whisper_task", "output_language", "cleanup_style",
    "custom_instructions", "add_trailing_space", "start_minimized", "ui_language",
    "history_limit",
)

LEGACY_MODEL_MAP: dict[str, str] = {
    "tiny": "whisper-tiny",
    "tiny.en": "whisper-tiny",
    "base": "whisper-base",
    "base.en": "whisper-base",
    "small": "whisper-small",
    "small.en": "whisper-small",
    "medium": "whisper-medium",
    "large-v3-turbo": "whisper-large-v3-turbo",
    "large-v3": "whisper-large-v3",
}


def _map_model_id(model_id: Any) -> Any:
    if isinstance(model_id, str):
        return LEGACY_MODEL_MAP.get(model_id, model_id)
    return model_id


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a stored config dict to the current schema, in place semantics."""
    data = copy.deepcopy(data)
    version = int(data.get("version", 1) or 1)

    # v1 -> v2 ---------------------------------------------------------
    if version < 2:
        legacy_model = data.get("whisper_model")
        if legacy_model and "speech_model" not in data:
            data["speech_model"] = _map_model_id(legacy_model)
        # v1 had separate toggle/hold modes. Both keep working; new installs
        # start in hybrid mode because it covers both gestures.
        if data.get("hotkey_mode") not in ("toggle", "hold", "hybrid"):
            data["hotkey_mode"] = "hybrid"
        data.setdefault("cleanup_enabled", False)
        # Existing users already completed the old first-run flow; never show
        # the new setup assistant uninvited.
        data.setdefault("onboarding_done", bool(data.get("first_run_done", False)))
        data["version"] = 2

    if data.get("speech_model"):
        data["speech_model"] = _map_model_id(data["speech_model"])
    if data.get("whisper_model"):
        data["whisper_model"] = _map_model_id(data["whisper_model"])

    # Keep the legacy alias consistent in both directions.
    if data.get("speech_model") and not data.get("whisper_model"):
        data["whisper_model"] = data["speech_model"]
    if data.get("whisper_model") and not data.get("speech_model"):
        data["speech_model"] = data["whisper_model"]

    # Repair obviously wrong values instead of crashing later.
    if data.get("hotkey_mode") not in ("toggle", "hold", "hybrid"):
        data["hotkey_mode"] = "hybrid"
    if data.get("insert_mode") not in ("auto", "paste", "type", "clipboard"):
        data["insert_mode"] = "auto"
    if data.get("theme") not in ("system", "light", "dark"):
        data["theme"] = "system"
    try:
        data["tap_threshold_ms"] = max(150, min(900, int(data.get("tap_threshold_ms", 350))))
    except (TypeError, ValueError):
        data["tap_threshold_ms"] = 350
    try:
        data["history_limit"] = max(0, min(2000, int(data.get("history_limit", 200))))
    except (TypeError, ValueError):
        data["history_limit"] = 200
    if not isinstance(data.get("snippets"), list):
        data["snippets"] = []
    if not isinstance(data.get("replacements"), dict):
        data["replacements"] = {}
    if not isinstance(data.get("wayland_restore_token"), str):
        data["wayland_restore_token"] = ""
    # Anyone who already finished the old first-run flow must not see the new
    # assistant uninvited, even if the config was written by an early 2.0 build.
    data.setdefault("onboarding_done", bool(data.get("first_run_done", False)))
    data["onboarding_done"] = bool(data["onboarding_done"])
    data["version"] = SCHEMA_VERSION
    return data


class Config:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (config_dir() / "config.json")
        self._lock = threading.RLock()
        self._data: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                return
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as exc:  # corrupt file -> keep defaults, back it up
                log.error("Could not read config (%s); using defaults", exc)
                try:
                    self.path.rename(self.path.with_suffix(".broken.json"))
                except OSError:
                    pass
                return
            if not isinstance(loaded, dict):
                log.error("Config is not an object; using defaults")
                return
            migrated = migrate(loaded)
            self._data = _deep_merge(DEFAULT_CONFIG, migrated)

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
            if key in ("speech_model", "whisper_model"):
                mapped = _map_model_id(value)
                self._data["speech_model"] = mapped
                self._data["whisper_model"] = mapped
            else:
                self._data[key] = value
            if save:
                self.save()

    def update(self, values: dict[str, Any]) -> None:
        with self._lock:
            self._data.update(values)
            if "speech_model" in values:
                mapped = _map_model_id(values["speech_model"])
                self._data["speech_model"] = mapped
                self._data["whisper_model"] = mapped
            elif "whisper_model" in values:
                mapped = _map_model_id(values["whisper_model"])
                self._data["speech_model"] = mapped
                self._data["whisper_model"] = mapped
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
