"""Starts and stops the threads: capture -> tracker -> engine -> cursor."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from vision_ai.actions.cursor_thread import CursorThread
from vision_ai.config.defaults import CameraConfig, CursorConfig, TrackerConfig
from vision_ai.core.capture import CaptureThread
from vision_ai.core.slot import LatestSlot, RateMeter
from vision_ai.core.tracker import TrackerThread
from vision_ai.core.types import Frame, HandFrame
from vision_ai.gestures.cursor_controller import CursorController

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class EngineOutput:
    """What the preview window needs to draw."""

    frame: HandFrame
    aim: tuple[float, float] | None  # screen position the engine wants (pixels)
    pinch: float | None  # thumb-index pinch ratio of the active hand


class EngineThread(threading.Thread):
    def __init__(
        self,
        hands: LatestSlot[HandFrame],
        out: LatestSlot[EngineOutput],
        controller: CursorController | None,
        cursor: CursorThread | None,
    ) -> None:
        super().__init__(name="engine", daemon=True)
        self._in = hands
        self._out = out
        self._controller = controller
        self._cursor = cursor
        self._stop_evt = threading.Event()
        self.fps = RateMeter()
        self.control_enabled = True

    def stop(self) -> None:
        self._stop_evt.set()

    def run(self) -> None:
        from vision_ai.gestures.features import pinch_ratio

        seq = 0
        was_enabled = True
        try:
            while not self._stop_evt.is_set():
                got = self._in.get(seq, timeout=0.2)
                if got is None:
                    if self._in.closed:
                        break
                    continue
                frame, seq = got
                self.fps.tick()
                aim = None
                pinch = None
                if self._controller is not None:
                    hand = self._controller.pick_hand(frame)
                    if hand is not None:
                        pinch = pinch_ratio(hand)
                    if self.control_enabled:
                        if not was_enabled:
                            self._controller.reset()
                        aim = self._controller.update(frame)
                        if aim is not None and self._cursor is not None:
                            self._cursor.set_target(aim[0], aim[1], frame.t)
                    was_enabled = self.control_enabled
                self._out.put(EngineOutput(frame=frame, aim=aim, pinch=pinch))
        finally:
            self._out.close()


class Pipeline:
    """Owns all worker threads. `controller`/`mover` are None for tracking-only mode."""

    def __init__(
        self,
        camera: CameraConfig,
        tracker: TrackerConfig,
        cursor_cfg: CursorConfig,
        model_path: Path,
        controller: CursorController | None = None,
        mover: Callable[[int, int], None] | None = None,
    ) -> None:
        self.frames: LatestSlot[Frame] = LatestSlot()
        self.hands: LatestSlot[HandFrame] = LatestSlot()
        self.output: LatestSlot[EngineOutput] = LatestSlot()
        self.capture = CaptureThread(self.frames, camera)
        self.tracker = TrackerThread(self.frames, self.hands, model_path, tracker)
        self.controller = controller
        self.cursor = CursorThread(mover, cursor_cfg) if mover is not None else None
        self.engine = EngineThread(self.hands, self.output, controller, self.cursor)

    def start(self) -> None:
        if self.cursor is not None:
            self.cursor.start()
        self.engine.start()
        self.tracker.start()
        self.capture.start()

    def stop(self) -> None:
        for t in (self.capture, self.tracker, self.engine, self.cursor):
            if t is not None:
                t.stop()
        for t in (self.capture, self.tracker, self.engine, self.cursor):
            if t is not None and t.is_alive():
                t.join(timeout=2.0)

    def set_control_enabled(self, enabled: bool) -> None:
        self.engine.control_enabled = enabled
        if self.cursor is not None:
            self.cursor.enabled = enabled

    @property
    def control_enabled(self) -> bool:
        return self.engine.control_enabled

    def first_error(self) -> str | None:
        for t in (self.capture, self.tracker, self.cursor):
            err = getattr(t, "error", None)
            if err:
                return err
        return None
