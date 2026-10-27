from vision_ai.gestures.calibrator import STEPS, Calibrator
from vision_ai.gestures.hand_pose import EXT, HandPose


def pose(idx=1.0, mid=1.0, ring=1.0):
    return HandPose(idx, mid, (EXT, EXT, EXT, EXT), ring)


def run(cal, make, fps=30):
    t = 0.0
    while not cal.done and t < 100:
        name = cal.current[0]
        cal.feed(t, make(name))
        t += 1 / fps
    return cal.result()


def good(name):
    return pose(
        idx=0.1 if name == "index" else 0.9,
        mid=0.1 if name == "middle" else 0.9,
        ring=0.1 if name == "ring" else 0.9,
    )


def test_calibration_walks_all_steps_and_gives_thresholds():
    cal = Calibrator()
    res = run(cal, good)
    assert cal.done and res.ok
    for key in ("pinch_on", "pinch_off", "arm_on", "mid_pinch_on", "ring_pinch_on"):
        assert key in res.values
    assert 0.1 < res.values["pinch_on"] < res.values["pinch_off"] < 0.9


def test_total_time_matches_the_steps():
    cal = Calibrator()
    n = 0
    t = 0.0
    while not cal.done:
        cal.feed(t, good(cal.current[0]))
        t += 1 / 30
        n += 1
    assert abs(t - sum(s[2] for s in STEPS)) < 1.0


def test_overlapping_numbers_fail_with_a_helpful_message():
    res = run(Calibrator(), lambda name: pose(idx=0.5, mid=0.5, ring=0.5))
    assert not res.ok and any("Could not tell" in ln for ln in res.lines)


def test_no_hand_at_all_fails():
    res = run(Calibrator(), lambda name: None)
    assert not res.ok


def test_unclear_ring_keeps_defaults_but_index_still_saved():
    def make(name):
        p = good(name)
        return pose(p.pinch_index, p.pinch_middle, 0.5)

    res = run(Calibrator(), make)
    assert res.ok and "ring_pinch_on" not in res.values and "pinch_on" in res.values
