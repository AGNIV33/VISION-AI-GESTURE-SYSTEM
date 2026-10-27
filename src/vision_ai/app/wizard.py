"""First-run setup guide (4 steps) and the stand-alone calibration dialog."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from vision_ai import APP_NAME
from vision_ai.app.camera_view import CameraView
from vision_ai.app.controller import AppController
from vision_ai.app.engine import EngineManager
from vision_ai.config import calibration
from vision_ai.gestures.calibrator import STEPS, Calibrator
from vision_ai.licensing.features import GESTURES


def _text(text: str, name: str = "") -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    if name:
        lab.setObjectName(name)
    return lab


class _Page(QWizardPage):
    """A wizard page whose 'Next is allowed' rule can be set from outside."""

    def __init__(self) -> None:
        super().__init__()
        self.can_continue = lambda: True

    def isComplete(self) -> bool:  # noqa: N802 (Qt name)
        return bool(self.can_continue())


class CalibrationPanel(QWidget):
    """The 25-second finger calibration: instruction, countdown, camera picture, result."""

    def __init__(self, manager: EngineManager, view: CameraView, parent=None) -> None:
        super().__init__(parent)
        self._manager = manager
        self._view = view
        self._cal: Calibrator | None = None
        self.finished_ok: bool | None = None  # None = not run yet
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.instruction = _text("", "big")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bar = QProgressBar()
        self.bar.setRange(0, len(STEPS))
        self.result = _text("")
        self.start_btn = QPushButton("Start")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self.start)
        lay.addWidget(self.instruction)
        lay.addWidget(self.bar)
        lay.addWidget(self.result)
        lay.addWidget(self.start_btn, 0, Qt.AlignmentFlag.AlignLeft)
        self._view.output.connect(self._on_output)
        self.on_done = lambda ok: None

    def start(self) -> None:
        self._cal = Calibrator()
        self.finished_ok = None
        self.result.setText("")
        self.start_btn.setEnabled(False)
        self.bar.setValue(0)
        self.instruction.setText("Get ready: hold your hand up in front of the camera...")

    def _on_output(self, out) -> None:
        cal = self._cal
        if cal is None or cal.done:
            return
        now = time.monotonic()
        cal.feed(now, out.pose)
        self.bar.setValue(cal.index)
        cur = cal.current
        if cur is not None:
            self.instruction.setText(f"{cur[1]}  ({cal.seconds_left(now):.0f})")
            return
        res = cal.result()
        self._cal = None
        self.finished_ok = res.ok
        if res.ok:
            calibration.save(res.values)
            self._manager.reload_calibration()
            self.instruction.setText("Done! Your fingers are calibrated.")
            self.result.setObjectName("good")
        else:
            self.instruction.setText("That did not work.")
            self.result.setObjectName("warn")
        self.result.setText(res.lines[-1] if res.lines else "")
        self.result.style().unpolish(self.result)
        self.result.style().polish(self.result)
        self.start_btn.setText("Try again")
        self.start_btn.setEnabled(True)
        self.on_done(res.ok)


class CalibrationDialog(QDialog):
    """Opened from Settings > Cursor > Calibrate."""

    def __init__(self, manager: EngineManager, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Calibrate fingers")
        self._manager = manager
        lay = QVBoxLayout(self)
        lay.addWidget(
            _text(
                "Keep your hand inside the frame. Follow the steps: open hand, then touch your "
                "thumb to each fingertip when asked."
            )
        )
        self.view = CameraView(manager, width=520)
        lay.addWidget(self.view)
        self.panel = CalibrationPanel(manager, self.view)
        lay.addWidget(self.panel)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)

    def showEvent(self, event) -> None:  # noqa: N802
        self._manager.set_suspended(True)  # track, but do not click while calibrating
        super().showEvent(event)

    def done(self, result: int) -> None:
        self._manager.set_suspended(False)
        super().done(result)


class SetupWizard(QWizard):
    def __init__(self, ctrl: AppController, manager: EngineManager, parent=None) -> None:
        super().__init__(parent)
        self.ctrl, self.manager = ctrl, manager
        self.setWindowTitle(f"{APP_NAME} - Setup")
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOption(QWizard.WizardOption.NoCancelButtonOnLastPage, True)
        self.setMinimumSize(640, 640)
        self.view = CameraView(manager, width=520)
        self.addPage(self._welcome())
        self.camera_page = self._camera()
        self.addPage(self.camera_page)
        self.cal_page = self._calibrate()
        self.addPage(self.cal_page)
        self.addPage(self._finish())
        self.finished.connect(self._on_finished)

    def showEvent(self, event) -> None:  # noqa: N802
        self.manager.set_suspended(True)
        super().showEvent(event)

    # --- pages -----------------------------------------------------------------------------

    def _welcome(self) -> QWizardPage:
        p = _Page()
        p.setTitle(f"Welcome to {APP_NAME}")
        lay = QVBoxLayout(p)
        lay.addWidget(_text("Control your PC with your hand. Just a normal webcam is enough."))
        lay.addWidget(_text("This quick setup takes about one minute:", "heading"))
        lay.addWidget(
            _text("1. Check your camera\n2. Calibrate your fingers (30 s)\n3. Learn the gestures")
        )
        lay.addWidget(
            _text(
                "Tip: sit about an arm's length from the screen, with light in front of you.",
                "muted",
            )
        )
        lay.addStretch()
        return p

    def _camera(self) -> QWizardPage:
        p = _Page()
        p.setTitle("Step 1: Check your camera")
        lay = QVBoxLayout(p)
        lay.addWidget(_text("Hold your hand up. You should see green lines drawn on it."))
        lay.addWidget(self.view)
        row = QHBoxLayout()
        row.addWidget(QLabel("Camera number:"))
        self.cam_spin = QSpinBox()
        self.cam_spin.setRange(0, 9)
        self.cam_spin.setValue(self.ctrl.settings.camera_index)
        self.cam_spin.valueChanged.connect(lambda v: self.ctrl.update(camera_index=v))
        row.addWidget(self.cam_spin)
        row.addStretch()
        lay.addLayout(row)
        self.cam_status = _text("Waiting for your hand...", "muted")
        lay.addWidget(self.cam_status)
        self.seen = False
        self.view.output.connect(self._camera_output)
        self._camera_t0 = time.monotonic()
        p.can_continue = lambda: self.seen or time.monotonic() - self._camera_t0 > 12
        self._tick = QTimer(p)
        self._tick.setInterval(500)
        self._tick.timeout.connect(p.completeChanged.emit)
        self._tick.start()
        return p

    def _camera_output(self, out) -> None:
        if out.frame.hands and not self.seen:
            self.seen = True
            self.cam_status.setText("Great, I can see your hand.")
            self.cam_status.setObjectName("good")
            self.cam_status.style().unpolish(self.cam_status)
            self.cam_status.style().polish(self.cam_status)
            self.camera_page.completeChanged.emit()
        elif not self.seen and self.manager.pipeline is not None:
            b = self.manager.pipeline.capture.brightness
            if b < 40:
                self.cam_status.setText("The picture is dark. Turn on a light in front of you.")

    def _calibrate(self) -> QWizardPage:
        p = _Page()
        p.setTitle("Step 2: Calibrate your fingers")
        lay = QVBoxLayout(p)
        lay.addWidget(
            _text("This teaches the app how big your pinch is, so taps work for your hand.")
        )
        self.view2 = CameraView(self.manager, width=520)
        self.panel = CalibrationPanel(self.manager, self.view2)
        lay.addWidget(self.view2)
        lay.addWidget(self.panel)
        lay.addWidget(_text("You can skip this and calibrate later in Settings.", "muted"))
        return p

    def _finish(self) -> QWizardPage:
        p = _Page()
        p.setTitle("You are ready!")
        lay = QVBoxLayout(p)
        lay.addWidget(
            _text("Vision AI now lives in the tray (near the clock). Gestures:", "heading")
        )
        for g in GESTURES:
            tag = "" if g.free else "  [PRO]"
            lay.addWidget(_text(f"<b>{g.name}</b>{tag}: {g.how}"))
        self.autostart_box = QCheckBox("Start Vision AI when Windows starts")
        self.autostart_box.setChecked(True)
        lay.addWidget(self.autostart_box)
        lay.addWidget(
            _text("Pause any time: hold a fist for 1.5 seconds, or press Ctrl+Alt+P.", "muted")
        )
        lay.addStretch()
        return p

    def _on_finished(self, result: int) -> None:
        self.manager.set_suspended(False)
        if result == QDialog.DialogCode.Accepted:
            self.ctrl.update(first_run_done=True, start_with_windows=self.autostart_box.isChecked())
        else:
            self.ctrl.update(first_run_done=True)
