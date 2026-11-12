"""Platform specific directories (config, data, models, logs)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from voicewright import APP_ID, APP_NAME

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def _base_config_dir() -> Path:
    if IS_WINDOWS:
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
    if IS_MACOS:
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_ID


def _base_data_dir() -> Path:
    if IS_WINDOWS:
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
    if IS_MACOS:
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_ID


def config_dir() -> Path:
    override = os.environ.get("VOICEWRIGHT_CONFIG_DIR")
    p = Path(override) if override else _base_config_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def data_dir() -> Path:
    override = os.environ.get("VOICEWRIGHT_DATA_DIR")
    p = Path(override) if override else _base_data_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def models_dir() -> Path:
    p = data_dir() / "models"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def resource_path(*parts: str) -> Path:
    """Locate bundled resources both in source checkouts and PyInstaller builds."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidate = Path(base).joinpath("assets", *parts)
        if candidate.exists():
            return candidate
    here = Path(__file__).resolve()
    for root in (here.parent / "assets", here.parents[2] / "assets"):
        candidate = root.joinpath(*parts)
        if candidate.exists():
            return candidate
    return here.parent.joinpath("assets", *parts)


def session_type() -> str:
    """Return 'wayland', 'x11' or '' (non-Linux)."""
    if not IS_LINUX:
        return ""
    st = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if st in ("wayland", "x11"):
        return st
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return ""
