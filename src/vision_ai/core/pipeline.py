"""Starts and stops the threads: capture -> tracker -> engine -> cursor."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from vision_ai.actions.cursor_thread import CursorThread
from vision_ai.actions.dispatcher import Dispatcher
from vision_ai.config.defaults import CameraConfig, CursorConfig, TrackerConfig
from vision_ai.core.capture import CaptureThread
from vision_ai.core.slot import LatestSlot, RateMeter
from vision_ai.core.tracker import TrackerThread
from vision_ai.core.types import Frame, HandFrame, aim_point
from vision_ai.gestures.cursor_controller import CursorController
from vision_ai.gestures.hand_pose import HandPose, read_pose
from vision_ai.gestures.recognizer import GestureOutput, GestureRecognizer
from vision_ai.gestures.two_hand import TwoHandZoom

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class EngineOutput:
    """What the preview window needs to draw."""

    frame: HandFrame
    aim: tuple[float, float] | None  # screen position the cursor is sent to (pixels)
    pose: HandPose | None  # pinch numbers and finger states of the active hand
    gesture: str = ""  # current gesture state, e.g. "move", "drag"


class EngineThread(threading.Thread):
    def __init__(
        self,
        hands: LatestSlot[HandFrame],
        out: LatestSlot[EngineOutput],
        controller: CursorController | None,
        cursor: CursorThread | None,
        recognizer: GestureRecognizer | None = None,
        dispatcher: Dispatcher | None = None,
        two_hand: TwoHandZoom | None = None,
    ) -> None:
        super().__init__(name="engine", daemon=True)
        self._in = hands
        self._out = out
        self._controller = controller
        self._cursor = cursor
        self._recognizer = recognizer
        self._dispatcher = dispatcher
        self._two_hand = two_hand
        self._hold = False
        self._stop_evt = threading.Event()
        self.fps = RateMeter()
        self.control_enabled = True
        self._frozen: tuple[float, float] | None = None
        self._last_target: tuple[float, float] | None = None
        self._last_click_pos: tuple[float, float] | None = None

    def stop(self) -> None:
        self._stop_evt.set()

    def run(self) -> None:
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
                self._out.put(self._process(frame, was_enabled))
                was_enabled = self.control_enabled
        finally:
            if self._dispatcher is not None:
                self._dispatcher.release_all()
            self._out.close()

    def _two_hand_step(self, frame: HandFrame) -> GestureOutput | None:
        th, rec = self._two_hand, self._recognizer
        if th is None or rec is None:
            return None
        if len(frame.hands) == 2:
            a, b = frame.hands
            (ax, ay), (bx, by) = aim_point(a), aim_point(b)
            dist = ((ax - bx) * a.aspect) ** 2 + (ay - by) ** 2
            out = th.update((read_pose(a, rec.cfg), read_pose(b, rec.cfg)), dist**0.5 * 1000.0)
        else:
            out = th.update(None, None)
        if not out.active:
            return None
        return GestureOutput("two-hand zoom", freeze=True, events=list(out.events))

    def _process(self, frame: HandFrame, was_enabled: bool) -> EngineOutput:
        ctrl = self._controller
        if ctrl is None:
            return EngineOutput(frame=frame, aim=None, pose=None)
        if self.control_enabled and not was_enabled:
            ctrl.reset()
        hand = ctrl.pick_hand(frame)
        ctrl.holding = self._hold  # trackpad mode: do not move while pinching, scrolling...
        aim = ctrl.update(frame)
        pose = read_pose(hand, self._recognizer.cfg) if (hand and self._recognizer) else None

        g = None
        if self._recognizer is not None:
            two = self._two_hand_step(frame)
            if two is not None:  # two-hand zoom wins over the one-hand gestures
                self._recognizer.update(None, None, frame.t)
                g = two
            else:
                g = self._recognizer.update(pose, ctrl.last_unit if hand else None, frame.t)
            self._hold = g.freeze
            if self._dispatcher is not None and g.events:
                self._dispatcher.handle(g.events, paused=not self.control_enabled)
                if any(e[0] == "click" for e in g.events):
                    self._last_click_pos = self._frozen or self._last_target

        target = aim
        if aim is not None and g is not None and g.freeze:
            if self._frozen is None:
                snap = g.snap_to_last_click and self._last_click_pos is not None
                self._frozen = self._last_click_pos if snap else (self._last_target or aim)
            target = self._frozen
        else:
            self._frozen = None

        if target is not None and self.control_enabled:
            self._last_target = target
            if self._cursor is not None:
                self._cursor.set_target(target[0], target[1], frame.t)
        return EngineOutput(frame=frame, aim=target, pose=pose, gesture=g.state if g else "")


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
        recognizer: GestureRecognizer | None = None,
        dispatcher: Dispatcher | None = None,
        two_hand: TwoHandZoom | None = None,
    ) -> None:
        self.frames: LatestSlot[Frame] = LatestSlot()
        self.hands: LatestSlot[HandFrame] = LatestSlot()
        self.output: LatestSlot[EngineOutput] = LatestSlot()
        self.capture = CaptureThread(self.frames, camera)
        self.tracker = TrackerThread(self.frames, self.hands, model_path, tracker)
        self.controller = controller
        self.cursor = CursorThread(mover, cursor_cfg) if mover is not None else None
        self.recognizer = recognizer
        self.dispatcher = dispatcher
        self.engine = EngineThread(
            self.hands, self.output, controller, self.cursor, recognizer, dispatcher, two_hand
        )

    def start(self) -> None:
        if self.cursor is not None:
            self.cursor.start()
        self.engine.start()
        self.tracker.start()
        self.capture.start()

    def stop(self) -> None:
        if self.dispatcher is not None:
            self.dispatcher.release_all()
        for t in (self.capture, self.tracker, self.engine, self.cursor):
            if t is not None:
                t.stop()
        for t in (self.capture, self.tracker, self.engine, self.cursor):
            if t is not None and t.is_alive():
                t.join(timeout=2.0)

    def set_control_enabled(self, enabled: bool) -> None:
        if not enabled and self.dispatcher is not None:
            self.dispatcher.release_all()
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
