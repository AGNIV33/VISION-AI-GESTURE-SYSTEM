"""All tunable numbers live here (see AGENTS.md). Values are STARTING points:
they are not tuned yet and must be adjusted on real hardware."""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass
class CameraConfig:
    index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    # "msmf" gave 32 fps on the owner's PC vs 9.8 fps with "dshow" (2026-10-27).
    # If msmf cannot open the camera, open_camera falls back to dshow.
    backend: str = "msmf" if sys.platform == "win32" else "auto"
    mirror: bool = True  # mirrored view: moving your hand right moves the cursor right


@dataclass
class TrackerConfig:
    # 1 hand is much faster: with 2, MediaPipe keeps searching for a second hand on
    # every picture while only one is visible. Two-hand gestures (Phase 4) will need 2.
    num_hands: int = 1
    min_detection_confidence: float = 0.5
    min_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    # Pictures wider than this are shrunk before tracking. MediaPipe shrinks them
    # internally anyway, so this only removes wasted work.
    input_width: int = 640


@dataclass
class CursorConfig:
    # Active box in mirrored camera coordinates (0..1): left, top, width, height.
    # Lower-middle of the view so the arm can rest.
    box: tuple[float, float, float, float] = (0.20, 0.25, 0.60, 0.60)
    main_hand: str = "right"
    # One Euro filter. Applied in "box units" (0..1000 across the active box),
    # so the feel does not depend on screen resolution.
    min_cutoff: float = 1.0
    beta: float = 0.05  # was 0.007: owner found it too laggy (2026-10-27)
    d_cutoff: float = 1.0
    dead_zone_px: float = 2.0
    lost_timeout_s: float = 0.3  # no hand for this long -> forget the old position
    # High-rate cursor mover (runs faster than the camera).
    rate_hz: float = 120.0
    smoother_tau_s: float = 0.025
    predict_gain: float = 0.5  # 0 = no prediction
    max_predict_s: float = 0.06


FILTER_UNITS = 1000.0
