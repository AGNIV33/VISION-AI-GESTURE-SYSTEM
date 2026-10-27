"""Which gestures are free and which need a paid plan (Phase 9).

Pure data + one helper, no Windows calls. Change the FREE flags here to change the plans.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Gesture:
    id: str
    name: str
    how: str  # one line: how to do it
    free: bool


GESTURES: tuple[Gesture, ...] = (
    Gesture("move", "Move cursor", "Open hand, move it. The cursor follows.", True),
    Gesture("tap", "Tap (click, double click)", "Touch thumb and index fingertip, release.", True),
    Gesture("scroll", "Scroll", "Peace sign (index + middle up), move hand up / down.", True),
    Gesture("pause", "Pause / resume", "Make a fist and hold it for 1.5 seconds.", True),
    Gesture("right_click", "Right click", "Touch thumb and middle fingertip.", False),
    Gesture("drag", "Drag and drop", "Pinch, hold and move, then release.", False),
    Gesture(
        "zoom", "Zoom (one hand)", "Thumb on index + middle fingertips, hand up / down.", False
    ),
    Gesture(
        "home", "Task View (Win+Tab)", "Touch thumb and ring fingertip, hold half a second.", False
    ),
    Gesture(
        "two_hand_zoom",
        "Zoom (two hands)",
        "Pinch with both hands, move them apart / closer.",
        False,
    ),
)

BY_ID = {g.id: g for g in GESTURES}

# which gesture an event from the recognizer belongs to
_EVENT_GESTURE = {
    "click_left": "tap",
    "click_right": "right_click",
    "down": "drag",
    "up": "drag",
    "scroll": "scroll",
    "hscroll": "scroll",
    "zoom": "zoom",
    "zoom2": "two_hand_zoom",
    "home": "home",
    "toggle_pause": "pause",
}


def gesture_for_event(event: tuple) -> str | None:
    kind = event[0]
    if kind == "click":
        kind = f"click_{event[1]}"
    return _EVENT_GESTURE.get(kind)


def allowed_ids(paid: bool, user_off: set[str] | frozenset[str] = frozenset()) -> set[str]:
    """Gesture ids that may run: free ones always, paid ones only on a paid plan,
    minus anything the user switched off in Settings."""
    ids = {g.id for g in GESTURES if g.free or paid}
    return (ids - set(user_off)) | {"move"}  # moving the cursor can never be switched off
