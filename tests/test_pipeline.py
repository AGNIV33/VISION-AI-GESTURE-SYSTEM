import time

from conftest import make_frame, make_hand

from vision_ai.config.defaults import CameraConfig, CursorConfig, TrackerConfig
from vision_ai.core.pipeline import EngineOutput, EngineThread, Pipeline
from vision_ai.core.slot import LatestSlot
from vision_ai.gestures.cursor_controller import CursorController
from vision_ai.gestures.cursor_mapper import CursorMapper, Rect


class FakeCursor:
    def __init__(self):
        self.targets = []

    def set_target(self, x, y, t):
        self.targets.append((x, y, t))


def _engine(control=True):
    cfg = CursorConfig()
    ctrl = CursorController(CursorMapper(Rect(*cfg.box), Rect(0, 0, 1920, 1080)), cfg)
    hands, out, cursor = LatestSlot(), LatestSlot(), FakeCursor()
    eng = EngineThread(hands, out, ctrl, cursor)
    eng.control_enabled = control
    return eng, hands, out, cursor


def test_engine_sends_target_to_cursor_and_output_to_preview():
    eng, hands, out, cursor = _engine()
    eng.start()
    try:
        hands.put(make_frame(1.0, [make_hand(index_mcp=(0.5, 0.55))]))
        got = out.get(0, timeout=1.0)
        assert got is not None
        result: EngineOutput = got[0]
        assert result.aim is not None and result.pinch is not None
        assert len(cursor.targets) == 1
    finally:
        eng.stop()
        eng.join(1)


def test_engine_does_not_move_cursor_when_paused():
    eng, hands, out, cursor = _engine(control=False)
    eng.start()
    try:
        hands.put(make_frame(1.0, [make_hand()]))
        assert out.get(0, timeout=1.0) is not None
        assert cursor.targets == []
    finally:
        eng.stop()
        eng.join(1)


def test_pipeline_starts_and_stops_cleanly_without_camera_or_model(tmp_path):
    pipe = Pipeline(
        CameraConfig(index=99),
        TrackerConfig(),
        CursorConfig(),
        tmp_path / "missing.task",
        controller=None,
        mover=None,
    )
    pipe.start()
    assert pipe.capture.opened.wait(timeout=10)
    t0 = time.monotonic()
    pipe.stop()
    assert time.monotonic() - t0 < 5
    assert pipe.first_error()  # tells the user what went wrong
