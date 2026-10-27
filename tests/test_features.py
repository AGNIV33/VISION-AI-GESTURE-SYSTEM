from conftest import make_hand

from vision_ai.gestures.features import palm_size, pinch_ratio


def test_touching_fingers_give_zero():
    assert pinch_ratio(make_hand(thumb_index_gap=0.0)) < 1e-6


def test_ratio_is_gap_divided_by_palm():
    assert abs(pinch_ratio(make_hand(thumb_index_gap=0.045, palm=0.09)) - 0.5) < 1e-5


def test_same_pinch_near_and_far_gives_same_number():
    near = make_hand(thumb_index_gap=0.06, palm=0.12)
    far = make_hand(thumb_index_gap=0.03, palm=0.06)
    assert abs(pinch_ratio(near) - pinch_ratio(far)) < 1e-5


def test_palm_size():
    assert abs(palm_size(make_hand(palm=0.09)) - 0.09) < 1e-6


def test_zero_palm_does_not_divide_by_zero():
    assert pinch_ratio(make_hand(palm=0.0)) >= 0
