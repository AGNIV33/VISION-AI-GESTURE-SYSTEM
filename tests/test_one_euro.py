import random

from vision_ai.gestures.one_euro import OneEuroFilter, OneEuroFilter2D


def test_first_value_passes_through():
    f = OneEuroFilter()
    assert f(5.0, 0.0) == 5.0


def test_constant_input_stays_constant():
    f = OneEuroFilter()
    out = [f(10.0, i / 30) for i in range(60)]
    assert all(abs(v - 10.0) < 1e-9 for v in out)


def test_still_hand_noise_is_reduced():
    rng = random.Random(1)
    f = OneEuroFilter(min_cutoff=1.0, beta=0.007)
    raw = [500 + rng.uniform(-3, 3) for _ in range(300)]
    out = [f(v, i / 30) for i, v in enumerate(raw)]
    spread_raw = max(raw[60:]) - min(raw[60:])
    spread_out = max(out[60:]) - min(out[60:])
    assert spread_out < spread_raw * 0.5


def test_fast_motion_has_small_lag():
    f = OneEuroFilter(min_cutoff=1.0, beta=0.007)
    out = []
    for i in range(60):  # 600 units per second ramp
        out.append(f(20.0 * i, i / 30))
    assert 20.0 * 59 - out[-1] < 120  # less than ~6 frames behind


def test_same_timestamp_does_not_crash_or_move():
    f = OneEuroFilter()
    f(1.0, 1.0)
    assert f(99.0, 1.0) == 1.0


def test_reset_forgets_history():
    f = OneEuroFilter()
    f(0.0, 0.0)
    f(0.0, 0.1)
    f.reset()
    assert f(100.0, 5.0) == 100.0


def test_2d_filter_matches_axes():
    f = OneEuroFilter2D()
    assert f(1.0, 2.0, 0.0) == (1.0, 2.0)
