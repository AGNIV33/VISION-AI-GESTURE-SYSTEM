from conftest import make_frame, make_hand

from vision_ai.config.defaults import CursorConfig
from vision_ai.gestures.cursor_controller import CursorController
from vision_ai.gestures.cursor_mapper import CursorMapper, Rect


def controller(**kw):
    cfg = CursorConfig(**kw)
    return CursorController(CursorMapper(Rect(*cfg.box), Rect(0, 0, 1920, 1080)), cfg)


def test_no_hand_returns_none():
    assert controller().update(make_frame(0.0)) is None


def test_hand_gives_screen_position():
    c = controller()
    x, y = c.update(make_frame(0.0, [make_hand(index_mcp=(0.5, 0.55))]))
    assert 900 < x < 1020 and 500 < y < 580


def test_main_hand_preferred_over_other_hand():
    c = controller(main_hand="right")
    left = make_hand("left", index_mcp=(0.2, 0.25))
    right = make_hand("right", index_mcp=(0.8, 0.85))
    x, y = c.update(make_frame(0.0, [left, right]))
    assert x > 1900 and y > 1060


def test_falls_back_to_other_hand_if_main_missing():
    c = controller(main_hand="right")
    assert c.update(make_frame(0.0, [make_hand("left")])) is not None


def test_still_hand_with_jitter_barely_moves_cursor():
    c = controller()
    xs = []
    for i in range(90):
        jitter = 0.002 * (1 if i % 2 else -1)  # about 3 px of camera noise
        out = c.update(make_frame(i / 30, [make_hand(index_mcp=(0.5 + jitter, 0.55))]))
        xs.append(out[0])
    assert max(xs[30:]) - min(xs[30:]) <= 2.0


def test_hand_returning_after_gap_does_not_glide_from_old_spot():
    c = controller()
    c.update(make_frame(0.0, [make_hand(index_mcp=(0.2, 0.25))]))
    x, _ = c.update(make_frame(5.0, [make_hand(index_mcp=(0.8, 0.25))]))
    assert x > 1900
