"""Builds a ready-to-start Pipeline from configs. Used by the tray app and the --cursor tool."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from vision_ai.config.defaults import CameraConfig, CursorConfig, GestureConfig, TrackerConfig
from vision_ai.core.pipeline import Pipeline
from vision_ai.gestures.cursor_controller import CursorController
from vision_ai.gestures.cursor_mapper import CursorMapper, Rect
from vision_ai.gestures.recognizer import GestureRecognizer
from vision_ai.gestures.two_hand import TwoHandZoom


def build_pipeline(
    camera: CameraConfig,
    tracker: TrackerConfig,
    cursor_cfg: CursorConfig,
    gesture_cfg: GestureConfig,
    model: Path,
    *,
    control: bool,
    allowed: Callable[[str], bool] | None = None,
    trackpad_gain: float | None = None,
    on_pause_changed: Callable[[bool], None] | None = None,
    on_event: Callable[[tuple], None] | None = None,
) -> Pipeline:
    """control=False: only track and show gestures, never touch the mouse (--debug, wizard)."""
    from vision_ai.actions.dispatcher import Dispatcher, WindowsBackend

    recognizer = GestureRecognizer(gesture_cfg)
    two_hand = TwoHandZoom(gesture_cfg) if tracker.num_hands >= 2 else None
    pipe_ref: list[Pipeline] = []
    dispatcher = mover = None
    start_pos = None

    if control:
        if sys.platform != "win32":
            raise OSError("Mouse control only works on Windows")
        from vision_ai.actions import win_input

        screen = win_input.virtual_screen_rect()

        def mover(x: int, y: int) -> None:
            win_input.move_abs(x, y, screen)

        def start_pos() -> tuple[float, float]:
            return win_input.cursor_pos()

        def toggle_pause() -> None:
            p = pipe_ref[0]
            p.set_control_enabled(not p.control_enabled)
            if on_pause_changed is not None:
                on_pause_changed(not p.control_enabled)

        dispatcher = Dispatcher(WindowsBackend(), toggle_pause, allowed, on_event)
    else:
        screen = Rect(0, 0, 1920, 1080)  # gestures are shown, nothing is clicked

    controller = CursorController(
        CursorMapper(Rect(*cursor_cfg.box), screen),
        cursor_cfg,
        trackpad_gain=trackpad_gain,
        start_pos=start_pos,
    )
    pipe = Pipeline(
        camera, tracker, cursor_cfg, model, controller, mover, recognizer, dispatcher, two_hand
    )
    pipe_ref.append(pipe)
    return pipe
