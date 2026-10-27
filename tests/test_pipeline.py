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
        assert result.aim is not None
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


def test_engine_freezes_cursor_during_pinch_and_sends_one_click():
    from vision_ai.actions.dispatcher import Dispatcher
    from vision_ai.gestures.recognizer import GestureRecognizer

    class FakeBackend:
        def __init__(self):
            self.calls = []

        def button(self, which, down):
            self.calls.append((which, down))

        def wheel(self, delta, horizontal=False):
            self.calls.append(("wheel", delta))

    cfg = CursorConfig()
    ctrl = CursorController(CursorMapper(Rect(*cfg.box), Rect(0, 0, 1920, 1080)), cfg)
    backend = FakeBackend()
    cursor = FakeCursor()
    eng = EngineThread(
        LatestSlot(),
        LatestSlot(),
        ctrl,
        cursor,
        GestureRecognizer(),
        Dispatcher(backend, lambda: None),
    )
    t = 0.0
    for _ in range(5):  # open hand at the centre
        t += 1 / 30
        eng._process(make_frame(t, [make_hand(index_mcp=(0.5, 0.55), thumb_index_gap=0.10)]), True)
    before = cursor.targets[-1][:2]
    for _ in range(4):  # pinch; the knuckle wobbles a little while pinching
        t += 1 / 30
        eng._process(
            make_frame(t, [make_hand(index_mcp=(0.51, 0.56), thumb_index_gap=0.005)]), True
        )
    assert cursor.targets[-1][:2] == before  # cursor held still
    for _ in range(3):  # release
        t += 1 / 30
        eng._process(make_frame(t, [make_hand(index_mcp=(0.51, 0.56), thumb_index_gap=0.10)]), True)
    assert backend.calls == [("left", True), ("left", False)]
