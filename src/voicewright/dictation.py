"""Hybrid dictation gestures: one shortcut, two behaviours, no mode switch.

The machine is pure logic with an injectable clock so it can be tested without
a keyboard, a display server or real time.

Gestures
--------
``hybrid`` (default)
    Press  -> recording starts immediately.
    Release before ``tap_threshold_ms`` -> it was a tap, recording continues.
    Next press -> recording stops.
    Release after ``tap_threshold_ms`` -> it was a hold, recording stops.
    Escape -> discard.

``toggle``
    Press starts, next press stops. Releases are ignored.

``hold``
    Press starts, release stops. A release before ``min_hold_ms`` discards the
    take because it is almost always an accidental brush of the shortcut.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

IDLE = "idle"
RECORDING = "recording"

# Actions reported to the controller
START = "start"
STOP = "stop"
CANCEL = "cancel"
NONE = ""


class DictationMachine:
    def __init__(
        self,
        mode: str = "hybrid",
        tap_threshold_ms: int = 350,
        min_hold_ms: int = 250,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.mode = mode if mode in ("hybrid", "toggle", "hold") else "hybrid"
        self.tap_threshold_ms = max(150, min(900, int(tap_threshold_ms)))
        self.min_hold_ms = max(50, int(min_hold_ms))
        self._clock = clock
        self.state = IDLE
        self.tapped = False          # hybrid: a tap opened the recording
        self._pressed_at: Optional[float] = None
        self.on_start: Optional[Callable[[], None]] = None
        self.on_stop: Optional[Callable[[], None]] = None
        self.on_cancel: Optional[Callable[[], None]] = None
        self.last_action = NONE

    # ------------------------------------------------------------------
    def configure(self, mode: Optional[str] = None, tap_threshold_ms: Optional[int] = None,
                  min_hold_ms: Optional[int] = None) -> None:
        if mode in ("hybrid", "toggle", "hold"):
            self.mode = mode
        if tap_threshold_ms is not None:
            self.tap_threshold_ms = max(150, min(900, int(tap_threshold_ms)))
        if min_hold_ms is not None:
            self.min_hold_ms = max(50, int(min_hold_ms))

    @property
    def recording(self) -> bool:
        return self.state == RECORDING

    @property
    def held_seconds(self) -> float:
        if self._pressed_at is None:
            return 0.0
        return max(0.0, self._clock() - self._pressed_at)

    # ------------------------------------------------------------------
    def key_down(self) -> str:
        """Shortcut pressed. Returns the action taken."""
        now = self._clock()
        if self.state == IDLE:
            self.state = RECORDING
            self.tapped = False
            self._pressed_at = now
            return self._emit(START)

        # Already recording.
        if self.mode == "toggle":
            self._pressed_at = now
            return self._stop()
        if self.mode == "hold":
            # Key repeat or a second press while holding: ignore.
            return NONE
        # hybrid
        if self.tapped:
            self.tapped = False
            self._pressed_at = now
            return self._stop()
        # Still holding from the first press (key repeat): ignore.
        return NONE

    def key_up(self) -> str:
        """Shortcut released. Returns the action taken."""
        if self.state != RECORDING:
            return NONE
        held = self.held_seconds
        self._pressed_at = None
        if self.mode == "toggle":
            return NONE
        if self.mode == "hold":
            if held * 1000 < self.min_hold_ms:
                return self._cancel()
            return self._stop()
        # hybrid
        if held * 1000 < self.tap_threshold_ms:
            # Tap: keep recording until the next press.
            self.tapped = True
            return NONE
        self.tapped = False
        return self._stop()

    def escape(self) -> str:
        if self.state == RECORDING:
            return self._cancel()
        return NONE

    def reset(self) -> None:
        self.state = IDLE
        self.tapped = False
        self._pressed_at = None
        self.last_action = NONE

    # ------------------------------------------------------------------
    def _stop(self) -> str:
        self.state = IDLE
        self.tapped = False
        self._pressed_at = None
        return self._emit(STOP)

    def _cancel(self) -> str:
        self.state = IDLE
        self.tapped = False
        self._pressed_at = None
        return self._emit(CANCEL)

    def _emit(self, action: str) -> str:
        self.last_action = action
        callback = {START: self.on_start, STOP: self.on_stop, CANCEL: self.on_cancel}.get(action)
        if callback is not None:
            callback()
        return action
