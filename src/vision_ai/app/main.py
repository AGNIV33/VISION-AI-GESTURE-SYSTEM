"""The Vision AI tray app: `python -m vision_ai` (or the installed Vision AI.exe)."""

from __future__ import annotations

import logging
import sys

from vision_ai import APP_NAME

log = logging.getLogger(__name__)


class AppShell:
    """Creates and connects every piece of the tray app."""

    def __init__(self, app, background: bool) -> None:
        from PySide6.QtCore import QTimer

        from vision_ai.app.controller import AppController
        from vision_ai.app.engine import EngineManager
        from vision_ai.app.overlay import ClickRing
        from vision_ai.app.settings_window import SettingsWindow
        from vision_ai.app.tray import TrayIcon
        from vision_ai.config import settings as st
        from vision_ai.platform import autostart
        from vision_ai.platform.hotkey import GlobalHotkey

        self.app = app
        self.background = background
        settings = st.load()
        self.manager = EngineManager(settings)
        self.ctrl = AppController(
            settings,
            self.manager,
            autostart_set=autostart.set_enabled,
            hotkey_factory=GlobalHotkey,
        )
        self.settings_win = SettingsWindow(self.ctrl)
        self.preview_win = None
        self.wizard = None
        self.ring = ClickRing()
        self.ring.enabled = settings.show_overlay
        self.manager.gesture_ran.connect(self.ring.on_event)
        self.ctrl.settings_changed.connect(self._settings_changed)
        self.tray = TrayIcon(
            self.ctrl,
            self.manager,
            self.show_settings,
            self.show_preview,
            self.show_calibration,
            self.show_wizard,
        )
        self.tray.quit_requested.connect(self.quit)
        self.settings_win.open_preview.connect(self.show_preview)
        self.settings_win.open_wizard.connect(self.show_wizard)
        self.settings_win.open_calibration.connect(self.show_calibration)
        self.settings_win.closed_to_tray.connect(self._closed_to_tray)
        self.manager.warning.connect(self.tray.message)
        self.ctrl.hotkey_problem.connect(self.tray.message)
        self.tray.show()
        self.manager.start()
        if not settings.first_run_done:
            QTimer.singleShot(300, self.show_wizard)
        elif not background:
            QTimer.singleShot(300, self.show_settings)

    def _settings_changed(self) -> None:
        self.ring.enabled = self.ctrl.settings.show_overlay

    def _closed_to_tray(self) -> None:
        if not self.ctrl.settings.tray_tip_shown:
            self.tray.message("Vision AI is still running here. Right-click the icon to quit.")
            self.ctrl.update(tray_tip_shown=True)

    def _raise(self, win) -> None:
        win.show()
        win.raise_()
        win.activateWindow()

    def show_settings(self) -> None:
        self._raise(self.settings_win)

    def show_preview(self) -> None:
        from PySide6.QtWidgets import QVBoxLayout, QWidget

        from vision_ai.app.camera_view import CameraView

        if self.preview_win is None:
            w = QWidget()
            w.setWindowTitle(f"{APP_NAME} - Camera")
            lay = QVBoxLayout(w)
            lay.addWidget(CameraView(self.manager, width=640, info=True))
            w.resize(680, 420)
            self.preview_win = w
        self._raise(self.preview_win)

    def show_calibration(self) -> None:
        from vision_ai.app.wizard import CalibrationDialog

        dlg = CalibrationDialog(self.manager)
        dlg.exec()

    def show_wizard(self) -> None:
        from vision_ai.app.wizard import SetupWizard

        self.wizard = SetupWizard(self.ctrl, self.manager)
        self._raise(self.wizard)

    def quit(self) -> None:
        log.info("quitting")
        self.tray.hide()
        self.ctrl.shutdown()  # saves settings, stops the camera, releases mouse buttons
        self.ring.hide()
        self.app.quit()


def run(background: bool = False) -> int:
    from vision_ai.app import logs
    from vision_ai.platform.dpi import enable_dpi_awareness

    logs.setup()
    log.info("starting %s (background=%s)", APP_NAME, background)
    enable_dpi_awareness()

    from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

    from vision_ai.app.single_instance import SingleInstance
    from vision_ai.app.theme import STYLE

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)  # closing a window never quits: only Quit does
    app.setStyleSheet(STYLE)

    single = SingleInstance()
    if not single.acquire():
        log.info("already running; asked the first copy to show itself")
        return 0
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.warning(None, APP_NAME, "This PC has no system tray, so the app cannot run.")
        return 1

    shell = AppShell(app, background)
    single.activated.connect(shell.show_settings)
    try:
        return app.exec()
    finally:
        single.release()
