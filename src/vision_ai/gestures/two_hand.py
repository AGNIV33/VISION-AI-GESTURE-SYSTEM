"""Two-hand zoom: pinch with BOTH hands, move them apart (zoom in) or closer (zoom out).

Pure logic. While it is active the one-hand gestures are paused (two-hand wins).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vision_ai.config.defaults import GestureConfig
from vision_ai.gestures.hand_pose import HandPose

LOST_FRAMES = 6  # one hand may vanish this many pictures before the zoom ends


@dataclass
class TwoHandOutput:
    active: bool = False
    events: list[tuple] = field(default_factory=list)


class TwoHandZoom:
    def __init__(self, cfg: GestureConfig | None = None) -> None:
        self.cfg = cfg or GestureConfig()
        self.reset()

    def reset(self) -> None:
        self.active = False
        self._on = 0
        self._off = 0
        self._lost = 0
        self._prev: float | None = None
        self._acc = 0.0

    def update(self, poses: tuple[HandPose, HandPose] | None, dist: float | None) -> TwoHandOutput:
        """`dist` = distance between the two hands in picture-height units x 1000."""
        c = self.cfg
        events: list[tuple] = []
        if poses is None or dist is None:
            if self.active:
                self._lost += 1
                if self._lost >= LOST_FRAMES:
                    self.reset()
            else:
                self._on = 0
            return TwoHandOutput(self.active, events)
        self._lost = 0
        both_on = all(p.pinch_index < c.pinch_on for p in poses)
        either_off = any(p.pinch_index > c.pinch_off for p in poses)
        if not self.active:
            self._on = self._on + 1 if both_on else 0
            if self._on >= c.two_hand_confirm_frames:
                self.active, self._prev, self._acc, self._off = True, dist, 0.0, 0
        else:
            self._off = self._off + 1 if either_off else 0
            if self._off >= c.pose_exit_frames:
                self.reset()
                return TwoHandOutput(False, events)
            if self._prev is not None:
                self._acc += (dist - self._prev) * c.two_hand_gain  # apart = zoom in
            self._prev = dist
            whole = int(self._acc)
            if whole:
                events.append(("zoom2", whole))
                self._acc -= whole
        return TwoHandOutput(self.active, events)
