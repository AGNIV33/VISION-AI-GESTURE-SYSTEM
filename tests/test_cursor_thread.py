import ctypes
import time

from vision_ai.actions.cursor_thread import CursorSmoother, CursorThread
from vision_ai.actions.win_input import INPUT, abs_coords
from vision_ai.config.defaults import CursorConfig
from vision_ai.gestures.cursor_mapper import Rect


def test_smoother_snaps_to_first_target():
    s = CursorSmoother(0.025, 0.0, 0.06)
    s.set_target(100, 200, 0.0)
    assert s.step(0.0) == (100, 200)


def test_smoother_glides_toward_new_target():
    s = CursorSmoother(0.025, 0.0, 0.06)
    s.set_target(0, 0, 0.0)
    s.step(0.0)
    s.set_target(100, 0, 0.033)
    x1 = s.step(0.0083)[0]
    x2 = s.step(0.0166)[0]
    x3 = s.step(0.0249)[0]
    assert 0 < x1 < x2 < x3 < 100


def test_smoother_reaches_target_when_still():
    s = CursorSmoother(0.025, 0.5, 0.06)
    s.set_target(0, 0, 0.0)
    s.set_target(100, 0, 0.033)
    p = None
    for i in range(1, 200):
        p = s.step(0.033 + i * 0.0083)
    assert abs(p[0] - 100) < 1.5  # prediction fades out, so it settles ON the target


def test_prediction_is_capped():
    s = CursorSmoother(0.0, 1.0, 0.05)  # tau 0 = jump straight to predicted point
    s.set_target(0, 0, 0.0)
    s.set_target(100, 0, 0.1)  # velocity about 500/s (after smoothing)
    s.step(0.1)
    ahead = s.step(0.1 + 0.05)[0]  # 50 ms after the last target: prediction at its cap
    assert 100 < ahead <= 100 + 600 * 0.05
    assert abs(s.step(10.0)[0] - 100) < 1e-6  # very old: no prediction left


def test_thread_moves_cursor_to_target_and_stops_sending_when_still():
    moves = []
    t = CursorThread(lambda x, y: moves.append((x, y)), CursorConfig(rate_hz=200))
    t.start()
    try:
        t.set_target(300, 400, time.monotonic())
        time.sleep(0.3)
        assert moves and moves[-1] == (300, 400)
        n = len(moves)
        time.sleep(0.1)
        assert len(moves) == n  # no repeated identical moves
    finally:
        t.stop()
        t.join(1)


def test_thread_does_nothing_when_disabled():
    moves = []
    t = CursorThread(lambda x, y: moves.append((x, y)), CursorConfig(rate_hz=200))
    t.enabled = False
    t.start()
    try:
        t.set_target(10, 10, time.monotonic())
        time.sleep(0.1)
        assert moves == []
    finally:
        t.stop()
        t.join(1)


def test_abs_coords_edges_and_negative_origin():
    screen = Rect(-1920, 0, 3840, 1080)
    assert abs_coords(-1920, 0, screen) == (0, 0)
    assert abs_coords(1919, 1079, screen) == (65535, 65535)
    assert abs_coords(-5000, -5, screen) == (0, 0)  # clamped


def test_input_struct_size_matches_windows():
    # 40 bytes on 64-bit Windows, 28 on 32-bit
    assert ctypes.sizeof(INPUT) in (40, 28)
