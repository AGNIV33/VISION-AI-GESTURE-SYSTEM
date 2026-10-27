"""Owns the tracking pipeline for the tray app: start / stop / restart, live settings,
pause, health checks (camera unplugged, dark room, admin windows)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from vision_ai.config import calibration
from vision_ai.config import settings as st
from vision_ai.core.pipeline import Pipeline
from vision_ai.core.tracker import find_model
from vision_ai.licensing import license as lic
from vision_ai.licensing.features import allowed_ids

log = logging.getLogger(__name__)

RETRY_S = 5.0
LOW_LIGHT = 40.0  # camera picture brightness (0..255) below this = too dark
OK_LIGHT = 55.0
LOW_LIGHT_SECONDS = 6
UIPI_REPEAT_S = 600.0

STARTING, RUNNING, PAUSED, ERROR, STOPPED = "starting", "running", "paused", "error", "stopped"


class EngineManager(QObject):
    status_changed = Signal(str, str)  # (state, text for the tray tooltip)
    paused_changed = Signal(bool)
    gesture_ran = Signal(tuple)  # an event that really ran, for the click ring
    warning = Signal(str)  # one-time tips: dark room, admin window

    def __init__(
        self,
        settings: st.Settings,
        pipeline_factory: Callable[..., Pipeline] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._factory = pipeline_factory
        self.pipeline: Pipeline | None = None
        self.state = STOPPED
        self.message = ""
        self._paused = False
        self._suspended = 0
        self._dark_count = 0
        self._dark_warned = False
        self._uipi_ticks = 0
        self._uipi_last = -UIPI_REPEAT_S
        self._ticks = 0
        self._retry_at: int | None = None
        self.license = lic.check(settings.license_key)
        self._allowed: set[str] = set()
        self._recompute_allowed()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._health)
        self.paused_changed.connect(self._sync_state)  # runs on the Qt thread

    # --- plan -----------------------------------------------------------------------------

    def _recompute_allowed(self) -> None:
        self.license = lic.check(self.settings.license_key)
        self._allowed = allowed_ids(self.license.paid, set(self.settings.gestures_off))

    def is_allowed(self, gesture_id: str) -> bool:
        return gesture_id in self._allowed

    @property
    def paused(self) -> bool:
        return self._paused

    def _effective(self) -> st.Settings:
        """Two-hand tracking only when the plan allows two-hand zoom."""
        two = self.settings.two_hand and "two_hand_zoom" in self._allowed
        return replace(self.settings, two_hand=two)

    # --- start / stop ----------------------------------------------------------------------

    def start(self) -> None:
        if self.pipeline is not None:
            return
        self._set_state(STARTING, "Starting the camera...")
        model = find_model()
        if model is None and self._factory is None:
            self._set_state(
                ERROR,
                "Hand model file is missing. Run scripts/download_model.py (or reinstall the app).",
            )
            self._timer.start()
            return
        try:
            self.pipeline = self._build(model)
            self.pipeline.start()
        except Exception as exc:  # camera / input problems must never crash the app
            log.exception("could not start")
            self.pipeline = None
            self._set_state(ERROR, f"Could not start: {exc}")
            self._timer.start()
            return
        self._apply_enabled()
        self._timer.start()

    def _build(self, model):
        s = self._effective()
        camera, tracker, cursor, gestures = st.make_configs(s)
        gain = st.trackpad_gain(s) if s.mode == "trackpad" else None
        if self._factory is not None:
            return self._factory(camera, tracker, cursor, gestures, model, gain)
        from vision_ai.core.runtime import build_pipeline

        return build_pipeline(
            camera, tracker, cursor, gestures, model,
            control=True,
            allowed=self.is_allowed,
            trackpad_gain=gain,
            on_pause_changed=self._pause_from_gesture,
            on_event=self.gesture_ran.emit,
        )  # fmt: skip

    def stop(self) -> None:
        self._timer.stop()
        pipe, self.pipeline = self.pipeline, None
        if pipe is not None:
            pipe.stop()
        self._set_state(STOPPED, "Stopped")

    def restart(self) -> None:
        self.stop()
        self.start()

    # --- pause -----------------------------------------------------------------------------

    def _pause_from_gesture(self, paused: bool) -> None:  # runs on the engine thread
        self._paused = paused
        self.paused_changed.emit(paused)

    @Slot(bool)
    def _sync_state(self, _paused: bool) -> None:
        if self.state in (RUNNING, PAUSED):
            self._set_state(PAUSED if self._paused else RUNNING, self._text_for_state())

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        self._apply_enabled()
        self.paused_changed.emit(paused)

    def toggle_pause(self) -> None:
        self.set_paused(not self._paused)

    def set_suspended(self, on: bool) -> None:
        """Wizard / calibration: keep tracking but do not move or click."""
        self._suspended = max(0, self._suspended + (1 if on else -1))
        self._apply_enabled()

    def _apply_enabled(self) -> None:
        if self.pipeline is not None:
            self.pipeline.set_control_enabled(not self._paused and not self._suspended)
        if self.state in (RUNNING, PAUSED):
            self._set_state(PAUSED if self._paused else RUNNING, self._text_for_state())

    # --- live settings ---------------------------------------------------------------------

    def apply_settings(self, new: st.Settings) -> None:
        before = (self.settings.camera_index, self._effective().two_hand)
        self.settings = new
        self._recompute_allowed()
        after = (new.camera_index, self._effective().two_hand)
        if self.pipeline is None:
            return
        if before != after:
            self.restart()
            return
        ctrl = self.pipeline.controller
        if ctrl is not None:
            min_cutoff, beta = st.cursor_params(new)
            ctrl.tune(min_cutoff=min_cutoff, beta=beta)
            ctrl.cfg.main_hand = new.main_hand
            gain = st.trackpad_gain(new) if new.mode == "trackpad" else None
            if gain != ctrl.trackpad_gain:
                ctrl.trackpad_gain = gain
                ctrl.reset()
            elif gain is not None:
                ctrl.trackpad_gain = gain

    def reload_calibration(self) -> None:
        """Use the numbers just saved by the calibration."""
        pipe = self.pipeline
        if pipe is not None and pipe.recognizer is not None:
            cfg, _ = calibration.load_gesture_config()
            pipe.recognizer.cfg = cfg

    # --- health ----------------------------------------------------------------------------

    def _text_for_state(self) -> str:
        return "Paused (hold a fist or press Ctrl+Alt+P)" if self._paused else "Running"

    def _set_state(self, state: str, text: str) -> None:
        if state != self.state or text != self.message:
            self.state, self.message = state, text
            self.status_changed.emit(state, text)

    def _health(self) -> None:
        self._ticks += 1
        pipe = self.pipeline
        if pipe is None:
            if self.state == ERROR and self._retry_at is not None and self._ticks >= self._retry_at:
                self._retry_at = None
                self.start()
            elif self.state == ERROR and self._retry_at is None:
                self._retry_at = self._ticks + int(RETRY_S)
            return
        err = pipe.first_error()
        if err:
            log.error("pipeline error: %s", err)
            self.stop_pipeline_for_retry(err)
            return
        if self.state == STARTING and pipe.capture.opened.is_set():
            self._set_state(PAUSED if self._paused else RUNNING, self._text_for_state())
        if self.state in (RUNNING, PAUSED):
            self._check_light(pipe)
            self._check_admin_window()

    def stop_pipeline_for_retry(self, err: str) -> None:
        pipe, self.pipeline = self.pipeline, None
        if pipe is not None:
            pipe.stop()
        self._retry_at = self._ticks + int(RETRY_S)
        self._set_state(ERROR, f"{err} Trying again...")
        self.warning.emit(f"{err} Trying again...")

    def _check_light(self, pipe: Pipeline) -> None:
        b = pipe.capture.brightness
        if b < LOW_LIGHT:
            self._dark_count += 1
        elif b > OK_LIGHT:
            self._dark_count = 0
            self._dark_warned = False
        if self._dark_count >= LOW_LIGHT_SECONDS and not self._dark_warned:
            self._dark_warned = True
            self.warning.emit("The room looks dark. Hand tracking works best with good light.")

    def _check_admin_window(self) -> None:
        self._uipi_ticks += 1
        if self._uipi_ticks % 2 or self._paused:
            return
        from vision_ai.platform.uipi import foreground_blocks_us

        if self._ticks - self._uipi_last >= UIPI_REPEAT_S and foreground_blocks_us():
            self._uipi_last = self._ticks
            self.warning.emit(
                "The window in front runs as administrator, so Windows blocks gestures there. "
                "Run Vision AI as administrator to control it."
            )
