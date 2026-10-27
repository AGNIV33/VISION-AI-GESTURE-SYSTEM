"""Trackpad mode and two-hand zoom."""

from conftest import make_frame, make_hand

from vision_ai.config.defaults import CursorConfig, GestureConfig
from vision_ai.gestures.cursor_controller import CursorController
from vision_ai.gestures.cursor_mapper import CursorMapper, Rect
from vision_ai.gestures.hand_pose import EXT, HandPose
from vision_ai.gestures.two_hand import TwoHandZoom

SCREEN = Rect(0, 0, 1920, 1080)


def trackpad(gain=1.0, start=(300.0, 400.0)):
    cfg = CursorConfig()
    return CursorController(
        CursorMapper(Rect(*cfg.box), SCREEN), cfg, trackpad_gain=gain, start_pos=lambda: start
    )


def feed(c, x, y, i):
    return c.update(make_frame(i / 30, [make_hand(index_mcp=(x, y))]))


def test_trackpad_starts_where_the_real_cursor_is():
    c = trackpad(start=(300.0, 400.0))
    x, y = feed(c, 0.5, 0.4, 0)
    assert (round(x), round(y)) == (300, 400)


def test_trackpad_moves_by_hand_movement_not_hand_position():
    c = trackpad()
    for i in range(10):
        pos = feed(c, 0.5, 0.4, i)
    for i in range(10, 40):  # hand moves right 0.1 of the picture
        pos = feed(c, 0.5 + 0.1 * (i - 9) / 30, 0.4, i)
    assert pos[0] > 300 + 100 and abs(pos[1] - 400) < 5


def test_trackpad_faster_hand_goes_farther_per_distance():
    def travel(frames):
        c = trackpad()
        feed(c, 0.5, 0.4, 0)
        for i in range(1, frames + 1):
            pos = feed(c, 0.5 + 0.1 * i / frames, 0.4, i)
        return pos[0] - 300

    assert travel(6) > travel(60) * 1.15  # same distance, fast vs slow


def test_trackpad_hold_keeps_cursor_still_and_does_not_jump_after():
    c = trackpad()
    for i in range(5):
        feed(c, 0.5, 0.4, i)
    before = feed(c, 0.5, 0.4, 5)
    c.holding = True
    for i in range(6, 20):  # hand wanders while pinching
        held = feed(c, 0.5 + 0.01 * (i - 5), 0.4, i)
    assert held == before
    c.holding = False
    after = feed(c, 0.5 + 0.01 * 15, 0.4, 20)
    assert abs(after[0] - before[0]) < 60  # one normal step, not the whole wander (~300 px)


def test_trackpad_stays_inside_the_screen():
    c = trackpad(gain=5.0)
    feed(c, 0.2, 0.4, 0)
    for i in range(1, 30):
        pos = feed(c, 0.2 + 0.6 * i / 29, 0.4, i)
    assert 0 <= pos[0] <= 1919


def test_trackpad_hand_back_after_gap_starts_at_real_cursor():
    c = trackpad(start=(900.0, 500.0))
    feed(c, 0.5, 0.4, 0)
    pos = c.update(make_frame(5.0, [make_hand(index_mcp=(0.8, 0.7))]))
    assert (round(pos[0]), round(pos[1])) == (900, 500)


# --- two-hand zoom ---------------------------------------------------------------------


def pinch(v):
    return HandPose(pinch_index=v, pinch_middle=1.0, fingers=(EXT, EXT, EXT, EXT))


def run(th, dists, v=0.1):
    events = []
    out = None
    for d in dists:
        out = th.update((pinch(v), pinch(v)), d)
        events += out.events
    return out, events


def test_two_hand_zoom_apart_zooms_in_closer_zooms_out():
    th = TwoHandZoom(GestureConfig())
    out, ev = run(th, [300.0] * 5)
    assert out.active and ev == []
    out, ev = run(th, [300.0 + 10 * i for i in range(1, 20)])
    assert ev and all(e[0] == "zoom2" and e[1] > 0 for e in ev)
    out, ev = run(th, [490.0 - 10 * i for i in range(1, 20)])
    assert ev and all(e[1] < 0 for e in ev)


def test_two_hand_zoom_needs_both_hands_pinched():
    th = TwoHandZoom(GestureConfig())
    for d in [300.0] * 10:
        out = th.update((pinch(0.1), pinch(0.9)), d)
    assert not out.active


def test_two_hand_zoom_ends_when_a_hand_opens_or_disappears():
    th = TwoHandZoom(GestureConfig())
    run(th, [300.0] * 5)
    out, _ = run(th, [300.0] * 8, v=0.9)
    assert not out.active
    th2 = TwoHandZoom(GestureConfig())
    run(th2, [300.0] * 5)
    for _ in range(10):
        out = th2.update(None, None)
    assert not out.active


def test_a_hand_may_vanish_for_a_moment_without_ending_the_zoom():
    th = TwoHandZoom(GestureConfig())
    run(th, [300.0] * 5)
    for _ in range(3):
        out = th.update(None, None)
    assert out.active
