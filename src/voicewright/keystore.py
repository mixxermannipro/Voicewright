"""Read explicit environment overrides and store keys in the system keyring."""
from __future__ import annotations

import logging
import os

from voicewright import APP_ID

log = logging.getLogger(__name__)

try:
    import keyring
    from keyring.errors import PasswordDeleteError
except ImportError:
    keyring = None


def _keyring_usable() -> bool:
    if keyring is None:
        return False
    try:
        backend = keyring.get_keyring()
        return type(backend).__module__.startswith("keyring.backends.") and backend.priority > 0
    except Exception:
        return False


def get_api_key(provider: str) -> str:
    env = os.environ.get(f"VOICEWRIGHT_{provider.upper()}_API_KEY")
    if env:
        return env
    if _keyring_usable():
        try:
            return keyring.get_password(APP_ID, provider) or ""
        except Exception:
            log.warning("System keyring read failed")
    return ""


def set_api_key(provider: str, key: str) -> str:
    if not _keyring_usable():
        return "unavailable"
    try:
        if key.strip():
            keyring.set_password(APP_ID, provider, key.strip())
        elif keyring.get_password(APP_ID, provider) is not None:
            keyring.delete_password(APP_ID, provider)
        return "keychain"
    except PasswordDeleteError:
        log.warning("System keyring delete failed")
    except Exception:
        log.warning("System keyring write failed")
    return "unavailable"
