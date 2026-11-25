"""Model catalog and a resumable, checksum-verified downloader.

Every file has a pinned size and SHA-256 taken from the upstream Hugging Face
or GitHub metadata. A download that does not match is deleted, never used.

Three kinds of payload:

``whisper``
    A directory of CTranslate2 files for faster-whisper.
``sherpa``
    Individual ONNX files for sherpa-onnx (Parakeet, SenseVoice).
``gguf``
    One quantised model file for llama.cpp.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import shutil
import tarfile
import threading
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from voicewright.paths import data_dir, models_dir

log = logging.getLogger(__name__)

HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
USER_AGENT = "Voicewright/2.0 (+https://github.com/voicewright)"


@dataclass(frozen=True)
class ModelFile:
    name: str
    size: int
    sha256: str = ""


@dataclass(frozen=True)
class Model:
    id: str
    kind: str                 # whisper | sherpa | gguf
    name: str
    repo: str
    files: tuple[ModelFile, ...]
    size_mb: int
    languages: str
    speed: int                # 1 (slow) .. 5 (fast)
    accuracy: int             # 1 (low) .. 5 (high)
    engine: str               # faster-whisper | sherpa-onnx | llama.cpp
    recommended: str = ""     # "default" | "cpu" | "gpu" | ""
    note: str = ""
    license: str = ""
    seconds: str = ""         # estimated time for 10 s of audio
    ram_mb: int = 0
    language_codes: tuple[str, ...] = field(default_factory=tuple)


def _w(repo: str, files: tuple[ModelFile, ...]) -> tuple[ModelFile, ...]:
    return files


# ---------------------------------------------------------------------------
# Speech recognition
# ---------------------------------------------------------------------------
PARAKEET_V3 = Model(
    id="parakeet-v3",
    kind="sherpa",
    name="Parakeet TDT 0.6B v3 (int8)",
    repo="csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",
    files=(
        ModelFile("encoder.int8.onnx", 652282294,
                  "1afbe69c1ffdabee94755f42e4daf1d93549131a3da11356bda84fcef0f2c479"),
        ModelFile("decoder.int8.onnx", 11845274,
                  "0222a86147299d4dee90edf95b6d13827edb42ad8b7c9cf0b2582f030937c0b5"),
        ModelFile("joiner.int8.onnx", 6355277,
                  "cbd02f3696e9944970111fb439d9c3fd365a80374565f13f2b9c7007d253fc98"),
        ModelFile("tokens.txt", 93939,
                  "d58544679ea4bc6ac563d1f545eb7d474bd6cfa467f0a6e2c1dc1c7d37e3c35d"),
    ),
    size_mb=675, languages="25 European", speed=5, accuracy=4,
    engine="sherpa-onnx", recommended="default", license="CC-BY-4.0",
    note="Fastest accurate model for German, English and most European languages. "
         "Runs on CPU in a fraction of real time.",
    seconds="≈0.1–0.3 s", ram_mb=900,
    language_codes=("de", "en", "fr", "es", "it", "pt", "nl", "pl", "cs", "sk",
                    "hu", "ro", "bg", "hr", "sl", "sv", "da", "no", "fi", "et",
                    "lv", "lt", "el", "mt", "ga"),
)

SENSEVOICE = Model(
    id="sensevoice",
    kind="sherpa",
    name="SenseVoice Small (int8)",
    repo="csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
    files=(
        ModelFile("model.int8.onnx", 239233841,
                  "c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51"),
        ModelFile("tokens.txt", 315894,
                  "f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc"),
    ),
    size_mb=229, languages="zh, en, ja, ko, yue", speed=5, accuracy=3,
    engine="sherpa-onnx", license="Apache-2.0",
    note="Small and fast for Chinese, Japanese, Korean and Cantonese.",
    seconds="≈0.1–0.2 s", ram_mb=500,
    language_codes=("zh", "en", "ja", "ko", "yue"),
)

_WHISPER_COMMON = (
    ModelFile("config.json", 0),
)


def _whisper_files(config_size: int, config_sha: str, model_size: int, model_sha: str,
                   tok_size: int, tok_sha: str, vocab_name: str, vocab_size: int,
                   vocab_sha: str, preprocessor: bool = False) -> tuple[ModelFile, ...]:
    files = [
        ModelFile("config.json", config_size, config_sha),
        ModelFile("model.bin", model_size, model_sha),
        ModelFile("tokenizer.json", tok_size, tok_sha),
        ModelFile(vocab_name, vocab_size, vocab_sha),
    ]
    if preprocessor:
        files.append(ModelFile("preprocessor_config.json", 340,
                               "7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711"))
    return tuple(files)


_TOK_SHA = "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"
_VOCAB_SHA = "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913"
_VOCAB_JSON_SHA = "c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1"

WHISPER_TINY = Model(
    id="whisper-tiny", kind="whisper", name="Whisper Tiny",
    repo="Systran/faster-whisper-tiny",
    files=_whisper_files(2249, "a73a28cdfe1c43ccc7202fa333d1f89c202477271407ae9a7f19afa52039cac8",
                         75538270, "dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1",
                         2203239, _TOK_SHA, "vocabulary.txt", 459861, _VOCAB_SHA),
    size_mb=75, languages="99", speed=5, accuracy=1, engine="faster-whisper",
    license="MIT", note="Very fast, low accuracy. Useful for testing.",
    seconds="≈0.2 s", ram_mb=300,
)

WHISPER_BASE = Model(
    id="whisper-base", kind="whisper", name="Whisper Base",
    repo="Systran/faster-whisper-base",
    files=_whisper_files(2309, "56a6d8110d311f19c8f0471e562832c7527f146b567275bfca59fcf7c184da9a",
                         145217532, "d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9",
                         2203239, _TOK_SHA, "vocabulary.txt", 459861, _VOCAB_SHA),
    size_mb=145, languages="99", speed=5, accuracy=2, engine="faster-whisper",
    license="MIT", note="Fast, okay for clear speech.",
    seconds="≈0.3 s", ram_mb=450,
)

WHISPER_SMALL = Model(
    id="whisper-small", kind="whisper", name="Whisper Small",
    repo="Systran/faster-whisper-small",
    files=_whisper_files(2370, "b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828",
                         483546902, "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671",
                         2203239, _TOK_SHA, "vocabulary.txt", 459861, _VOCAB_SHA),
    size_mb=485, languages="99", speed=4, accuracy=3, engine="faster-whisper",
    recommended="cpu", license="MIT",
    note="Best all-language balance for CPUs without a GPU.",
    seconds="≈0.6 s", ram_mb=900,
)

WHISPER_MEDIUM = Model(
    id="whisper-medium", kind="whisper", name="Whisper Medium",
    repo="Systran/faster-whisper-medium",
    files=_whisper_files(2257, "3622a2ddc41ec0e0fd4e68c13c6830f03b90c38d89aaad184de02c8c642cf807",
                         1527906378, "9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae",
                         2203239, _TOK_SHA, "vocabulary.txt", 459861, _VOCAB_SHA),
    size_mb=1530, languages="99", speed=2, accuracy=4, engine="faster-whisper",
    license="MIT", note="High accuracy, slow on CPU.",
    seconds="≈2.5 s", ram_mb=2500,
)

WHISPER_TURBO = Model(
    id="whisper-large-v3-turbo", kind="whisper", name="Whisper Large v3 Turbo",
    repo="mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    files=_whisper_files(2263, "b0253ea6c0d3bea6b1e19e91a02acfd3b53f4467362efcb5a3e6b16c9b3a9b7e",
                         1617884929, "e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da",
                         2710337, "297b13372ac43916285644fb9687add3cc62ee2a1adb60da3dc25cc94c1871fd",
                         "vocabulary.json", 1068114, _VOCAB_JSON_SHA, preprocessor=True),
    size_mb=1620, languages="99", speed=3, accuracy=5, engine="faster-whisper",
    recommended="gpu", license="MIT",
    note="Near large-v3 quality and about six times faster. Best with a GPU or a fast CPU.",
    seconds="≈1.2 s", ram_mb=3000,
)

WHISPER_LARGE = Model(
    id="whisper-large-v3", kind="whisper", name="Whisper Large v3",
    repo="Systran/faster-whisper-large-v3",
    files=_whisper_files(2394, "a9306624f5ec14270a014b647e5c316b6e03a662c369758d1b90697a7b0655b9",
                         3087284237, "69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1",
                         2480617, "6d8cbd7cd0d8d5815e478dac67b85a26bbe77c1f5e0c6d76d1ce2abc0e5f21ca",
                         "vocabulary.json", 1068114, _VOCAB_JSON_SHA, preprocessor=True),
    size_mb=3090, languages="99", speed=1, accuracy=5, engine="faster-whisper",
    license="MIT", note="Maximum accuracy, needs strong hardware.",
    seconds="≈4 s", ram_mb=5000,
)

CATALOG: list[Model] = [
    PARAKEET_V3, SENSEVOICE,
    WHISPER_TINY, WHISPER_BASE, WHISPER_SMALL, WHISPER_MEDIUM, WHISPER_TURBO, WHISPER_LARGE,
]
CATALOG_BY_ID = {m.id: m for m in CATALOG}


# ---------------------------------------------------------------------------
# Local cleanup models (llama.cpp GGUF)
# ---------------------------------------------------------------------------
CLEANUP_CATALOG: list[Model] = [
    Model(
        id="qwen3-0.6b-q4", kind="gguf", name="Qwen3 0.6B (Q4_K_M)",
        repo="unsloth/Qwen3-0.6B-GGUF",
        files=(ModelFile("Qwen3-0.6B-Q4_K_M.gguf", 396705472,
                         "ac2d97712095a558e31573f62f466a3f9d93990898b0ec79d7c974c1780d524a"),),
        size_mb=397, languages="multilingual", speed=5, accuracy=3,
        engine="llama.cpp", recommended="default", license="Apache-2.0",
        note="Default. Fast enough to feel instant, good at fillers, grammar and punctuation.",
        seconds="≈0.4–1.5 s", ram_mb=900,
    ),
    Model(
        id="qwen3-1.7b-q4", kind="gguf", name="Qwen3 1.7B (Q4_K_M)",
        repo="unsloth/Qwen3-1.7B-GGUF",
        files=(ModelFile("Qwen3-1.7B-Q4_K_M.gguf", 1107409472,
                         "b139949c5bd74937ad8ed8c8cf3d9ffb1e99c866c823204dc42c0d91fa181897"),),
        size_mb=1107, languages="multilingual", speed=3, accuracy=4,
        engine="llama.cpp", license="Apache-2.0",
        note="Noticeably better at restructuring and long sentences. Needs a modern CPU.",
        seconds="≈1–3 s", ram_mb=2200,
    ),
    Model(
        id="qwen3-0.6b-q8", kind="gguf", name="Qwen3 0.6B (Q8_0)",
        repo="Qwen/Qwen3-0.6B-GGUF",
        files=(ModelFile("Qwen3-0.6B-Q8_0.gguf", 639446688,
                         "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031"),),
        size_mb=639, languages="multilingual", speed=4, accuracy=3,
        engine="llama.cpp", license="Apache-2.0",
        note="Same size class, slightly better fidelity, a little slower than Q4.",
        seconds="≈0.6–2 s", ram_mb=1200,
    ),
]
CLEANUP_BY_ID = {m.id: m for m in CLEANUP_CATALOG}

ALL_MODELS = CATALOG + CLEANUP_CATALOG
ALL_BY_ID = {m.id: m for m in ALL_MODELS}


# ---------------------------------------------------------------------------
# llama.cpp runtime (downloaded on demand, never silently executed)
# ---------------------------------------------------------------------------
LLAMA_VERSION = "b12728"
LLAMA_RELEASE = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_VERSION}"

LLAMA_ASSETS: dict[str, tuple[str, int, str]] = {
    "linux-x86_64": ("llama-b12728-bin-ubuntu-x64.tar.gz", 23392294,
                     "7c8d787ff15384423d6742a42fad8e7e453d61b94a9c4cd85296e800d538b178"),
    "darwin-arm64": ("llama-b12728-bin-macos-arm64.tar.gz", 16834886,
                     "001140842db7fa5253e57f891c14db5377937faf07d955a2646b471df0e7d9bd"),
    "darwin-x86_64": ("llama-b12728-bin-macos-x64.tar.gz", 12557446,
                      "817b0faa91432ff32ccd6895a7b11a19f0d6ee57d3800c75e93c7d78265c1a9d"),
    "win32-x86_64": ("llama-b12728-bin-win-cpu-x64.zip", 25230941,
                     "a8ace09d44bb10e2617268c55c3f2db0e0adeedd9c1ba722969920665a3ae698"),
    "win32-arm64": ("llama-b12728-bin-win-cpu-arm64.zip", 13299036,
                    "c4babfa1a8ba38b7a86f3719c7254cf15b918eca81179b1a0c76a23779d3985a"),
}


def runtime_key() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        machine = "x86_64"
    elif machine in ("arm64", "aarch64"):
        machine = "arm64"
    if system == "linux":
        return f"linux-{machine}"
    if system == "darwin":
        return f"darwin-{machine}"
    if system == "windows":
        return f"win32-{machine}"
    return f"{system}-{machine}"


def runtime_asset() -> Optional[tuple[str, int, str]]:
    return LLAMA_ASSETS.get(runtime_key())


# ---------------------------------------------------------------------------
# Paths and state
# ---------------------------------------------------------------------------
def model_path(model_id: str) -> Path:
    return models_dir() / model_id.replace("/", "--")


def runtime_dir() -> Path:
    return data_dir() / "runtime" / f"llama-{LLAMA_VERSION}"


def _required_names(model: Model) -> tuple[str, ...]:
    if model.kind == "whisper":
        return ("model.bin", "config.json")
    return tuple(f.name for f in model.files)


def is_downloaded(model_id: str) -> bool:
    model = ALL_BY_ID.get(model_id)
    if model is None:
        return False
    p = model_path(model_id)
    if (p / ".incomplete").exists():
        return False
    return all((p / name).exists() and (p / name).stat().st_size > 0
               for name in _required_names(model))


def downloaded_models() -> list[str]:
    return [m.id for m in CATALOG if is_downloaded(m.id)]


def downloaded_cleanup_models() -> list[str]:
    return [m.id for m in CLEANUP_CATALOG if is_downloaded(m.id)]


def delete_model(model_id: str) -> None:
    p = model_path(model_id)
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)


def disk_usage_mb(model_id: str) -> float:
    p = model_path(model_id)
    if not p.exists():
        return 0.0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / (1024 * 1024)


def recommended_model(cuda: bool = False, sherpa: bool = False) -> str:
    """Return the recommended speech model ID for the current hardware."""
    if sherpa:
        return "parakeet-v3"
    if cuda:
        return "whisper-large-v3-turbo"
    return "whisper-small"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_model(model_id: str) -> tuple[bool, list[str]]:
    """Full hash check. Returns (ok, problems). Slow for multi-GB models."""
    model = ALL_BY_ID.get(model_id)
    if model is None:
        return False, ["unknown model"]
    problems: list[str] = []
    for f in model.files:
        path = model_path(model_id) / f.name
        if not path.exists():
            problems.append(f"{f.name}: missing")
            continue
        if f.size and path.stat().st_size != f.size:
            problems.append(f"{f.name}: size {path.stat().st_size} != {f.size}")
            continue
        if f.sha256 and _sha256(path) != f.sha256:
            problems.append(f"{f.name}: checksum mismatch")
    return not problems, problems


class DownloadCancelled(Exception):
    pass


def _request(url: str, headers: Optional[dict] = None) -> urllib.request.Request:
    h = {"User-Agent": USER_AGENT}
    token = os.environ.get("HF_TOKEN")
    if token and "huggingface.co" in url:
        h["Authorization"] = f"Bearer {token}"
    if headers:
        h.update(headers)
    return urllib.request.Request(url, headers=h)


def _download_file(url: str, dest: Path, size: int, sha256: str,
                   progress: Optional[Callable[[int, int, str], None]],
                   done_before: int, total: int, cancel_event: Optional[threading.Event]) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")

    if dest.exists() and (not size or dest.stat().st_size == size):
        if not sha256 or _sha256(dest) == sha256:
            return size or dest.stat().st_size

    existing = part.stat().st_size if part.exists() else 0
    if size and existing >= size:
        existing = 0
    headers = {"Range": f"bytes={existing}-"} if existing else {}
    try:
        resp = urllib.request.urlopen(_request(url, headers), timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code == 416:  # part already complete
            part.replace(dest)
            return size or dest.stat().st_size
        raise
    written = existing
    with resp as r:
        mode = "ab" if existing and getattr(r, "status", 200) == 206 else "wb"
        if mode == "wb":
            written = 0
        with open(part, mode) as fh:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise DownloadCancelled()
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                fh.write(chunk)
                written += len(chunk)
                if progress:
                    progress(done_before + written, total, dest.name)

    if sha256 and _sha256(part) != sha256:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum mismatch for {dest.name}")
    if size and part.stat().st_size != size:
        actual = part.stat().st_size
        part.unlink(missing_ok=True)
        raise RuntimeError(f"Size mismatch for {dest.name}: {actual} != {size}")
    part.replace(dest)
    return written


def download_model(
    model_id: str,
    progress: Optional[Callable[[int, int, str], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Path:
    """Download a catalog model. ``progress(done_bytes, total_bytes, filename)``."""
    model = ALL_BY_ID.get(model_id)
    if model is None:
        raise ValueError(f"Unknown model: {model_id}")
    target = model_path(model_id)
    target.mkdir(parents=True, exist_ok=True)
    marker = target / ".incomplete"
    marker.write_text(f"downloading {model_id}\n", encoding="utf-8")
    total = sum(f.size for f in model.files) or 1
    done = 0
    try:
        for f in model.files:
            url = f"{HF_ENDPOINT}/{model.repo}/resolve/main/{f.name}"
            log.info("Downloading %s", url)
            done += _download_file(url, target / f.name, f.size, f.sha256,
                                   progress, done, total, cancel_event)
    except BaseException:
        # Keep the marker so a partial tree is never treated as ready.
        raise
    marker.unlink(missing_ok=True)
    log.info("Model %s ready at %s", model_id, target)
    return target


# ---------------------------------------------------------------------------
# llama.cpp runtime download
# ---------------------------------------------------------------------------
def runtime_installed() -> bool:
    return any(runtime_dir().glob("llama-*")) or any(runtime_dir().glob("llama-server*"))


def download_runtime(progress: Optional[Callable[[int, int, str], None]] = None,
                     cancel_event: Optional[threading.Event] = None) -> Path:
    asset = runtime_asset()
    if asset is None:
        raise RuntimeError(f"No llama.cpp build for {runtime_key()}")
    name, size, sha = asset
    target = runtime_dir()
    target.mkdir(parents=True, exist_ok=True)
    archive = target / name
    _download_file(f"{LLAMA_RELEASE}/{name}", archive, size, sha, progress, 0, size, cancel_event)
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(target)
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(target)
    archive.unlink(missing_ok=True)
    return target
