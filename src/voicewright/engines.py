"""Speech engines: sherpa-onnx (Parakeet, SenseVoice) and faster-whisper.

Both are optional at import time. A missing package produces a clear error
instead of a crash, so the app can keep running and tell the user what to
install.
"""
from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

from voicewright.config import Config
from voicewright.models import ALL_BY_ID, is_downloaded, model_path

log = logging.getLogger(__name__)


class EngineError(Exception):
    pass


def _threads() -> int:
    return max(1, min(4, os.cpu_count() or 4))


def cuda_available() -> bool:
    try:
        import ctranslate2  # type: ignore
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# sherpa-onnx
# ---------------------------------------------------------------------------
_sherpa_preloaded = False


def preload_sherpa() -> None:
    """Make bundled onnxruntime libraries findable.

    Some wheels put the extension module and the shared libraries in different
    directories (notably inside virtual environments with both ``lib`` and
    ``lib64``). Loading them with ``RTLD_GLOBAL`` before the import fixes the
    lookup without touching system paths.
    """
    global _sherpa_preloaded
    if _sherpa_preloaded:
        return
    _sherpa_preloaded = True
    if sys.platform.startswith("win"):
        candidates = [Path(p) / "sherpa_onnx" / "lib" for p in sys.path if p]
        for d in candidates:
            if d.is_dir():
                try:
                    os.add_dll_directory(str(d))  # type: ignore[attr-defined]
                except (AttributeError, OSError):
                    pass
        return
    if not sys.platform.startswith("linux"):
        return
    names = ("libonnxruntime.so", "libsherpa-onnx-c-api.so", "libsherpa-onnx-cxx-api.so")
    for entry in sys.path:
        d = Path(entry or ".") / "sherpa_onnx" / "lib"
        if not d.is_dir():
            continue
        for name in names:
            p = d / name
            if p.exists():
                try:
                    ctypes.CDLL(str(p), mode=ctypes.RTLD_GLOBAL)
                except OSError as exc:
                    log.debug("Could not preload %s: %s", p, exc)


def sherpa_available() -> bool:
    try:
        preload_sherpa()
        import sherpa_onnx  # noqa: F401
        return True
    except Exception as exc:  # noqa: BLE001
        log.debug("sherpa-onnx unavailable: %s", exc)
        return False


class SherpaEngine:
    """Offline recogniser for Parakeet and SenseVoice ONNX models."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._recognizer = None
        self._loaded_id: Optional[str] = None
        self._lock = threading.Lock()

    def load(self, model_id: Optional[str] = None) -> None:
        model_id = model_id or self.config.get("speech_model")
        if self._recognizer is not None and self._loaded_id == model_id:
            return
        model = ALL_BY_ID.get(model_id)
        if model is None or model.kind != "sherpa":
            raise EngineError(f"Not a sherpa model: {model_id}")
        if not is_downloaded(model_id):
            raise EngineError(f"MODEL_MISSING:{model_id}")
        if not sherpa_available():
            raise EngineError("sherpa-onnx is not installed. Install the 'asr' extra.")

        preload_sherpa()
        import sherpa_onnx  # type: ignore

        root = model_path(model_id)
        files = {f.name: str(root / f.name) for f in model.files}
        t0 = time.time()
        with self._lock:
            if model_id == "sensevoice":
                recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                    model=files["model.int8.onnx"],
                    tokens=files["tokens.txt"],
                    num_threads=_threads(),
                    language=self._sense_language(),
                    use_itn=True,
                )
            else:
                # Parakeet is a NeMo TDT export: it needs the NeMo transducer
                # implementation and 128-dimensional features. Without these
                # two flags sherpa-onnx aborts while reading the decoder.
                recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                    encoder=files["encoder.int8.onnx"],
                    decoder=files["decoder.int8.onnx"],
                    joiner=files["joiner.int8.onnx"],
                    tokens=files["tokens.txt"],
                    num_threads=_threads(),
                    decoding_method="greedy_search",
                    sample_rate=16000,
                    feature_dim=128,
                    model_type="nemo_transducer",
                )
            self._recognizer = recognizer
            self._loaded_id = model_id
        log.info("Loaded %s in %.1fs", model_id, time.time() - t0)

    def _sense_language(self) -> str:
        lang = self.config.get("language", "auto")
        if lang in ("auto", "", None):
            return ""
        return lang

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> tuple[str, str]:
        if audio is None or audio.size == 0:
            return "", ""
        self.load()
        assert self._recognizer is not None
        data = np.ascontiguousarray(audio, dtype=np.float32)
        if sample_rate != 16000:
            data = _resample(data, sample_rate, 16000)
        with self._lock:
            stream = self._recognizer.create_stream()
            stream.accept_waveform(16000, data)
            self._recognizer.decode_stream(stream)
            result = stream.result
        text = (getattr(result, "text", "") or "").strip()
        lang = getattr(result, "lang", "") or self.config.get("language", "")
        if lang == "auto":
            lang = ""
        return text, lang

    def unload(self) -> None:
        with self._lock:
            self._recognizer = None
            self._loaded_id = None


def _resample(audio: np.ndarray, src: int, dst: int) -> np.ndarray:
    if src == dst or audio.size == 0:
        return audio
    duration = audio.size / src
    n = int(round(duration * dst))
    x_old = np.linspace(0.0, duration, num=audio.size, endpoint=False)
    x_new = np.linspace(0.0, duration, num=n, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


# ---------------------------------------------------------------------------
# faster-whisper
# ---------------------------------------------------------------------------
class WhisperEngine:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._model = None
        self._loaded_key: Optional[tuple] = None
        self._lock = threading.Lock()

    def _resolve_device(self) -> tuple[str, str]:
        device = self.config.get("whisper_device", "auto")
        compute = self.config.get("whisper_compute_type", "auto")
        if device == "auto":
            device = "cuda" if cuda_available() else "cpu"
        if compute == "auto":
            compute = "float16" if device == "cuda" else "int8"
        return device, compute

    def load(self, model_id: Optional[str] = None) -> None:
        model_id = model_id or self.config.get("speech_model")
        if not is_downloaded(model_id):
            raise EngineError(f"MODEL_MISSING:{model_id}")
        device, compute = self._resolve_device()
        key = (model_id, device, compute)
        with self._lock:
            if self._model is not None and self._loaded_key == key:
                return
            self._model = None
            try:
                from faster_whisper import WhisperModel  # type: ignore
            except Exception as exc:  # noqa: BLE001
                raise EngineError(f"faster-whisper is not installed: {exc}") from exc
            t0 = time.time()
            try:
                self._model = WhisperModel(str(model_path(model_id)), device=device,
                                           compute_type=compute)
            except Exception as exc:
                if device == "cuda":
                    log.warning("CUDA load failed (%s) – falling back to CPU/int8", exc)
                    self._model = WhisperModel(str(model_path(model_id)), device="cpu",
                                               compute_type="int8")
                    key = (model_id, "cpu", "int8")
                else:
                    raise EngineError(str(exc)) from exc
            self._loaded_key = key
            log.info("Loaded Whisper %s on %s/%s in %.1fs", model_id, key[1], key[2],
                     time.time() - t0)

    def unload(self) -> None:
        with self._lock:
            self._model = None
            self._loaded_key = None

    @property
    def loaded_info(self) -> str:
        if not self._loaded_key:
            return ""
        return f"{self._loaded_key[0]} ({self._loaded_key[1]}, {self._loaded_key[2]})"

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> tuple[str, str]:
        if audio is None or audio.size < sample_rate * 0.2:
            return "", ""
        self.load()
        lang = self.config.get("language", "auto")
        dictionary = [w for w in self.config.get("custom_dictionary", []) if w.strip()]
        prompt = (self.config.get("initial_prompt") or "").strip()
        if dictionary:
            prompt = (prompt + " " + ", ".join(dictionary)).strip()
        t0 = time.time()
        try:
            text, info = self._run(audio, lang, prompt)
        except Exception as exc:
            if self._loaded_key and self._loaded_key[1] == "cuda":
                log.warning("GPU transcription failed (%s) – retrying on CPU", exc)
                with self._lock:
                    from faster_whisper import WhisperModel  # type: ignore
                    mid = self._loaded_key[0]
                    self._model = WhisperModel(str(model_path(mid)), device="cpu",
                                               compute_type="int8")
                    self._loaded_key = (mid, "cpu", "int8")
                self.config.set("whisper_device", "cpu")
                text, info = self._run(audio, lang, prompt)
            else:
                raise EngineError(str(exc)) from exc
        log.info("Transcribed %.1fs audio in %.1fs (lang=%s)",
                 audio.size / sample_rate, time.time() - t0,
                 getattr(info, "language", "?"))
        if not self.config.get("keep_model_loaded", True):
            self.unload()
        return text, getattr(info, "language", "") or ""

    def _run(self, audio: np.ndarray, lang: str, prompt: str):
        with self._lock:
            assert self._model is not None
            segments, info = self._model.transcribe(
                audio.astype(np.float32),
                language=None if lang == "auto" else lang,
                task=self.config.get("whisper_task", "transcribe"),
                beam_size=int(self.config.get("beam_size", 5)),
                vad_filter=bool(self.config.get("vad_filter", True)),
                vad_parameters={"min_silence_duration_ms": 500},
                initial_prompt=prompt or None,
                condition_on_previous_text=False,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
        return text, info
