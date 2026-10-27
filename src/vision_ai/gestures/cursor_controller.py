"""Turns tracked hands into a screen position for the cursor (pure Python, no Windows calls)."""

from __future__ import annotations

import math
from collections.abc import Callable

from vision_ai.config.defaults import FILTER_UNITS, CursorConfig
from vision_ai.core.types import Hand, HandFrame, aim_point
from vision_ai.gestures.cursor_mapper import CursorMapper, DeadZone
from vision_ai.gestures.one_euro import OneEuroFilter2D


class CursorController:
    """Absolute mode (default): the cursor sits where your hand is inside the active box.

    Trackpad mode (`trackpad_gain` given): the hand only pushes the cursor, like a touchpad,
    with extra gain on fast moves. `start_pos` says where the real cursor is, so the cursor
    never jumps when tracking starts or the hand comes back."""

    def __init__(
        self,
        mapper: CursorMapper,
        cfg: CursorConfig,
        trackpad_gain: float | None = None,
        start_pos: Callable[[], tuple[float, float]] | None = None,
    ) -> None:
        self.mapper = mapper
        self.cfg = cfg
        self.trackpad_gain = trackpad_gain
        self._start = start_pos
        self._filter = OneEuroFilter2D(cfg.min_cutoff, cfg.beta, cfg.d_cutoff)
        self._dead = DeadZone(cfg.dead_zone_px)
        self._last_seen: float | None = None
        self._rel_prev: tuple[float, float, float] | None = None
        self._rel_pos: tuple[float, float] | None = None
        self.holding = False  # trackpad mode: ignore hand movement (pinching, scrolling...)
        # filtered hand position inside the active box, 0..1000 (used by gestures)
        self.last_unit: tuple[float, float] | None = None

    def tune(self, min_cutoff: float | None = None, beta: float | None = None) -> None:
        """Change smoothing while running. Lower min_cutoff = steadier but slower;
        higher beta = less lag on fast moves."""
        if min_cutoff is not None:
            self.cfg.min_cutoff = max(0.05, min_cutoff)
        if beta is not None:
            self.cfg.beta = max(0.0, beta)
        self._filter.set_params(self.cfg.min_cutoff, self.cfg.beta)

    def reset(self) -> None:
        self._filter.reset()
        self._dead.reset()
        self._last_seen = None
        self._rel_prev = None
        self._rel_pos = None

    def pick_hand(self, frame: HandFrame) -> Hand | None:
        """Main hand if visible, otherwise the first hand seen."""
        return frame.hand(self.cfg.main_hand) or (frame.hands[0] if frame.hands else None)

    def update(self, frame: HandFrame) -> tuple[float, float] | None:
        """Returns the smoothed screen position (pixels), or None if no hand is visible."""
        hand = self.pick_hand(frame)
        if hand is None:
            return None
        if self._last_seen is not None and frame.t - self._last_seen > self.cfg.lost_timeout_s:
            self.reset()  # hand came back after a gap: do not smooth from the old spot
        self._last_seen = frame.t
        # Aim at the middle of the knuckles: steadier than one point, ignores pinching.
        x, y = aim_point(hand)
        u, v = self.mapper.to_unit(x, y)
        fu, fv = self._filter(u * FILTER_UNITS, v * FILTER_UNITS, frame.t)
        self.last_unit = (fu, fv)
        if self.trackpad_gain is not None:
            sx, sy = self._relative(fu, fv, frame.t)
        else:
            sx, sy = self.mapper.unit_to_screen(fu / FILTER_UNITS, fv / FILTER_UNITS)
        return self._dead(sx, sy)

    def _relative(self, fu: float, fv: float, t: float) -> tuple[float, float]:
        scr = self.mapper.screen
        if self._rel_prev is None or self._rel_pos is None:
            self._rel_prev = (fu, fv, t)
            self._rel_pos = (
                self._start()
                if self._start
                else (scr.left + scr.width / 2, scr.top + scr.height / 2)
            )
            return self._rel_pos
        pu, pv, pt = self._rel_prev
        self._rel_prev = (fu, fv, t)
        if self.holding:
            return self._rel_pos
        du, dv = fu - pu, fv - pv
        speed = math.hypot(du, dv) / max(t - pt, 1e-3)  # box units / second
        k = speed / (speed + self.cfg.trackpad_ref_speed)  # 0 slow ... ~1 fast
        gain = (self.trackpad_gain or 1.0) * (1.0 + self.cfg.trackpad_accel * k)
        x = self._rel_pos[0] + du / FILTER_UNITS * scr.width * gain
        y = self._rel_pos[1] + dv / FILTER_UNITS * scr.height * gain
        x = min(max(x, scr.left), scr.left + scr.width - 1)
        y = min(max(y, scr.top), scr.top + scr.height - 1)
        self._rel_pos = (x, y)
        return self._rel_pos
