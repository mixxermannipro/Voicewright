"""Launch-at-login for Windows (registry), macOS (LaunchAgent) and Linux (XDG autostart)."""
from __future__ import annotations

import logging
import os
import plistlib
import sys
from pathlib import Path

from voicewright import APP_ID, APP_NAME
from voicewright.paths import IS_LINUX, IS_MACOS, IS_WINDOWS

log = logging.getLogger(__name__)


def _launch_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--minimized"]
    return [sys.executable, "-m", "voicewright", "--minimized"]


def _linux_file() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart" / f"{APP_ID}.desktop"


def _mac_file() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"io.github.{APP_ID}.plist"


def is_enabled() -> bool:
    try:
        if IS_WINDOWS:
            import winreg  # type: ignore
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
                winreg.QueryValueEx(k, APP_NAME)
                return True
        if IS_MACOS:
            return _mac_file().exists()
        if IS_LINUX:
            return _linux_file().exists()
    except OSError:
        return False
    return False


def set_enabled(enabled: bool) -> None:
    cmd = _launch_command()
    if IS_WINDOWS:
        import winreg  # type: ignore
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, " ".join(f'"{c}"' for c in cmd))
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
    elif IS_MACOS:
        f = _mac_file()
        if enabled:
            f.parent.mkdir(parents=True, exist_ok=True)
            with open(f, "wb") as fh:
                plistlib.dump({"Label": f"io.github.{APP_ID}", "ProgramArguments": cmd,
                               "RunAtLoad": True, "ProcessType": "Interactive"}, fh)
        else:
            f.unlink(missing_ok=True)
    elif IS_LINUX:
        f = _linux_file()
        if enabled:
            f.parent.mkdir(parents=True, exist_ok=True)
            exec_line = " ".join(f'"{c}"' if " " in c else c for c in cmd)
            f.write_text(
                "[Desktop Entry]\nType=Application\n"
                f"Name={APP_NAME}\nExec={exec_line}\nIcon={APP_ID}\n"
                "X-GNOME-Autostart-enabled=true\nTerminal=false\n", encoding="utf-8")
        else:
            f.unlink(missing_ok=True)
