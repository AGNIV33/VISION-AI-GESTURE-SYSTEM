"""Gesture state machine (pure logic, no Windows calls, no clock).

Each picture: pose + hand position in, gesture state + events out.

Events:
    ("click", "left" | "right")   ("down", "left")   ("up", "left")
    ("scroll", delta)   ("hscroll", delta)   ("zoom", delta)   ("home",)   (120 = one wheel notch)
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
ZOOM = "zoom"
HOME = "task view (hold)"
HOME_DONE = "task view"
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
        self._both = 0
        self._zoomed = False
        self._ring_on = self._ring_off = 0
        self._scroll_v = [0.0, 0.0]  # wheel units / second, last good value while scrolling
        self._inertia = [0.0, 0.0]
        self._last_t = 0.0

    def _go(self, state: str, t: float) -> None:
        self.state = state
        self._t_enter = t
        if state == IDLE:
            self._snap = False

    def _coast(self, dt: float) -> list[Event]:
        """Scrolling keeps rolling for a moment after you stop, and fades out."""
        c = self.cfg
        out: list[Event] = []
        if max(abs(v) for v in self._inertia) < c.scroll_inertia_stop_v:
            self._inertia = [0.0, 0.0]
            return out
        decay = math.exp(-dt / c.scroll_inertia_tau_s)
        for i, kind in ((0, "scroll"), (1, "hscroll")):
            self._acc[i] += self._inertia[i] * dt
            self._inertia[i] *= decay
            whole = int(self._acc[i])
            if whole:
                out.append((kind, whole))
                self._acc[i] -= whole
        return out

    def _start_zoom(self, pos: tuple[float, float], t: float) -> None:
        self._go(ZOOM, t)
        self._last_pos = pos
        self._acc = [0.0, 0.0]
        self._zoomed = False

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
        self._mid_on = self._mid_on + 1 if pose.pinch_middle < c.mid_pinch_on else 0
        self._mid_off = self._mid_off + 1 if pose.pinch_middle > c.mid_pinch_off else 0
        n = c.confirm_frames
        self._ring_on = self._ring_on + 1 if pose.pinch_ring < c.ring_pinch_on else 0
        self._ring_off = self._ring_off + 1 if pose.pinch_ring > c.ring_pinch_off else 0
        ring_pinch = (
            self._ring_on >= n
            and pose.pinch_index > c.pinch_off
            and pose.pinch_middle > c.mid_pinch_off
        )
        dt = max(t - self._last_t, 1e-3) if self._last_t else 1 / 30
        self._last_t = t
        # zoom pose: thumb touching BOTH index and middle fingertips
        both = pose.pinch_index < c.pinch_on and pose.pinch_middle < c.mid_pinch_on
        self._both = self._both + 1 if both else 0
        zoom_start = self._both >= c.zoom_confirm_frames
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
                self._scroll_v = [0.0, 0.0]
                self._inertia = [0.0, 0.0]
            elif zoom_start:
                self._start_zoom(pos, t)
            elif right_pinch:
                self._go(RIGHT, t)
            elif ring_pinch:
                self._go(HOME, t)
            elif pose.pinch_index < c.arm_on:
                self._go(ARMED, t)
                self._snap = (t - self._last_click_t) < c.double_click_s

        elif s == ARMED:
            if zoom_start:
                self._start_zoom(pos, t)
            elif self._idx_on >= n:
                self._go(PINCHED, t)
                self._down_t = t
                self._pos0 = pos
            elif right_pinch:
                self._go(RIGHT, t)
            elif pose.pinch_index > c.arm_off:
                self._go(IDLE, t)

        elif s == PINCHED:
            if zoom_start:  # a pinch that turns out to be the zoom pose (before any drag)
                self._start_zoom(pos, t)
            elif self._idx_off >= n:
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
            self._pose_off = 0 if pose.keeps_scroll_pose else self._pose_off + 1
            if self._pose_off >= c.pose_exit_frames:
                if max(abs(v) for v in self._scroll_v) >= c.scroll_inertia_min_v:
                    self._inertia = list(self._scroll_v)
                    self._acc = [0.0, 0.0]
                self._go(IDLE, t)
            elif self._last_pos is not None:
                dx = pos[0] - self._last_pos[0]
                dy = pos[1] - self._last_pos[1]
                self._last_pos = pos
                # hand up = scroll up (y grows downward); hand right = scroll right
                for i, d, sign, kind in ((0, dy, -1.0, "scroll"), (1, dx, 1.0, "hscroll")):
                    step = sign * d * c.scroll_gain if abs(d) > c.scroll_deadband_units else 0.0
                    self._acc[i] += step
                    if self._pose_off == 0:  # speed of the hand while the pose is clean
                        self._scroll_v[i] += 0.4 * (step / dt - self._scroll_v[i])
                    whole = int(self._acc[i])
                    if whole:
                        events.append((kind, whole))
                        self._acc[i] -= whole

        elif s == ZOOM:
            if self._idx_off >= c.pose_exit_frames or self._mid_off >= c.pose_exit_frames:
                if not self._zoomed and t - self._t_enter <= c.tap_max_s:
                    events.append(("click", "left"))  # it was only a tap: do not lose it
                    self._last_click_t = t
                self._go(IDLE, t)
            elif self._last_pos is not None:
                dy = pos[1] - self._last_pos[1]
                self._last_pos = pos
                if abs(dy) > c.scroll_deadband_units:
                    self._acc[0] += -dy * c.zoom_gain  # hand up = zoom in
                whole = int(self._acc[0])
                if whole:
                    events.append(("zoom", whole))
                    self._acc[0] -= whole
                    self._zoomed = True

        elif s == HOME:
            if self._ring_off >= n:
                self._go(IDLE, t)
            elif t - self._t_enter >= c.home_hold_s:
                events.append(("home",))
                self._go(HOME_DONE, t)

        elif s == HOME_DONE:
            if self._ring_off >= n:
                self._go(IDLE, t)

        elif s == FIST:
            if not pose.is_fist:
                self._go(IDLE, t)
            elif t - self._t_enter >= c.fist_hold_s:
                events.append(("toggle_pause",))
                self._go(FIST_DONE, t)

        elif s == FIST_DONE:
            if not pose.is_fist:
                self._go(IDLE, t)

        if self.state == IDLE:
            events += self._coast(dt)
        else:
            self._inertia = [0.0, 0.0]
        st = self.state
        freeze = st in (PINCHED, RIGHT, SCROLL, ZOOM, HOME, HOME_DONE, FIST, FIST_DONE) or (
            st == ARMED and t - self._t_enter < c.arm_freeze_max_s
        )
        return GestureOutput(
            st, freeze=freeze, snap_to_last_click=freeze and self._snap, events=events
        )
