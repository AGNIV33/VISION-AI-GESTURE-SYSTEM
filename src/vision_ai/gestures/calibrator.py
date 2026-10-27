"""Measures YOUR open-hand and pinch numbers (pure logic; the windows just show the steps)."""

from __future__ import annotations

from dataclasses import dataclass, field

from vision_ai.config import calibration
from vision_ai.gestures.hand_pose import HandPose

SETTLE_S = 1.0  # ignore the first second of each step while you change your hand

# (name, instruction, seconds)
STEPS: tuple[tuple[str, str, float], ...] = (
    ("open", "Hold your hand OPEN, fingers apart", 4.0),
    ("index", "TOUCH thumb + INDEX fingertip and hold", 4.0),
    ("open2", "OPEN your hand again", 3.0),
    ("middle", "TOUCH thumb + MIDDLE fingertip and hold", 4.0),
    ("open3", "OPEN your hand again", 3.0),
    ("ring", "TOUCH thumb + RING fingertip and hold", 4.0),
)


@dataclass
class CalibrationResult:
    ok: bool
    values: dict[str, float] = field(default_factory=dict)
    lines: list[str] = field(default_factory=list)  # what to show / print


def _range_line(label: str, vals: list[float]) -> str:
    if not vals:
        return f"{label}: no hand seen"
    s = sorted(vals)
    return (
        f"{label}: lowest {s[0]:.2f}, most between {s[len(s) // 10]:.2f}-"
        f"{s[(len(s) * 9) // 10]:.2f}, highest {s[-1]:.2f}"
    )


class Calibrator:
    def __init__(self, steps=STEPS, settle_s: float = SETTLE_S) -> None:
        self.steps = steps
        self.settle_s = settle_s
        self._i = 0
        self._t0: float | None = None
        self._vals: dict[str, list[HandPose]] = {name: [] for name, _, _ in steps}

    @property
    def done(self) -> bool:
        return self._i >= len(self.steps)

    @property
    def index(self) -> int:
        return self._i

    @property
    def current(self) -> tuple[str, str, float] | None:
        return None if self.done else self.steps[self._i]

    def seconds_left(self, t: float) -> float:
        if self.done or self._t0 is None:
            return 0.0
        return max(self.steps[self._i][2] - (t - self._t0), 0.0)

    def feed(self, t: float, pose: HandPose | None) -> None:
        """Call for every tracked picture (pose=None when no hand is visible)."""
        if self.done:
            return
        if self._t0 is None:
            self._t0 = t
        name, _, secs = self.steps[self._i]
        elapsed = t - self._t0
        if pose is not None and elapsed > self.settle_s:
            self._vals[name].append(pose)
        if elapsed >= secs:
            self._i += 1
            self._t0 = None

    def result(self) -> CalibrationResult:
        v = self._vals

        def col(names: tuple[str, ...], attr: str) -> list[float]:
            return [getattr(p, attr) for n in names if n in v for p in v[n]]

        opens = ("open", "open2", "open3")
        o_idx, o_mid, o_ring = (
            col(opens, a) for a in ("pinch_index", "pinch_middle", "pinch_ring")
        )
        p_idx, p_mid, p_ring = (
            col(("index",), "pinch_index"),
            col(("middle",), "pinch_middle"),
            col(("ring",), "pinch_ring"),
        )
        lines = [
            _range_line("open hand (thumb-index)", o_idx),
            _range_line("index pinch (thumb-index)", p_idx),
            _range_line("open hand (thumb-middle)", o_mid),
            _range_line("middle pinch (thumb-middle)", p_mid),
            _range_line("open hand (thumb-ring)", o_ring),
            _range_line("ring pinch (thumb-ring)", p_ring),
        ]
        idx = calibration.thresholds(o_idx, p_idx)
        if idx is None:
            lines.append(
                "Could not tell your open hand from your pinch. Use better light, keep your "
                "hand inside the box, and try again."
            )
            return CalibrationResult(False, {}, lines)
        values = {"pinch_on": idx[0], "pinch_off": idx[1], "arm_on": idx[2], "arm_off": idx[3]}
        mid = calibration.thresholds(o_mid, p_mid)
        if mid is not None:
            values.update({"mid_pinch_on": mid[0], "mid_pinch_off": mid[1]})
        else:
            lines.append("Middle-finger pinch was unclear: right click keeps the default numbers.")
        ring = calibration.thresholds(o_ring, p_ring)
        if ring is not None:
            values.update({"ring_pinch_on": ring[0], "ring_pinch_off": ring[1]})
        else:
            lines.append("Ring-finger pinch was unclear: Task View keeps the default numbers.")
        lines.append(f"Click when thumb-index is below {idx[0]:.2f}, release above {idx[1]:.2f}.")
        return CalibrationResult(True, {k: round(x, 3) for k, x in values.items()}, lines)
