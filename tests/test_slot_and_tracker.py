import threading
import time
from types import SimpleNamespace

import numpy as np

from vision_ai.core.slot import LatestSlot, RateMeter
from vision_ai.core.tracker import result_to_hands


def test_slot_keeps_only_newest():
    s = LatestSlot()
    for i in range(5):
        s.put(i)
    item, seq = s.get(0, timeout=0.1)
    assert item == 4 and seq == 5


def test_slot_times_out_when_nothing_new():
    s = LatestSlot()
    s.put(1)
    _, seq = s.get(0)
    assert s.get(seq, timeout=0.05) is None


def test_slot_wakes_waiting_reader():
    s = LatestSlot()
    got = []
    t = threading.Thread(target=lambda: got.append(s.get(0, timeout=2)))
    t.start()
    time.sleep(0.05)
    s.put("x")
    t.join(1)
    assert got[0][0] == "x"


def test_slot_close_releases_reader():
    s = LatestSlot()
    t = threading.Thread(target=lambda: s.get(0, timeout=5))
    t.start()
    s.close()
    t.join(1)
    assert not t.is_alive()


def test_rate_meter():
    r = RateMeter(smoothing=1.0)
    for i in range(5):
        r.tick(i * 0.05)
    assert abs(r.rate - 20.0) < 1e-6


def _fake_result(label="Right"):
    pts = [SimpleNamespace(x=0.1 * (i % 5), y=0.1, z=0.0) for i in range(21)]
    return SimpleNamespace(
        hand_landmarks=[pts],
        hand_world_landmarks=[pts],
        handedness=[[SimpleNamespace(category_name=label, score=0.9)]],
    )


def test_result_to_hands_converts_arrays_and_side():
    (hand,) = result_to_hands(_fake_result("Left"))
    assert hand.side == "left"
    assert hand.landmarks.shape == (21, 3) and hand.world.shape == (21, 3)
    assert hand.landmarks.dtype == np.float32


def test_result_with_no_hands():
    empty = SimpleNamespace(hand_landmarks=[], hand_world_landmarks=[], handedness=[])
    assert result_to_hands(empty) == ()


def test_prepare_image_shrinks_wide_pictures_and_keeps_shape():
    from vision_ai.core.tracker import prepare_image

    out = prepare_image(np.zeros((720, 1280, 3), np.uint8), 640)
    assert out.shape == (360, 640, 3)
    assert prepare_image(np.zeros((480, 640, 3), np.uint8), 640).shape == (480, 640, 3)
