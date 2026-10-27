"""Turns tracked hands into a screen position for the cursor (pure Python, no Windows calls)."""

from __future__ import annotations

from vision_ai.config.defaults import FILTER_UNITS, CursorConfig
from vision_ai.core.types import LM, Hand, HandFrame
from vision_ai.gestures.cursor_mapper import CursorMapper, DeadZone
from vision_ai.gestures.one_euro import OneEuroFilter2D


class CursorController:
    def __init__(self, mapper: CursorMapper, cfg: CursorConfig) -> None:
        self.mapper = mapper
        self.cfg = cfg
        self._filter = OneEuroFilter2D(cfg.min_cutoff, cfg.beta, cfg.d_cutoff)
        self._dead = DeadZone(cfg.dead_zone_px)
        self._last_seen: float | None = None

    def reset(self) -> None:
        self._filter.reset()
        self._dead.reset()
        self._last_seen = None

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
        # Aim at the index-finger BASE: it hardly moves when you pinch with the fingertips.
        x, y = float(hand.landmarks[LM.INDEX_MCP][0]), float(hand.landmarks[LM.INDEX_MCP][1])
        u, v = self.mapper.to_unit(x, y)
        fu, fv = self._filter(u * FILTER_UNITS, v * FILTER_UNITS, frame.t)
        sx, sy = self.mapper.unit_to_screen(fu / FILTER_UNITS, fv / FILTER_UNITS)
        return self._dead(sx, sy)
