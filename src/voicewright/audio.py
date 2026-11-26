"""Microphone capture (16 kHz mono float32) and short UI feedback sounds."""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000

try:
    import sounddevice as sd  # type: ignore
except Exception as exc:  # pragma: no cover
    sd = None
    log.error("sounddevice unavailable: %s", exc)


class AudioError(Exception):
    pass


def list_input_devices() -> list[str]:
    if sd is None:
        return []
    names: list[str] = []
    try:
        for dev in sd.query_devices():
            if dev.get("max_input_channels", 0) > 0 and dev["name"] not in names:
                names.append(dev["name"])
    except Exception as exc:
        log.warning("Could not list devices: %s", exc)
    return names


def device_index(name: Optional[str]) -> Optional[int]:
    """Public wrapper used by the setup assistant's level test."""
    return _device_index(name)


def _device_index(name: Optional[str]) -> Optional[int]:
    if not name or sd is None:
        return None
    try:
        for i, dev in enumerate(sd.query_devices()):
            if dev["name"] == name and dev.get("max_input_channels", 0) > 0:
                return i
    except Exception:
        pass
    return None


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int = SAMPLE_RATE) -> np.ndarray:
    if src_rate == dst_rate or audio.size == 0:
        return audio
    duration = audio.size / src_rate
    n = int(round(duration * dst_rate))
    x_old = np.linspace(0.0, duration, num=audio.size, endpoint=False)
    x_new = np.linspace(0.0, duration, num=n, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def trim_silence(audio: np.ndarray, threshold: float = 0.008, pad: float = 0.25) -> np.ndarray:
    if audio.size == 0:
        return audio
    win = int(SAMPLE_RATE * 0.02)
    n = audio.size // win
    if n == 0:
        return audio
    rms = np.sqrt(np.mean(audio[: n * win].reshape(n, win) ** 2, axis=1))
    voiced = np.where(rms > threshold)[0]
    if voiced.size == 0:
        return audio[:0]
    p = int(pad * SAMPLE_RATE)
    start = max(0, voiced[0] * win - p)
    end = min(audio.size, (voiced[-1] + 1) * win + p)
    return audio[start:end]


class Recorder:
    """Records from the microphone into memory. Thread-safe start/stop."""

    def __init__(self, level_callback: Optional[Callable[[float], None]] = None) -> None:
        self._chunks: list[np.ndarray] = []
        self._stream = None
        self._lock = threading.Lock()
        self._rate = SAMPLE_RATE
        self.level_callback = level_callback
        self.recording = False

    def start(self, device_name: Optional[str] = None) -> None:
        if sd is None:
            raise AudioError("sounddevice/PortAudio is not available")
        with self._lock:
            if self.recording:
                return
            self._chunks = []
            dev = _device_index(device_name)
            rate = SAMPLE_RATE
            stream = None
            try:
                try:
                    sd.check_input_settings(device=dev, samplerate=SAMPLE_RATE, channels=1, dtype="float32")
                except Exception:
                    info = sd.query_devices(dev, "input") if dev is not None else sd.query_devices(kind="input")
                    rate = int(info["default_samplerate"])
                stream = sd.InputStream(
                    samplerate=rate, channels=1, dtype="float32", device=dev,
                    blocksize=int(rate * 0.05), callback=self._callback,
                )
                stream.start()
            except Exception as exc:
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                raise AudioError(str(exc)) from exc
            self._rate = rate
            self._stream = stream
            self.recording = True

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        mono = indata[:, 0].copy()
        self._chunks.append(mono)
        if self.level_callback is not None:
            try:
                self.level_callback(float(np.sqrt(np.mean(mono ** 2))))
            except Exception:
                pass

    def stop(self) -> np.ndarray:
        with self._lock:
            if not self.recording:
                return np.zeros(0, dtype=np.float32)
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
            self.recording = False
            audio = np.concatenate(self._chunks) if self._chunks else np.zeros(0, dtype=np.float32)
            self._chunks = []
        return _resample(audio, self._rate)

    def cancel(self) -> None:
        self.stop()


# ---------------------------------------------------------------------------
# Feedback sounds (generated, no asset files needed)
# ---------------------------------------------------------------------------
def _tone(freqs: list[float], dur: float = 0.07, volume: float = 0.18, rate: int = 44100) -> np.ndarray:
    parts = []
    for f in freqs:
        t = np.linspace(0, dur, int(rate * dur), endpoint=False)
        env = np.minimum(1.0, np.minimum(t / 0.008, (dur - t) / 0.02))
        parts.append((np.sin(2 * np.pi * f * t) * env * volume).astype(np.float32))
    return np.concatenate(parts)


_SOUNDS = {
    "start": [660.0, 880.0],
    "stop": [880.0, 660.0],
    "error": [300.0, 220.0],
    "cancel": [440.0, 330.0],
}


def play_sound(kind: str) -> None:
    if sd is None or kind not in _SOUNDS:
        return

    def _play() -> None:
        try:
            sd.play(_tone(_SOUNDS[kind]), 44100, blocking=False)
        except Exception as exc:
            log.debug("sound failed: %s", exc)

    threading.Thread(target=_play, daemon=True).start()
