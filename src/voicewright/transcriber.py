"""Local speech-to-text with faster-whisper (CTranslate2). Fully offline."""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import numpy as np

from voicewright.config import Config
from voicewright.models import is_downloaded, model_path

log = logging.getLogger(__name__)


class TranscriberError(Exception):
    pass


def cuda_available() -> bool:
    try:
        import ctranslate2  # type: ignore
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


class Transcriber:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._model = None
        self._loaded_key: Optional[tuple] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def _resolve_device(self) -> tuple[str, str]:
        device = self.config.get("whisper_device", "auto")
        compute = self.config.get("whisper_compute_type", "auto")
        if device == "auto":
            device = "cuda" if cuda_available() else "cpu"
        if compute == "auto":
            compute = "float16" if device == "cuda" else "int8"
        return device, compute

    def load(self) -> None:
        model_id = self.config.get("whisper_model")
        if not is_downloaded(model_id):
            raise TranscriberError(f"MODEL_MISSING:{model_id}")
        device, compute = self._resolve_device()
        key = (model_id, device, compute)
        with self._lock:
            if self._model is not None and self._loaded_key == key:
                return
            self._model = None
            try:
                from faster_whisper import WhisperModel  # type: ignore
            except Exception as exc:
                raise TranscriberError(f"faster-whisper is not installed: {exc}") from exc
            t0 = time.time()
            try:
                self._model = WhisperModel(str(model_path(model_id)), device=device, compute_type=compute)
            except Exception as exc:
                if device == "cuda":
                    log.warning("CUDA load failed (%s) – falling back to CPU/int8", exc)
                    self._model = WhisperModel(str(model_path(model_id)), device="cpu", compute_type="int8")
                    key = (model_id, "cpu", "int8")
                else:
                    raise TranscriberError(str(exc)) from exc
            self._loaded_key = key
            log.info("Loaded Whisper model %s on %s/%s in %.1fs", model_id, key[1], key[2], time.time() - t0)

    def unload(self) -> None:
        with self._lock:
            self._model = None
            self._loaded_key = None

    @property
    def loaded_info(self) -> str:
        if not self._loaded_key:
            return ""
        return f"{self._loaded_key[0]} ({self._loaded_key[1]}, {self._loaded_key[2]})"

    # ------------------------------------------------------------------
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> tuple[str, str]:
        """Return (text, detected_language)."""
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
            # Typical case: CUDA visible but cuBLAS/cuDNN libraries missing.
            if self._loaded_key and self._loaded_key[1] == "cuda":
                log.warning("GPU transcription failed (%s) – retrying on CPU", exc)
                with self._lock:
                    from faster_whisper import WhisperModel  # type: ignore
                    mid = self._loaded_key[0]
                    self._model = WhisperModel(str(model_path(mid)), device="cpu", compute_type="int8")
                    self._loaded_key = (mid, "cpu", "int8")
                self.config.set("whisper_device", "cpu")
                text, info = self._run(audio, lang, prompt)
            else:
                raise TranscriberError(str(exc)) from exc
        log.info("Transcribed %.1fs audio in %.1fs (lang=%s)",
                 audio.size / sample_rate, time.time() - t0, getattr(info, "language", "?"))
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
            # segments is a lazy generator – the actual decoding happens here
            text = " ".join(seg.text.strip() for seg in segments).strip()
        return text, info
