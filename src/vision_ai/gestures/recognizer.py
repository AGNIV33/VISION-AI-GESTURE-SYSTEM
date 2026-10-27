"""Gesture state machine (pure logic, no Windows calls, no clock).

Each picture: pose + hand position in, gesture state + events out.

Events:
    ("click", "left" | "right")   ("down", "left")   ("up", "left")
    ("scroll", delta)   ("hscroll", delta)   (120 = one wheel notch)
    ("toggle_pause",)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from vision_ai.config.defaults import GestureConfig
from vision_ai.gestures.hand_pose import HandPose

IDLE = "move"
ARMED = "pinch?"
PINCHED = "pinched"
DRAG = "drag"
RIGHT = "right click"
SCROLL = "scroll"
FIST = "fist (hold to pause)"
FIST_DONE = "fist"

Event = tuple


@dataclass
class GestureOutput:
    state: str
    freeze: bool = False  # hold the cursor still
    snap_to_last_click: bool = False  # hold it on the last click spot (double click)
    events: list[Event] = field(default_factory=list)


class GestureRecognizer:
    def __init__(self, cfg: GestureConfig | None = None) -> None:
        self.cfg = cfg or GestureConfig()
        self._last_click_t = -math.inf
        self.reset()

    def reset(self) -> None:
        self.state = IDLE
        self._t_enter = 0.0
        self._down_t = 0.0
        self._pos0 = (0.0, 0.0)
        self._last_pos: tuple[float, float] | None = None
        self._idx_on = self._idx_off = self._mid_on = self._mid_off = 0
        self._pose_off = 0
        self._acc = [0.0, 0.0]
        self._snap = False

    def _go(self, state: str, t: float) -> None:
        self.state = state
        self._t_enter = t
        if state == IDLE:
            self._snap = False

    def update(
        self, pose: HandPose | None, pos: tuple[float, float] | None, t: float
    ) -> GestureOutput:
        c = self.cfg
        events: list[Event] = []

        if pose is None or pos is None:  # hand lost: never leave the button stuck down
            if self.state == DRAG:
                events.append(("up", "left"))
            self.reset()
            return GestureOutput(IDLE, events=events)

        # count how many pictures in a row each pinch has been on / off
        self._idx_on = self._idx_on + 1 if pose.pinch_index < c.pinch_on else 0
        self._idx_off = self._idx_off + 1 if pose.pinch_index > c.pinch_off else 0
        self._mid_on = self._mid_on + 1 if pose.pinch_middle < c.pinch_on else 0
        self._mid_off = self._mid_off + 1 if pose.pinch_middle > c.pinch_off else 0
        n = c.confirm_frames
        right_pinch = self._mid_on >= n and pose.pinch_index > c.pinch_off

        s = self.state
        if s == IDLE:
            if pose.is_fist:
                self._go(FIST, t)
            elif pose.is_scroll_pose:
                self._go(SCROLL, t)
                self._last_pos = pos
                self._acc = [0.0, 0.0]
                self._pose_off = 0
            elif right_pinch:
                self._go(RIGHT, t)
            elif pose.pinch_index < c.arm_on:
                self._go(ARMED, t)
                self._snap = (t - self._last_click_t) < c.double_click_s

        elif s == ARMED:
            if self._idx_on >= n:
                self._go(PINCHED, t)
                self._down_t = t
                self._pos0 = pos
            elif right_pinch:
                self._go(RIGHT, t)
            elif pose.pinch_index > c.arm_off:
                self._go(IDLE, t)

        elif s == PINCHED:
            if self._idx_off >= n:
                if t - self._down_t <= c.tap_max_s:
                    events.append(("click", "left"))
                    self._last_click_t = t
                self._go(IDLE, t)
            elif (
                math.dist(pos, self._pos0) > c.drag_start_units or t - self._down_t > c.drag_hold_s
            ):
                events.append(("down", "left"))
                self._go(DRAG, t)

        elif s == DRAG:
            if self._idx_off >= n:
                events.append(("up", "left"))
                self._go(IDLE, t)

        elif s == RIGHT:
            if self._mid_off >= n:
                events.append(("click", "right"))
                self._go(IDLE, t)

        elif s == SCROLL:
            self._pose_off = 0 if pose.is_scroll_pose else self._pose_off + 1
            if self._pose_off >= c.pose_exit_frames:
                self._go(IDLE, t)
            elif self._last_pos is not None:
                dx = pos[0] - self._last_pos[0]
                dy = pos[1] - self._last_pos[1]
                self._last_pos = pos
                # hand up = scroll up (y grows downward); hand right = scroll right
                for i, d, sign, kind in ((0, dy, -1.0, "scroll"), (1, dx, 1.0, "hscroll")):
                    if abs(d) > c.scroll_deadband_units:
                        self._acc[i] += sign * d * c.scroll_gain
                    whole = int(self._acc[i])
                    if whole:
                        events.append((kind, whole))
                        self._acc[i] -= whole

        elif s == FIST:
            if not pose.is_fist:
                self._go(IDLE, t)
            elif t - self._t_enter >= c.fist_hold_s:
                events.append(("toggle_pause",))
                self._go(FIST_DONE, t)

        elif s == FIST_DONE:
            if not pose.is_fist:
                self._go(IDLE, t)

        st = self.state
        freeze = st in (PINCHED, RIGHT, SCROLL, FIST, FIST_DONE) or (
            st == ARMED and t - self._t_enter < c.arm_freeze_max_s
        )
        return GestureOutput(
            st, freeze=freeze, snap_to_last_click=freeze and self._snap, events=events
        )
