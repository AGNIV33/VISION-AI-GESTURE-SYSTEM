import json

from vision_ai.config import calibration
from vision_ai.config.defaults import GestureConfig


def test_thresholds_sit_between_pinch_and_open():
    on, off, arm_on, arm_off = calibration.thresholds([1.0] * 20, [0.4] * 20)
    assert 0.4 < on < off < arm_on < arm_off < 1.0


def test_thresholds_refuse_overlapping_numbers():
    assert calibration.thresholds([0.5] * 20, [0.45] * 20) is None


def test_thresholds_need_enough_pictures():
    assert calibration.thresholds([1.0] * 3, [0.3] * 3) is None


def test_a_few_bad_pictures_do_not_spoil_it():
    pinch = [0.35] * 18 + [0.9, 0.95]  # two pictures where the pinch was lost
    res = calibration.thresholds([1.0] * 20, pinch)
    assert res is not None and res[0] < 0.6


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(calibration, "calibration_path", lambda: tmp_path / "c.json")
    calibration.save({"pinch_on": 0.5, "pinch_off": 0.6, "unknown_key": 9})
    cfg, ok = calibration.load_gesture_config()
    assert ok and cfg.pinch_on == 0.5 and cfg.pinch_off == 0.6


def test_missing_or_broken_file_falls_back_to_defaults(tmp_path, monkeypatch):
    p = tmp_path / "c.json"
    monkeypatch.setattr(calibration, "calibration_path", lambda: p)
    assert calibration.load_gesture_config() == (GestureConfig(), False)
    p.write_text("{not json")
    assert calibration.load_gesture_config()[1] is False
    p.write_text(json.dumps({"pinch_on": "abc"}))
    assert calibration.load_gesture_config()[1] is False
