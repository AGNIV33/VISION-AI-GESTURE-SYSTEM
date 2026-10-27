"""High-rate cursor mover.

The camera gives ~30 positions per second. This thread moves the real cursor ~120 times
per second, gliding toward the newest position (with a little prediction), so motion
looks smoother than the camera rate.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable

from vision_ai.config.defaults import CursorConfig


class CursorSmoother:
    """Pure logic (no threads, no clock) so it can be tested."""

    def __init__(self, tau_s: float, predict_gain: float, max_predict_s: float) -> None:
        self.tau = tau_s
        self.gain = predict_gain
        self.max_predict = max_predict_s
        self._target: tuple[float, float] | None = None
        self._target_t = 0.0
        self._vel = (0.0, 0.0)
        self._pos: tuple[float, float] | None = None
        self._step_t: float | None = None

    @property
    def position(self) -> tuple[float, float] | None:
        return self._pos

    def set_target(self, x: float, y: float, t: float) -> None:
        if self._target is not None and t > self._target_t:
            dt = t - self._target_t
            vx, vy = (x - self._target[0]) / dt, (y - self._target[1]) / dt
            # light smoothing of the speed estimate so noise does not become overshoot
            self._vel = (
                self._vel[0] + 0.5 * (vx - self._vel[0]),
                self._vel[1] + 0.5 * (vy - self._vel[1]),
            )
        self._target = (x, y)
        self._target_t = t

    def clear(self) -> None:
        self._target = None
        self._vel = (0.0, 0.0)

    def step(self, now: float) -> tuple[float, float] | None:
        if self._target is None:
            return self._pos
        age = max(now - self._target_t, 0.0)
        # Predict ahead for up to `max_predict` seconds. If no new position arrives for
        # longer (hand lost or stopped), fade the prediction out so the cursor settles ON
        # the last target instead of staying ahead of it.
        if age > self.max_predict:
            age = max(2.0 * self.max_predict - age, 0.0)
        tx = self._target[0] + self._vel[0] * age * self.gain
        ty = self._target[1] + self._vel[1] * age * self.gain
        if self._pos is None or self._step_t is None:
            self._pos = (tx, ty)
        else:
            dt = max(now - self._step_t, 0.0)
            a = 1.0 - math.exp(-dt / self.tau) if self.tau > 0 else 1.0
            self._pos = (
                self._pos[0] + (tx - self._pos[0]) * a,
                self._pos[1] + (ty - self._pos[1]) * a,
            )
        self._step_t = now
        return self._pos


class CursorThread(threading.Thread):
    def __init__(
        self,
        mover: Callable[[int, int], None],
        cfg: CursorConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(name="cursor", daemon=True)
        self._mover = mover
        self._period = 1.0 / cfg.rate_hz
        self._clock = clock
        self._lock = threading.Lock()
        self._smoother = CursorSmoother(cfg.smoother_tau_s, cfg.predict_gain, cfg.max_predict_s)
        self._stop_evt = threading.Event()
        self.enabled = True
        self.error: str | None = None

    def set_target(self, x: float, y: float, t: float) -> None:
        with self._lock:
            self._smoother.set_target(x, y, t)

    def stop(self) -> None:
        self._stop_evt.set()

    def run(self) -> None:
        last: tuple[int, int] | None = None
        next_tick = self._clock()
        while not self._stop_evt.is_set():
            now = self._clock()
            if self.enabled:
                with self._lock:
                    pos = self._smoother.step(now)
                if pos is not None:
                    cur = (round(pos[0]), round(pos[1]))
                    if cur != last:
                        try:
                            self._mover(*cur)
                        except OSError as exc:
                            self.error = f"Cannot move the cursor: {exc}"
                            return
                        last = cur
            else:
                with self._lock:
                    self._smoother.clear()
                last = None
            next_tick += self._period
            delay = next_tick - self._clock()
            if delay > 0:
                time.sleep(delay)
            else:
                next_tick = self._clock()  # fell behind: do not try to catch up
