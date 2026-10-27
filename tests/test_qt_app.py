"""The Qt app, run without a screen and with a fake camera pipeline."""

import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest
from conftest import make_hand

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from vision_ai.app.controller import AppController  # noqa: E402
from vision_ai.app.engine import ERROR, PAUSED, RUNNING, EngineManager  # noqa: E402
from vision_ai.config import settings as st  # noqa: E402
from vision_ai.config.defaults import CursorConfig, GestureConfig  # noqa: E402
from vision_ai.core.pipeline import EngineOutput  # noqa: E402
from vision_ai.core.slot import LatestSlot, RateMeter  # noqa: E402
from vision_ai.core.types import HandFrame  # noqa: E402
from vision_ai.gestures.cursor_controller import CursorController  # noqa: E402
from vision_ai.gestures.cursor_mapper import CursorMapper, Rect  # noqa: E402
from vision_ai.gestures.hand_pose import EXT, HandPose  # noqa: E402
from vision_ai.licensing import license as lic  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    from vision_ai.app.theme import STYLE

    app.setStyleSheet(STYLE)
    return app


class FakePipeline:
    def __init__(self, cursor_cfg, gain=None):
        self.capture = SimpleNamespace(
            opened=threading.Event(), error=None, brightness=120.0, fps=RateMeter()
        )
        self.capture.opened.set()
        self.tracker = SimpleNamespace(fps=RateMeter(), infer_ms=10.0)
        self.controller = CursorController(
            CursorMapper(Rect(*cursor_cfg.box), Rect(0, 0, 1920, 1080)), cursor_cfg, gain
        )
        self.recognizer = SimpleNamespace(cfg=GestureConfig())
        self.output = LatestSlot()
        self.control_enabled = True
        self.started = self.stopped = False
        self.error = None

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def set_control_enabled(self, on):
        self.control_enabled = on

    def first_error(self):
        return self.error


def make_manager(settings=None):
    made = []

    def factory(camera, tracker, cursor, gestures, model, gain):
        p = FakePipeline(cursor, gain)
        p.args = (camera, tracker, cursor, gain)
        made.append(p)
        return p

    m = EngineManager(settings or st.Settings(), pipeline_factory=factory)
    return m, made


def test_manager_starts_pauses_and_stops(qapp):
    m, made = make_manager()
    states = []
    m.status_changed.connect(lambda s, t: states.append(s))
    m.start()
    m._health()
    assert made[0].started and m.state == RUNNING
    m.toggle_pause()
    assert m.state == PAUSED and not made[0].control_enabled
    m.toggle_pause()
    assert m.state == RUNNING and made[0].control_enabled
    m.stop()
    assert made[0].stopped


def test_suspend_keeps_tracking_but_blocks_control(qapp):
    m, made = make_manager()
    m.start()
    m.set_suspended(True)
    assert not made[0].control_enabled
    m.set_suspended(True)
    m.set_suspended(False)
    assert not made[0].control_enabled  # still one wizard open
    m.set_suspended(False)
    assert made[0].control_enabled


def test_camera_error_shows_message_and_retries(qapp):
    m, made = make_manager()
    m.start()
    made[0].error = "Cannot open camera 0 (is another app using it?)"
    warnings = []
    m.warning.connect(warnings.append)
    m._health()
    assert m.state == ERROR and "camera" in m.message and warnings
    for _ in range(6):  # wait out the retry delay
        m._health()
    assert len(made) == 2 and made[1].started  # started again with a fresh pipeline


def test_live_settings_change_tune_without_restart_camera_change_restarts(qapp):
    m, made = make_manager()
    m.start()
    s = st.Settings(smoothness=9, main_hand="left")
    m.apply_settings(s)
    assert len(made) == 1
    ctrl = made[0].controller
    assert ctrl.cfg.main_hand == "left" and ctrl.cfg.min_cutoff < 1.0
    m.apply_settings(st.Settings(camera_index=1))
    assert len(made) == 2 and made[1].args[0].index == 1 and made[0].stopped


def test_trackpad_switch_is_live(qapp):
    m, made = make_manager()
    m.start()
    m.apply_settings(st.Settings(mode="trackpad"))
    assert made[0].controller.trackpad_gain is not None
    m.apply_settings(st.Settings(mode="absolute"))
    assert made[0].controller.trackpad_gain is None


def test_two_hand_needs_the_pro_plan(qapp, monkeypatch):
    m, made = make_manager(st.Settings(two_hand=True))
    m.start()
    assert made[0].args[1].num_hands == 1  # free plan: stays on one hand
    secret = bytes(range(32))
    from vision_ai.licensing import ed25519

    monkeypatch.setattr(lic, "PUBLIC_KEY_HEX", ed25519.public_key(secret).hex())
    key = lic.make_key(secret, "pro", "me")
    m.apply_settings(st.Settings(two_hand=True, license_key=key))
    assert m.license.paid and len(made) == 2 and made[1].args[1].num_hands == 2


def test_dark_room_warns_once(qapp):
    m, made = make_manager()
    m.start()
    m._health()
    made[0].capture.brightness = 10.0
    seen = []
    m.warning.connect(seen.append)
    for _ in range(12):
        m._health()
    assert len([w for w in seen if "dark" in w]) == 1


def test_controller_saves_and_applies(qapp, tmp_path):
    saved = []
    m, made = make_manager()
    m.start()
    ctrl = AppController(st.Settings(), m, save=saved.append, autostart_set=lambda on: True)
    ctrl.update(smoothness=8, start_with_windows=True)
    assert ctrl.settings.smoothness == 8 and ctrl.settings.start_with_windows
    ctrl.flush()
    assert saved and saved[-1].smoothness == 8
    ctrl.update(smoothness=99)
    assert ctrl.settings.smoothness == 10


def test_failed_autostart_change_is_reverted(qapp):
    m, _ = make_manager()
    ctrl = AppController(st.Settings(), m, save=lambda s: None, autostart_set=lambda on: False)
    ctrl.update(start_with_windows=True)
    assert ctrl.settings.start_with_windows is False


def test_hotkey_starts_stops_with_the_setting(qapp):
    m, _ = make_manager()

    class Hot:
        def __init__(self, cb):
            self.cb, self.started, self.stopped = cb, False, False
            self.ready = threading.Event()
            self.ready.set()
            self.error = None
            made.append(self)

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    made = []
    ctrl = AppController(st.Settings(), m, save=lambda s: None, hotkey_factory=Hot)
    assert made and made[0].started
    th = threading.Thread(target=made[0].cb)  # the real hotkey runs on its own thread
    th.start()
    th.join()
    for _ in range(20):
        qapp.processEvents()
        time.sleep(0.005)
    assert m.paused
    ctrl.update(pause_hotkey=False)
    assert made[0].stopped


def test_license_activation_flow(qapp, monkeypatch):
    from vision_ai.licensing import ed25519

    secret = bytes(range(32))
    monkeypatch.setattr(lic, "PUBLIC_KEY_HEX", ed25519.public_key(secret).hex())
    m, _ = make_manager()
    ctrl = AppController(st.Settings(), m, save=lambda s: None)
    bad = ctrl.activate_license("VAI1.JUNK")
    assert not bad.valid and ctrl.settings.license_key == ""
    good = ctrl.activate_license(lic.make_key(secret, "owner", "agniv"))
    assert good.valid and ctrl.license.paid
    ctrl.activate_license("")  # remove
    assert not ctrl.license.paid


def test_settings_window_builds_shows_plan_and_edits(qapp, monkeypatch):
    from vision_ai.app.settings_window import SettingsWindow
    from vision_ai.licensing import ed25519

    secret = bytes(range(32))
    monkeypatch.setattr(lic, "PUBLIC_KEY_HEX", ed25519.public_key(secret).hex())
    m, _ = make_manager()
    ctrl = AppController(st.Settings(), m, save=lambda s: None)
    w = SettingsWindow(ctrl)
    w.show()
    assert w.plan_label.text() == "FREE"
    cb, badge = w.gesture_boxes["right_click"]
    assert not cb.isEnabled() and not badge.isHidden()
    assert w.gesture_boxes["tap"][0].isChecked()
    w.smooth.setValue(9)
    assert ctrl.settings.smoothness == 9
    w.gesture_boxes["tap"][0].setChecked(False)
    assert "tap" in ctrl.settings.gestures_off
    w.key_edit.setPlainText(lic.make_key(secret, "pro", "x"))
    w._activate()
    assert w.plan_label.text() == "PRO" and w.gesture_boxes["right_click"][0].isEnabled()
    assert "Activated" in w.key_result.text()
    closed = []
    w.closed_to_tray.connect(lambda: closed.append(1))
    w.close()
    assert not w.isVisible() and closed


def feed(m, n=1, hand=True, pose=None):
    pipe = m.pipeline
    for _ in range(n):
        frame = HandFrame(
            t=time.monotonic(),
            done_t=time.monotonic(),
            hands=(make_hand(),) if hand else (),
            image=np.zeros((120, 160, 3), dtype=np.uint8),
        )
        pipe.output.put(EngineOutput(frame=frame, aim=None, pose=pose, gesture="move"))


def test_camera_view_draws_frames(qapp):
    from vision_ai.app.camera_view import CameraView

    m, _ = make_manager()
    m.start()
    v = CameraView(m, width=320)
    got = []
    v.output.connect(got.append)
    v.show()
    feed(m)
    v._tick()
    assert got and not v.pixmap().isNull()


def test_calibration_panel_runs_and_saves(qapp, tmp_path, monkeypatch):
    from vision_ai.app import wizard
    from vision_ai.app.camera_view import CameraView
    from vision_ai.config import calibration

    monkeypatch.setattr(calibration, "calibration_path", lambda: tmp_path / "cal.json")
    m, made = make_manager()
    m.start()
    view = CameraView(m, width=320)
    panel = wizard.CalibrationPanel(m, view)
    fake_now = [0.0]
    monkeypatch.setattr(wizard.time, "monotonic", lambda: fake_now[0])
    panel.start()
    done = []
    panel.on_done = done.append

    def pose_for(name):
        return HandPose(
            0.1 if name == "index" else 0.9,
            0.1 if name == "middle" else 0.9,
            (EXT, EXT, EXT, EXT),
            0.1 if name == "ring" else 0.9,
        )

    while panel._cal is not None and fake_now[0] < 100:
        name = panel._cal.current[0]
        out = SimpleNamespace(pose=pose_for(name))
        panel._on_output(out)
        fake_now[0] += 1 / 30
    assert done == [True] and panel.finished_ok
    assert (tmp_path / "cal.json").is_file()


def test_wizard_pages_and_finish(qapp):
    from vision_ai.app.wizard import SetupWizard

    m, _ = make_manager()
    m.start()
    ctrl = AppController(st.Settings(), m, save=lambda s: None, autostart_set=lambda on: True)
    w = SetupWizard(ctrl, m)
    w.show()
    assert len(w.pageIds()) == 4
    w.next()  # welcome -> camera
    assert not w.button(w.WizardButton.NextButton).isEnabled()  # waiting for a hand
    feed(m)
    w.view._tick()
    assert w.seen and w.button(w.WizardButton.NextButton).isEnabled()
    w.next()  # camera -> calibrate (can be skipped)
    w.next()
    w.autostart_box.setChecked(True)
    w.accept()
    assert ctrl.settings.first_run_done and ctrl.settings.start_with_windows


def test_tray_menu_reacts_to_state(qapp):
    from vision_ai.app.tray import TrayIcon

    m, _ = make_manager()
    ctrl = AppController(st.Settings(), m, save=lambda s: None)
    opened = []
    t = TrayIcon(ctrl, m, lambda: opened.append("s"), lambda: None, lambda: None, lambda: None)
    m.start()
    m._health()
    assert t.pause_action.text() == "Pause" and "Running" in t.status_action.text()
    m.toggle_pause()
    assert t.pause_action.text() == "Resume" and "Paused" in t.status_action.text()
    quit_ = []
    t.quit_requested.connect(lambda: quit_.append(1))
    t.quit_requested.emit()
    assert quit_


def test_click_ring_flashes_only_for_clicks(qapp):
    from vision_ai.app.overlay import ClickRing

    r = ClickRing()
    r.on_event(("scroll", 5))
    assert not r.isVisible()
    r.on_event(("click", "left"))
    assert r.isVisible()
    r.enabled = False
    r.hide()
    r.on_event(("click", "left"))
    assert not r.isVisible()


def test_second_copy_wakes_the_first(qapp):
    from vision_ai.app.single_instance import SingleInstance

    first = SingleInstance("VisionAI-test-instance")
    assert first.acquire()
    woke = []
    first.activated.connect(lambda: woke.append(1))
    second = SingleInstance("VisionAI-test-instance")
    assert second.acquire() is False
    for _ in range(50):
        qapp.processEvents()
        time.sleep(0.01)
    assert woke
    first.release()


def test_calibration_dialog_suspends_control(qapp):
    from vision_ai.app.wizard import CalibrationDialog

    m, made = make_manager()
    m.start()
    d = CalibrationDialog(m)
    d.show()
    assert not made[0].control_enabled
    d.accept()
    assert made[0].control_enabled
    assert CursorConfig()  # keep import used
