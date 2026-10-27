"""Active box (camera view) -> screen position, plus a small dead zone."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    left: float
    top: float
    width: float
    height: float


def _clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v


class CursorMapper:
    """`box` is in mirrored camera coordinates (0..1). `screen` is the virtual desktop
    in pixels (its left/top can be negative with monitors to the left/above)."""

    def __init__(self, box: Rect, screen: Rect) -> None:
        self.box = box
        self.screen = screen

    def to_unit(self, x: float, y: float) -> tuple[float, float]:
        """Camera point -> position inside the active box, 0..1 (clamped)."""
        u = (x - self.box.left) / self.box.width
        v = (y - self.box.top) / self.box.height
        return _clamp01(u), _clamp01(v)

    def unit_to_screen(self, u: float, v: float) -> tuple[float, float]:
        sx = self.screen.left + _clamp01(u) * (self.screen.width - 1)
        sy = self.screen.top + _clamp01(v) * (self.screen.height - 1)
        return sx, sy


class DeadZone:
    """Ignore tiny moves. When the target leaves the zone, the output follows it at the
    zone's edge (so there is no sudden jump)."""

    def __init__(self, radius_px: float) -> None:
        self.radius = radius_px
        self._pos: tuple[float, float] | None = None

    def reset(self) -> None:
        self._pos = None

    def __call__(self, x: float, y: float) -> tuple[float, float]:
        if self._pos is None:
            self._pos = (x, y)
            return self._pos
        px, py = self._pos
        d = math.hypot(x - px, y - py)
        if d <= self.radius:
            return self._pos
        k = (d - self.radius) / d
        self._pos = (px + (x - px) * k, py + (y - py) * k)
        return self._pos
