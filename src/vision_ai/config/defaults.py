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
    # Large box, clear of the picture edges where tracking gets shaky.
    box: tuple[float, float, float, float] = (0.15, 0.08, 0.70, 0.70)
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
    smoother_tau_s: float = 0.012
    predict_gain: float = 0.5  # 0 = no prediction
    max_predict_s: float = 0.06
    # Trackpad mode (relative movement with acceleration)
    trackpad_accel: float = 1.2  # extra gain at fast hand speed (0 = none)
    trackpad_ref_speed: float = 600.0  # box units / second where acceleration is half-way


FILTER_UNITS = 1000.0


@dataclass
class GestureConfig:
    """Pinch numbers are thumb-to-finger distance divided by palm size (0 = touching).
    Starting values: tune with the pinch numbers shown in the preview."""

    pinch_on: float = 0.30  # below this = pinched
    pinch_off: float = 0.42  # above this = released (gap avoids flicker)
    mid_pinch_on: float = 0.30  # same, for thumb + middle finger (right click)
    mid_pinch_off: float = 0.42
    arm_on: float = 0.50  # fingers getting close: freeze the cursor so the click lands still
    arm_off: float = 0.56
    arm_freeze_max_s: float = 0.25  # stop freezing if fingers hover close without pinching
    confirm_frames: int = 2  # a pinch/release must last this many pictures to count
    tap_max_s: float = 0.70  # pinch shorter than this = click
    drag_start_units: float = 70.0  # move this far while pinched = drag (box units, 1000 = box)
    drag_hold_s: float = 0.80  # or hold the pinch this long = drag
    double_click_s: float = 0.50  # second tap this soon lands on the first tap's spot
    finger_extended: float = 1.30  # tip-to-wrist / middle-joint-to-wrist above this = straight
    finger_folded: float = 1.10  # below this = curled
    scroll_gain: float = 1.8  # wheel units per box unit of hand movement (120 = one notch)
    scroll_deadband_units: float = 0.3  # ignore smaller moves per picture (noise)
    zoom_gain: float = 2.4  # wheel units per box unit of hand movement (up = zoom in)
    zoom_confirm_frames: int = 4  # thumb on index+middle this long before zoom starts
    pose_exit_frames: int = 6  # pose must be gone this many pictures to end scrolling
    fist_hold_s: float = 1.5  # hold a fist this long to pause / resume
    ring_pinch_on: float = 0.30  # thumb + ring finger (Task View)
    ring_pinch_off: float = 0.42
    home_hold_s: float = 0.50  # hold the ring pinch this long to open Task View
    scroll_inertia_tau_s: float = 0.35  # after you stop scrolling it coasts and fades
    scroll_inertia_min_v: float = 240.0  # wheel units / second needed to start coasting
    scroll_inertia_stop_v: float = 25.0
    two_hand_gain: float = 1.6  # wheel units per box unit change of the distance between hands
    two_hand_confirm_frames: int = 3
