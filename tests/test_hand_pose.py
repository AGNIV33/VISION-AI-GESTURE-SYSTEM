import numpy as np

from vision_ai.config.defaults import GestureConfig
from vision_ai.core.types import Hand
from vision_ai.gestures.hand_pose import EXT, FOLD, read_pose


def hand_with(fingers_straight):
    """Wrist at origin, fingers pointing up (-y). Straight = tip far, curled = tip near."""
    w = np.zeros((21, 3), np.float32)
    w[9] = (0, -0.09, 0)
    w[4] = (-0.06, -0.08, 0)  # thumb tip
    for k, (j, t) in enumerate(((6, 8), (10, 12), (14, 16), (18, 20))):
        x = 0.02 * k
        w[j] = (x, -0.12, 0)
        w[t] = (x, -0.18, 0) if fingers_straight[k] else (x, -0.08, 0)
    return Hand(side="right", landmarks=np.zeros((21, 3), np.float32), world=w, score=1.0)


def test_open_hand_all_fingers_straight():
    p = read_pose(hand_with([1, 1, 1, 1]), GestureConfig())
    assert p.fingers == (EXT, EXT, EXT, EXT) and not p.is_fist and not p.is_scroll_pose


def test_fist_all_curled():
    p = read_pose(hand_with([0, 0, 0, 0]), GestureConfig())
    assert p.fingers == (FOLD, FOLD, FOLD, FOLD) and p.is_fist


def test_peace_sign_is_scroll_pose():
    assert read_pose(hand_with([1, 1, 0, 0]), GestureConfig()).is_scroll_pose
