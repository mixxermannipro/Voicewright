"""Catalog of local Whisper (faster-whisper / CTranslate2) models and a
resumable downloader from Hugging Face that needs only the standard library."""
from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from voicewright.paths import models_dir

log = logging.getLogger(__name__)

HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
USER_AGENT = "Voicewright/1.0 (+https://github.com)"


@dataclass(frozen=True)
class WhisperModel:
    id: str
    repo: str
    size_mb: int
    languages: str          # "multi" | "en"
    speed: int              # 1 (slow) .. 5 (fast)
    accuracy: int           # 1 (low) .. 5 (high)
    recommended: str = ""   # short recommendation tag
    note: str = ""


CATALOG: list[WhisperModel] = [
    WhisperModel("tiny", "Systran/faster-whisper-tiny", 75, "multi", 5, 1,
                 note="Very fast, low accuracy. Good for testing."),
    WhisperModel("base", "Systran/faster-whisper-base", 145, "multi", 5, 2,
                 note="Fast, okay for clear speech."),
    WhisperModel("small", "Systran/faster-whisper-small", 485, "multi", 4, 3,
                 recommended="cpu",
                 note="Best balance for CPUs / laptops without GPU."),
    WhisperModel("medium", "Systran/faster-whisper-medium", 1530, "multi", 2, 4,
                 note="High accuracy, slow on CPU."),
    WhisperModel("large-v3-turbo", "mobiuslabsgmbh/faster-whisper-large-v3-turbo", 1620, "multi", 3, 5,
                 recommended="gpu",
                 note="Near large-v3 quality, ~6x faster. Best choice with GPU or fast CPU."),
    WhisperModel("large-v3", "Systran/faster-whisper-large-v3", 3090, "multi", 1, 5,
                 note="Highest accuracy, needs strong hardware."),
    WhisperModel("distil-large-v3", "Systran/faster-distil-whisper-large-v3", 1510, "en", 3, 4,
                 note="English only, fast and accurate."),
    WhisperModel("small.en", "Systran/faster-whisper-small.en", 485, "en", 4, 3,
                 note="English only small model."),
    WhisperModel("base.en", "Systran/faster-whisper-base.en", 145, "en", 5, 2,
                 note="English only base model."),
]

CATALOG_BY_ID = {m.id: m for m in CATALOG}
REQUIRED_FILES = ("model.bin", "config.json")


def model_path(model_id: str) -> Path:
    return models_dir() / model_id.replace("/", "--")


def is_downloaded(model_id: str) -> bool:
    p = model_path(model_id)
    return all((p / f).exists() for f in REQUIRED_FILES) and not (p / ".incomplete").exists()


def downloaded_models() -> list[str]:
    return [m.id for m in CATALOG if is_downloaded(m.id)]


def delete_model(model_id: str) -> None:
    p = model_path(model_id)
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)


def disk_usage_mb(model_id: str) -> float:
    p = model_path(model_id)
    if not p.exists():
        return 0.0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / (1024 * 1024)


_FALLBACK_FILES = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt",
                   "vocabulary.json", "preprocessor_config.json")
_OPTIONAL_FILES = {"vocabulary.txt", "vocabulary.json", "preprocessor_config.json", "tokenizer.json"}


class DownloadCancelled(Exception):
    pass


def _request(url: str, headers: Optional[dict] = None) -> urllib.request.Request:
    h = {"User-Agent": USER_AGENT}
    token = os.environ.get("HF_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    if headers:
        h.update(headers)
    return urllib.request.Request(url, headers=h)


def _list_repo_files(repo: str) -> list[tuple[str, int]]:
    url = f"{HF_ENDPOINT}/api/models/{repo}/tree/main"
    with urllib.request.urlopen(_request(url), timeout=30) as r:
        items = json.loads(r.read().decode("utf-8"))
    files = []
    for it in items:
        if it.get("type") != "file":
            continue
        name = it.get("path", "")
        if name.startswith(".") or name.lower().endswith((".md", ".gitattributes")):
            continue
        size = int(it.get("lfs", {}).get("size") or it.get("size") or 0)
        files.append((name, size))
    return files


def download_model(
    model_id: str,
    progress: Optional[Callable[[int, int, str], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Path:
    """Download a catalog model. `progress(done_bytes, total_bytes, filename)`."""
    model = CATALOG_BY_ID.get(model_id)
    if model is None:
        raise ValueError(f"Unknown model: {model_id}")
    target = model_path(model_id)
    target.mkdir(parents=True, exist_ok=True)
    marker = target / ".incomplete"
    marker.write_text("downloading")

    try:
        files = _list_repo_files(model.repo)
    except Exception as exc:  # API blocked -> try the well-known file set
        log.warning("Could not list repo files (%s); using default file list", exc)
        files = [(n, 0) for n in _FALLBACK_FILES]
    if not any(n == "model.bin" for n, _ in files):
        raise RuntimeError(f"Repository {model.repo} does not contain model.bin")
    total = sum(s for _, s in files) or 1
    done = 0

    for name, size in files:
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and size and dest.stat().st_size == size:
            done += size
            if progress:
                progress(done, total, name)
            continue
        part = dest.with_suffix(dest.suffix + ".part")
        existing = part.stat().st_size if part.exists() else 0
        headers = {"Range": f"bytes={existing}-"} if existing else {}
        url = f"{HF_ENDPOINT}/{model.repo}/resolve/main/{name}"
        log.info("Downloading %s", url)
        try:
            resp = urllib.request.urlopen(_request(url, headers), timeout=60)
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and name in _OPTIONAL_FILES:
                continue
            if exc.code == 416:  # range not satisfiable -> part file already complete
                part.replace(dest)
                continue
            raise
        with resp as r:
            mode = "ab" if existing and r.status == 206 else "wb"
            if mode == "wb":
                existing = 0
            done += existing
            with open(part, mode) as fh:
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise DownloadCancelled()
                    chunk = r.read(1024 * 256)
                    if not chunk:
                        break
                    fh.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total, name)
        part.replace(dest)

    marker.unlink(missing_ok=True)
    log.info("Model %s ready at %s", model_id, target)
    return target


def recommended_model() -> str:
    """Pick a sensible default based on available hardware."""
    try:
        import ctranslate2  # type: ignore
        if ctranslate2.get_cuda_device_count() > 0:
            return "large-v3-turbo"
    except Exception:
        pass
    return "small"
