"""Local llama.cpp runtime: start, watch and stop a private server.

The server listens on 127.0.0.1 with a random free port, is started only when
a local model is selected, and is terminated when the app quits. Nothing is
downloaded or executed without an explicit click in the settings.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from voicewright.config import Config
from voicewright.models import model_path, runtime_dir
from voicewright.paths import logs_dir

log = logging.getLogger(__name__)

_BINARY_NAMES = ("llama-server", "llama-server.exe")


def _spawn_options(windows: bool | None = None) -> dict:
    """Popen options that keep the helper server invisible and detached.

    On Windows the bundled ``llama-server.exe`` must never flash a console
    window. On POSIX a new session keeps the server alive when the launcher
    exits, and lets us terminate the whole process group.
    """
    if windows is None:
        windows = sys.platform.startswith("win")
    if windows:
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    return {"start_new_session": True}


class RuntimeError_(Exception):
    pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def find_server_binary(explicit: str = "") -> Optional[Path]:
    """Locate llama-server: explicit path, bundled runtime, then system PATH."""
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file():
            return p
    root = runtime_dir()
    if root.is_dir():
        for name in _BINARY_NAMES:
            for candidate in root.rglob(name):
                if candidate.is_file():
                    return candidate
    for name in _BINARY_NAMES:
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


class LocalRuntime:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._proc: Optional[subprocess.Popen] = None
        self._port: Optional[int] = None
        self._model_id: Optional[str] = None
        self._lock = threading.Lock()
        self.last_error = ""

    # ------------------------------------------------------------------
    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def base_url(self) -> str:
        if not self._port:
            return ""
        return f"http://127.0.0.1:{self._port}/v1"

    def status(self) -> str:
        if self.running:
            return f"running on port {self._port} ({self._model_id})"
        if self.last_error:
            return f"stopped: {self.last_error}"
        return "stopped"

    # ------------------------------------------------------------------
    def _command(self, binary: Path, model_file: Path, port: int) -> list[str]:
        threads = int(self.config.get("llm_threads", 0) or 0) or max(1, min(8, os.cpu_count() or 4))
        ctx = int(self.config.get("llm_context", 2048) or 2048)
        cmd = [
            str(binary),
            "-m", str(model_file),
            "--host", "127.0.0.1",
            "--port", str(port),
            "-t", str(threads),
            "-c", str(ctx),
            "-ngl", "0",
            "--no-webui",
        ]
        if sys.platform.startswith("linux"):
            cmd += ["--no-mmap"] if self.config.get("llm_no_mmap", False) else []
        return cmd

    def _wait_ready(self, port: int, timeout: float = 90.0) -> bool:
        deadline = time.time() + timeout
        url = f"http://127.0.0.1:{port}/health"
        while time.time() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                return False
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    if r.status == 200:
                        return True
            except Exception:
                pass
            time.sleep(0.25)
        return False

    def ensure_running(self, model_id: str, binary: str = "") -> str:
        """Start the server for ``model_id`` and return its base URL."""
        with self._lock:
            if self.running and self._model_id == model_id:
                return self.base_url()
            self.stop()

            model = None
            from voicewright.models import CLEANUP_BY_ID
            model = CLEANUP_BY_ID.get(model_id)
            if model is None:
                raise RuntimeError_(f"Unknown local model: {model_id}")
            model_file = model_path(model_id) / model.files[0].name
            if not model_file.exists():
                raise RuntimeError_(f"MODEL_MISSING:{model_id}")

            exe = find_server_binary(binary)
            if exe is None:
                raise RuntimeError_("RUNTIME_MISSING")

            port = _free_port()
            cmd = self._command(exe, model_file, port)
            log.info("Starting local model: %s", " ".join(cmd[:2] + cmd[-6:]))
            logfile = logs_dir() / "llama-server.log"
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=open(logfile, "ab"),
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    **_spawn_options(),
                )
            except OSError as exc:
                raise RuntimeError_(f"Could not start llama-server: {exc}") from exc
            self._port = port
            self._model_id = model_id
            if not self._wait_ready(port):
                tail = self._log_tail(logfile)
                self.stop()
                raise RuntimeError_(f"Local model did not start. {tail}".strip())
            log.info("Local model %s ready on port %s", model_id, port)
            return self.base_url()

    def _log_tail(self, path: Path, lines: int = 4) -> str:
        try:
            data = path.read_text(encoding="utf-8", errors="replace").splitlines()
            return " | ".join(data[-lines:])
        except OSError:
            return ""

    def stop(self) -> None:
        with self._lock:
            proc, self._proc = self._proc, None
            self._port = None
            self._model_id = None
            if proc is None:
                return
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    def complete(self, model: str, system: str, user: str, timeout: float = 60.0) -> str:
        """Chat completion against the running server."""
        if not self.running:
            raise RuntimeError_("Local model is not running")
        url = f"{self.base_url()}/chat/completions"
        payload = {
            "model": model,
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 512,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Voicewright/2.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError_(f"HTTP {exc.code}") from None
        except Exception as exc:
            raise RuntimeError_("Local model request failed") from exc
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as exc:
            raise RuntimeError_(f"Unexpected response: {str(data)[:160]}") from exc
