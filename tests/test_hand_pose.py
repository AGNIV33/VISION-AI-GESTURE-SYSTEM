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
    lm = w + np.array([0.5, 0.6, 0.0], np.float32)  # same shape in the picture
    return Hand(side="right", landmarks=lm, world=w, score=1.0)


def test_open_hand_all_fingers_straight():
    p = read_pose(hand_with([1, 1, 1, 1]), GestureConfig())
    assert p.fingers == (EXT, EXT, EXT, EXT) and not p.is_fist and not p.is_scroll_pose


def test_fist_all_curled():
    p = read_pose(hand_with([0, 0, 0, 0]), GestureConfig())
    assert p.fingers == (FOLD, FOLD, FOLD, FOLD) and p.is_fist


def test_peace_sign_is_scroll_pose():
    assert read_pose(hand_with([1, 1, 0, 0]), GestureConfig()).is_scroll_pose


def test_pinch_uses_flat_picture_distance_not_noisy_depth():
    h = hand_with([1, 1, 1, 1])
    lm = h.landmarks.copy()
    lm[8, :2] = lm[4, :2]  # index tip on top of thumb tip in the picture
    world = h.world.copy()
    world[8, 2] = 0.05  # but MediaPipe's depth guess says 5 cm apart
    p = read_pose(Hand("right", lm, world, 1.0), GestureConfig())
    assert p.pinch_index < 0.05


def test_wide_picture_shape_is_respected():
    h = hand_with([1, 1, 1, 1])
    lm = h.landmarks.copy()
    lm[8, :2] = lm[4, :2] + np.array([0.03, 0.0])  # gap only along x
    narrow = read_pose(Hand("right", lm, h.world, 1.0, aspect=1.0), GestureConfig())
    wide = read_pose(Hand("right", lm, h.world, 1.0, aspect=16 / 9), GestureConfig())
    assert wide.pinch_index > narrow.pinch_index
