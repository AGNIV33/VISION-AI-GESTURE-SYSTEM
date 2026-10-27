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


@dataclass
class GestureConfig:
    """Pinch numbers are thumb-to-finger distance divided by palm size (0 = touching).
    Starting values: tune with the pinch numbers shown in the preview."""

    pinch_on: float = 0.30  # below this = pinched
    pinch_off: float = 0.42  # above this = released (gap avoids flicker)
    arm_on: float = 0.50  # fingers getting close: freeze the cursor so the click lands still
    arm_off: float = 0.56
    arm_freeze_max_s: float = 0.25  # stop freezing if fingers hover close without pinching
    confirm_frames: int = 2  # a pinch/release must last this many pictures to count
    tap_max_s: float = 0.35  # pinch shorter than this = click
    drag_start_units: float = 30.0  # move this far while pinched = drag (box units, 1000 = box)
    drag_hold_s: float = 0.40  # or hold the pinch this long = drag
    double_click_s: float = 0.50  # second tap this soon lands on the first tap's spot
    finger_extended: float = 1.30  # tip-to-wrist / middle-joint-to-wrist above this = straight
    finger_folded: float = 1.10  # below this = curled
    scroll_gain: float = 1.8  # wheel units per box unit of hand movement (120 = one notch)
    scroll_deadband_units: float = 1.0  # ignore smaller moves per picture (noise)
    pose_exit_frames: int = 3  # pose must be gone this many pictures to end scrolling
    fist_hold_s: float = 1.5  # hold a fist this long to pause / resume
