"""Per-user pinch thresholds measured by `python -m vision_ai --calibrate`."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import replace
from pathlib import Path

from vision_ai.config.defaults import GestureConfig

log = logging.getLogger(__name__)

MIN_GAP = 0.15  # open and pinched numbers must differ at least this much


def data_dir() -> Path:
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "VisionAI"
    return Path.home() / ".vision_ai"


def calibration_path() -> Path:
    return data_dir() / "calibration.json"


def _percentile(values: list[float], q: float) -> float:
    s = sorted(values)
    k = min(len(s) - 1, max(0, round(q * (len(s) - 1))))
    return s[k]


def thresholds(open_vals: list[float], pinch_vals: list[float]) -> tuple[float, ...] | None:
    """From measured numbers: (on, off, arm_on, arm_off), or None if they overlap.

    Uses the 90th percentile of pinched values and the 10th percentile of open values,
    so a few bad pictures do not spoil it."""
    if len(open_vals) < 10 or len(pinch_vals) < 10:
        return None
    lo = _percentile(pinch_vals, 0.9)
    hi = _percentile(open_vals, 0.1)
    gap = hi - lo
    if gap < MIN_GAP:
        return None
    return (lo + 0.30 * gap, lo + 0.50 * gap, lo + 0.65 * gap, lo + 0.75 * gap)


def save(values: dict[str, float]) -> Path:
    path = calibration_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(values, indent=2), encoding="utf-8")
    return path


def load_gesture_config(base: GestureConfig | None = None) -> tuple[GestureConfig, bool]:
    """Default gesture settings with the saved calibration applied (if any)."""
    cfg = base or GestureConfig()
    path = calibration_path()
    if not path.is_file():
        return cfg, False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        allowed = {k: float(v) for k, v in data.items() if hasattr(cfg, k)}
        return replace(cfg, **allowed), True
    except (OSError, ValueError, TypeError) as exc:
        log.warning("ignoring broken calibration file %s: %s", path, exc)
        return cfg, False
