"""API key storage.

Keys are stored in the OS keychain (Windows Credential Manager, macOS Keychain,
Secret Service / KWallet on Linux) via `keyring`. If no keychain backend is
available, a fallback file with user-only permissions is used.
"""
from __future__ import annotations

import json
import logging
import os
import stat

from voicewright import APP_ID
from voicewright.paths import config_dir

log = logging.getLogger(__name__)

try:
    import keyring  # type: ignore
    from keyring.errors import KeyringError  # type: ignore
except Exception:  # pragma: no cover - optional
    keyring = None
    KeyringError = Exception

_FALLBACK = config_dir() / "keys.json"


def _keyring_usable() -> bool:
    if keyring is None:
        return False
    try:
        backend = keyring.get_keyring()
        mod = type(backend).__module__.lower()
        if mod.endswith((".fail", ".null")):
            return False
        return getattr(backend, "priority", 1) > 0
    except Exception:
        return False


def _read_fallback() -> dict:
    if _FALLBACK.exists():
        try:
            return json.loads(_FALLBACK.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _write_fallback(data: dict) -> None:
    _FALLBACK.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(_FALLBACK, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def get_api_key(provider: str) -> str:
    env = os.environ.get(f"VOICEWRIGHT_{provider.upper()}_API_KEY")
    if env:
        return env
    if _keyring_usable():
        try:
            val = keyring.get_password(APP_ID, provider)
            if val:
                return val
        except KeyringError as exc:
            log.warning("keyring read failed: %s", exc)
    return _read_fallback().get(provider, "")


def set_api_key(provider: str, key: str) -> str:
    """Store key. Returns the storage location used ('keychain' or 'file')."""
    key = key.strip()
    if _keyring_usable():
        try:
            if key:
                keyring.set_password(APP_ID, provider, key)
            else:
                try:
                    keyring.delete_password(APP_ID, provider)
                except Exception:
                    pass
            data = _read_fallback()
            if provider in data:
                data.pop(provider)
                _write_fallback(data)
            return "keychain"
        except KeyringError as exc:
            log.warning("keyring write failed, using file fallback: %s", exc)
    data = _read_fallback()
    if key:
        data[provider] = key
    else:
        data.pop(provider, None)
    _write_fallback(data)
    return "file"
