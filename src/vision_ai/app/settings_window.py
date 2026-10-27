"""The Settings window (opens from the tray icon)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from vision_ai import APP_NAME, COPYRIGHT, __version__
from vision_ai.app import logs
from vision_ai.app.controller import AppController
from vision_ai.licensing.features import GESTURES
from vision_ai.resources import asset_path


def _page() -> tuple[QWidget, QVBoxLayout]:
    w = QWidget()
    w.setObjectName("page")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(22, 20, 22, 20)
    lay.setSpacing(14)
    return w, lay


def _label(text: str, name: str = "", wrap: bool = True) -> QLabel:
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    return lab


def _slider(lo: int, hi: int, value: int, on_change) -> tuple[QSlider, QLabel]:
    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(lo, hi)
    s.setValue(value)
    val = QLabel(str(value))
    val.setMinimumWidth(22)
    s.valueChanged.connect(lambda v: (val.setText(str(v)), on_change(v)))
    return s, val


class SettingsWindow(QWidget):
    open_preview = Signal()
    open_wizard = Signal()
    open_calibration = Signal()
    closed_to_tray = Signal()

    def __init__(self, ctrl: AppController) -> None:
        super().__init__(None)
        self.ctrl = ctrl
        self.setWindowTitle(f"{APP_NAME} - Settings")
        self.resize(640, 600)
        icon = asset_path("icons/logo_256.png")
        if icon:
            from PySide6.QtGui import QIcon

            self.setWindowIcon(QIcon(str(icon)))
        self._building = True
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        head = QHBoxLayout()
        head.addWidget(_label(APP_NAME, "title", wrap=False))
        head.addStretch()
        self.plan_label = _label("", wrap=False)
        head.addWidget(self.plan_label)
        root.addLayout(head)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.tabs.addTab(self._general_tab(), "General")
        self.tabs.addTab(self._gestures_tab(), "Gestures")
        self.tabs.addTab(self._cursor_tab(), "Cursor")
        self.tabs.addTab(self._license_tab(), "License")
        self.tabs.addTab(self._about_tab(), "About")
        ctrl.settings_changed.connect(self.refresh)
        self._building = False
        self.refresh()

    # --- tabs ------------------------------------------------------------------------------

    def _general_tab(self) -> QWidget:
        page, lay = _page()
        s = self.ctrl.settings
        form = QFormLayout()
        form.setSpacing(12)
        self.hand = QComboBox()
        self.hand.addItem("Right hand", "right")
        self.hand.addItem("Left hand", "left")
        self.hand.currentIndexChanged.connect(
            lambda _: self._set(main_hand=self.hand.currentData())
        )
        form.addRow("Main hand", self.hand)
        self.camera = QSpinBox()
        self.camera.setRange(0, 9)
        self.camera.valueChanged.connect(lambda v: self._set(camera_index=v))
        row = QHBoxLayout()
        row.addWidget(self.camera)
        test = QPushButton("Show camera")
        test.clicked.connect(self.open_preview.emit)
        row.addWidget(test)
        row.addStretch()
        form.addRow("Camera number", row)
        lay.addLayout(form)
        lay.addWidget(
            _label("0 is your first camera. If the picture is wrong, try 1, 2...", "muted")
        )
        self.autostart = QCheckBox("Start Vision AI when Windows starts")
        self.autostart.toggled.connect(lambda v: self._set(start_with_windows=v))
        self.overlay = QCheckBox("Show a ring when a gesture clicks")
        self.overlay.toggled.connect(lambda v: self._set(show_overlay=v))
        self.hotkey = QCheckBox("Pause / resume from anywhere with Ctrl+Alt+P")
        self.hotkey.toggled.connect(lambda v: self._set(pause_hotkey=v))
        self.two_hand = QCheckBox("Track two hands (needed for two-hand zoom, a bit slower)")
        self.two_hand.toggled.connect(lambda v: self._set(two_hand=v))
        for cb in (self.autostart, self.overlay, self.hotkey, self.two_hand):
            lay.addWidget(cb)
        lay.addStretch()
        buttons = QHBoxLayout()
        wiz = QPushButton("Run setup guide again")
        wiz.clicked.connect(self.open_wizard.emit)
        buttons.addWidget(wiz)
        buttons.addStretch()
        lay.addLayout(buttons)
        del s
        return page

    def _gestures_tab(self) -> QWidget:
        outer = QWidget()
        outer.setObjectName("page")
        ol = QVBoxLayout(outer)
        ol.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner, lay = _page()
        self.plan_text = _label("", "muted")
        lay.addWidget(self.plan_text)
        self.gesture_boxes: dict[str, tuple[QCheckBox, QLabel]] = {}
        for g in GESTURES:
            box = QFrame()
            row = QHBoxLayout(box)
            row.setContentsMargins(0, 2, 0, 2)
            col = QVBoxLayout()
            cb = QCheckBox(g.name)
            cb.toggled.connect(lambda v, gid=g.id: self._gesture_toggled(gid, v))
            col.addWidget(cb)
            col.addWidget(_label(g.how, "muted"))
            row.addLayout(col, 1)
            badge = _label("PRO", "badge", wrap=False)
            row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
            lay.addWidget(box)
            self.gesture_boxes[g.id] = (cb, badge)
        lay.addStretch()
        scroll.setWidget(inner)
        ol.addWidget(scroll)
        return outer

    def _cursor_tab(self) -> QWidget:
        page, lay = _page()
        s = self.ctrl.settings
        form = QFormLayout()
        form.setSpacing(14)
        self.mode = QComboBox()
        self.mode.addItem("Absolute - the cursor goes where your hand is", "absolute")
        self.mode.addItem("Trackpad - your hand pushes the cursor like a touchpad", "trackpad")
        self.mode.currentIndexChanged.connect(lambda _: self._set(mode=self.mode.currentData()))
        form.addRow("Mode", self.mode)
        self.smooth, v1 = _slider(1, 10, s.smoothness, lambda v: self._set(smoothness=v))
        self.resp, v2 = _slider(1, 10, s.responsiveness, lambda v: self._set(responsiveness=v))
        self.sens, v3 = _slider(1, 10, s.sensitivity, lambda v: self._set(sensitivity=v))
        for text, slider, val in (
            ("Steadiness", self.smooth, v1),
            ("Quick response", self.resp, v2),
            ("Trackpad speed", self.sens, v3),
        ):
            row = QHBoxLayout()
            row.addWidget(slider, 1)
            row.addWidget(val)
            form.addRow(text, row)
        lay.addLayout(form)
        lay.addWidget(
            _label(
                "Steadiness: higher = less shake, a little slower. Quick response: higher = "
                "less delay on fast moves. Trackpad speed only works in Trackpad mode.",
                "muted",
            )
        )
        row = QHBoxLayout()
        cal = QPushButton("Calibrate my fingers")
        cal.clicked.connect(self.open_calibration.emit)
        reset = QPushButton("Reset cursor feel")
        reset.clicked.connect(
            lambda: self._set(smoothness=5, responsiveness=5, sensitivity=5, mode="absolute")
        )
        row.addWidget(cal)
        row.addWidget(reset)
        row.addStretch()
        lay.addLayout(row)
        lay.addWidget(
            _label(
                "Calibrate if taps are missed or happen by themselves (takes 25 seconds).", "muted"
            )
        )
        lay.addStretch()
        return page

    def _license_tab(self) -> QWidget:
        page, lay = _page()
        self.license_status = _label("", "heading")
        lay.addWidget(self.license_status)
        self.license_note = _label("", "muted")
        lay.addWidget(self.license_note)
        lay.addWidget(_label("License key"))
        self.key_edit = QPlainTextEdit()
        self.key_edit.setPlaceholderText("Paste your key here (starts with VAI1.)")
        self.key_edit.setFixedHeight(90)
        lay.addWidget(self.key_edit)
        row = QHBoxLayout()
        go = QPushButton("Activate")
        go.setObjectName("primary")
        go.clicked.connect(self._activate)
        rm = QPushButton("Remove key")
        rm.clicked.connect(self._remove_key)
        row.addWidget(go)
        row.addWidget(rm)
        row.addStretch()
        lay.addLayout(row)
        self.key_result = _label("")
        lay.addWidget(self.key_result)
        lay.addStretch()
        return page

    def _about_tab(self) -> QWidget:
        page, lay = _page()
        logo = asset_path("icons/logo_256.png")
        if logo:
            pic = QLabel()
            pic.setPixmap(
                QPixmap(str(logo)).scaled(
                    96, 96, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )  # fmt: skip
            lay.addWidget(pic)
        lay.addWidget(_label(APP_NAME, "title"))
        lay.addWidget(_label(f"Version {__version__}", "muted"))
        lay.addWidget(_label("Control your PC with hand gestures through a normal webcam."))
        lay.addWidget(_label("Designed and built by Agniv Sarkar", "heading"))
        lay.addWidget(_label(COPYRIGHT, "muted"))
        lay.addWidget(
            _label(
                "Your camera picture never leaves your PC. Nothing is recorded or sent.", "muted"
            )
        )
        row = QHBoxLayout()
        logs_btn = QPushButton("Open log folder")
        logs_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs.log_path().parent)))
        )
        row.addWidget(logs_btn)
        row.addStretch()
        lay.addLayout(row)
        lay.addStretch()
        return page

    # --- behaviour -------------------------------------------------------------------------

    def _set(self, **changes) -> None:
        if not self._building:
            self.ctrl.update(**changes)

    def _gesture_toggled(self, gid: str, on: bool) -> None:
        if self._building:
            return
        off = set(self.ctrl.settings.gestures_off)
        (off.discard if on else off.add)(gid)
        self.ctrl.update(gestures_off=sorted(off))

    def _activate(self) -> None:
        key = self.key_edit.toPlainText()
        info = self.ctrl.activate_license(key)
        if info.valid:
            self.key_result.setObjectName("good")
            self.key_result.setText(f"Activated: {info.plan.upper()} plan. Thank you!")
        else:
            self.key_result.setObjectName("bad")
            self.key_result.setText(info.reason or "Please paste a key first.")
        self.key_result.style().unpolish(self.key_result)
        self.key_result.style().polish(self.key_result)

    def _remove_key(self) -> None:
        self.key_edit.clear()
        self.ctrl.activate_license("")
        self.key_result.setText("Key removed. You are on the Free plan.")

    def refresh(self) -> None:
        """Show the current settings and plan (called after any change)."""
        s, lic = self.ctrl.settings, self.ctrl.license
        was, self._building = self._building, True
        self.hand.setCurrentIndex(self.hand.findData(s.main_hand))
        self.camera.setValue(s.camera_index)
        self.autostart.setChecked(s.start_with_windows)
        self.overlay.setChecked(s.show_overlay)
        self.hotkey.setChecked(s.pause_hotkey)
        self.two_hand.setChecked(s.two_hand)
        self.mode.setCurrentIndex(self.mode.findData(s.mode))
        self.smooth.setValue(s.smoothness)
        self.resp.setValue(s.responsiveness)
        self.sens.setValue(s.sensitivity)
        paid = lic.paid
        self.plan_label.setText("PRO" if paid else "FREE")
        color = "#5b8cff" if paid else "#8b92a6"
        self.plan_label.setStyleSheet(
            f"color:{color}; border:1px solid {color}; border-radius:8px; padding:1px 9px;"
            "font-weight:600;"
        )
        for g in GESTURES:
            cb, badge = self.gesture_boxes[g.id]
            unlocked = g.free or paid
            cb.setEnabled(unlocked and g.id != "move")
            cb.setChecked(unlocked and g.id not in s.gestures_off)
            badge.setVisible(not g.free and not paid)
        if paid:
            self.plan_text.setText(
                "Pro plan: all gestures are available. Untick any you do not want."
            )
            self.license_status.setText(f"{lic.plan.upper()} plan - {lic.who or 'licensed'}")
            self.license_note.setText(f"Expires: {lic.expires}" if lic.expires else "No expiry.")
        else:
            free = ", ".join(g.name for g in GESTURES if g.free)
            self.plan_text.setText(
                f"Free plan: {free}. Gestures marked PRO need a license key (License tab)."
            )
            self.license_status.setText("Free plan")
            self.license_note.setText(lic.reason or "Enter a key to unlock every gesture.")
        self._building = was

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()  # closing only hides it: the app keeps running in the tray
        self.hide()
        self.ctrl.flush()
        self.closed_to_tray.emit()
