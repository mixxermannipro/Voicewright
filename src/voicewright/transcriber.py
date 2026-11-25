"""Facade over the speech engines, chosen by the selected model."""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from voicewright.config import Config
from voicewright.engines import (EngineError, SherpaEngine, WhisperEngine,
                                 sherpa_available)
from voicewright.models import ALL_BY_ID, is_downloaded

log = logging.getLogger(__name__)


class TranscriberError(EngineError):
    pass


class Transcriber:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.whisper = WhisperEngine(config)
        self.sherpa = SherpaEngine(config)

    # ------------------------------------------------------------------
    def model_id(self) -> str:
        return self.config.get("speech_model") or self.config.get("whisper_model") or ""

    def engine_for(self, model_id: Optional[str] = None):
        model_id = model_id or self.model_id()
        model = ALL_BY_ID.get(model_id)
        if model is None:
            raise TranscriberError(f"UNKNOWN_MODEL:{model_id}")
        preferred = self.config.get("speech_engine", "auto")
        if model.kind == "sherpa":
            if preferred == "whisper":
                raise TranscriberError(f"MODEL_ENGINE_MISMATCH:{model_id}")
            if not sherpa_available():
                raise TranscriberError("SHERPA_MISSING")
            return self.sherpa
        return self.whisper

    # ------------------------------------------------------------------
    def load(self) -> None:
        model_id = self.model_id()
        if not is_downloaded(model_id):
            raise TranscriberError(f"MODEL_MISSING:{model_id}")
        self.engine_for(model_id).load(model_id)

    def unload(self) -> None:
        self.whisper.unload()
        self.sherpa.unload()

    @property
    def loaded_info(self) -> str:
        return self.whisper.loaded_info

    # ------------------------------------------------------------------
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> tuple[str, str]:
        if audio is None or audio.size < sample_rate * 0.2:
            return "", ""
        model_id = self.model_id()
        if not is_downloaded(model_id):
            raise TranscriberError(f"MODEL_MISSING:{model_id}")
        engine = self.engine_for(model_id)
        engine.load(model_id)
        return engine.transcribe(audio, sample_rate)

    # ------------------------------------------------------------------
    def candidates(self) -> list[str]:
        """Downloaded models that can actually run right now, best first."""
        out: list[str] = []
        for mid, model in ALL_BY_ID.items():
            if not is_downloaded(mid):
                continue
            if model.engine == "sherpa-onnx" and not sherpa_available():
                continue
            out.append(mid)
        return out
