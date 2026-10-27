"""One Euro Filter (Casiez, Roussel, Vogel 2012).

Strong smoothing when the signal moves slowly (no shake), little smoothing when it
moves fast (no lag).
"""

from __future__ import annotations

import math


def _alpha(cutoff: float, dt: float) -> float:
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self) -> None:
        self._t: float | None = None
        self._x_raw = 0.0
        self._x_hat = 0.0
        self._dx_hat = 0.0

    def __call__(self, x: float, t: float) -> float:
        if self._t is None:
            self._t, self._x_raw, self._x_hat, self._dx_hat = t, x, x, 0.0
            return x
        dt = t - self._t
        if dt <= 0.0:
            return self._x_hat
        dx = (x - self._x_raw) / dt
        a_d = _alpha(self.d_cutoff, dt)
        self._dx_hat += a_d * (dx - self._dx_hat)
        cutoff = self.min_cutoff + self.beta * abs(self._dx_hat)
        a = _alpha(cutoff, dt)
        self._x_hat += a * (x - self._x_hat)
        self._x_raw = x
        self._t = t
        return self._x_hat


class OneEuroFilter2D:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self._fx = OneEuroFilter(min_cutoff, beta, d_cutoff)
        self._fy = OneEuroFilter(min_cutoff, beta, d_cutoff)

    def reset(self) -> None:
        self._fx.reset()
        self._fy.reset()

    def set_params(self, min_cutoff: float, beta: float) -> None:
        for f in (self._fx, self._fy):
            f.min_cutoff = min_cutoff
            f.beta = beta

    def __call__(self, x: float, y: float, t: float) -> tuple[float, float]:
        return self._fx(x, t), self._fy(y, t)
