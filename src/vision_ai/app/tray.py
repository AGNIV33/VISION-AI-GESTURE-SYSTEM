"""The tray icon and its menu. This is where the app lives while it runs."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from vision_ai import APP_NAME
from vision_ai.app.controller import AppController
from vision_ai.app.engine import ERROR, PAUSED, RUNNING, STARTING, EngineManager
from vision_ai.resources import asset_path

DOT = {RUNNING: "#3ecf8e", PAUSED: "#f5a524", ERROR: "#ef5b5b", STARTING: "#8b92a6"}


def base_icon() -> QIcon:
    for name in ("icons/logo_256.png", "icons/app.ico"):
        path = asset_path(name)
        if path:
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    pm = QPixmap(64, 64)
    pm.fill(QColor("#5b8cff"))
    return QIcon(pm)


def status_icon(base: QIcon, state: str) -> QIcon:
    """The app icon with a small coloured dot: green running, orange paused, red problem."""
    pm = base.pixmap(64, 64)
    if pm.isNull():
        return base
    color = DOT.get(state)
    if color:
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(color))
        p.setPen(QColor("#12141a"))
        p.drawEllipse(36, 36, 26, 26)
        p.end()
    return QIcon(pm)


class TrayIcon(QObject):
    quit_requested = Signal()

    def __init__(
        self,
        ctrl: AppController,
        manager: EngineManager,
        open_settings: Callable[[], None],
        open_preview: Callable[[], None],
        open_calibration: Callable[[], None],
        open_wizard: Callable[[], None],
    ) -> None:
        super().__init__()
        self.ctrl, self.manager = ctrl, manager
        self._base = base_icon()
        self.tray = QSystemTrayIcon(status_icon(self._base, STARTING))
        self.tray.setToolTip(f"{APP_NAME} - starting")
        menu = QMenu()
        self.status_action = QAction("Starting...", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        menu.addSeparator()
        self.pause_action = QAction("Pause", menu)
        self.pause_action.triggered.connect(manager.toggle_pause)
        menu.addAction(self.pause_action)
        menu.addAction("Settings...", open_settings)
        menu.addAction("Show camera", open_preview)
        menu.addAction("Calibrate fingers...", open_calibration)
        menu.addAction("Setup guide...", open_wizard)
        menu.addSeparator()
        self.start_action = QAction("Start with Windows", menu)
        self.start_action.setCheckable(True)
        self.start_action.toggled.connect(lambda v: self._autostart(v))
        menu.addAction(self.start_action)
        menu.addSeparator()
        menu.addAction("Quit", self.quit_requested.emit)
        self._menu = menu  # keep a reference: Qt does not own it
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: (
                open_settings()
                if reason
                in (
                    QSystemTrayIcon.ActivationReason.Trigger,
                    QSystemTrayIcon.ActivationReason.DoubleClick,
                )
                else None
            )
        )
        manager.status_changed.connect(self._on_status)
        manager.paused_changed.connect(self._on_paused)  # may be emitted from another thread
        ctrl.settings_changed.connect(self._sync_checks)
        self._sync_checks()

    def show(self) -> None:
        self.tray.show()

    def hide(self) -> None:
        self.tray.hide()

    def message(self, text: str, title: str = APP_NAME) -> None:
        self.tray.showMessage(title, text, QSystemTrayIcon.MessageIcon.Information, 6000)

    def _autostart(self, on: bool) -> None:
        if on != self.ctrl.settings.start_with_windows:
            self.ctrl.update(start_with_windows=on)

    def _sync_checks(self) -> None:
        on = self.ctrl.settings.start_with_windows
        if self.start_action.isChecked() != on:
            self.start_action.blockSignals(True)
            self.start_action.setChecked(on)
            self.start_action.blockSignals(False)

    @Slot(bool)
    def _on_paused(self, _paused: bool) -> None:
        self._on_status(self.manager.state, self.manager.message)

    @Slot(str, str)
    def _on_status(self, state: str, text: str) -> None:
        if self.manager.paused and state in (RUNNING, PAUSED):
            state, text = PAUSED, "Paused (hold a fist or press Ctrl+Alt+P)"
        self.tray.setIcon(status_icon(self._base, state))
        self.tray.setToolTip(f"{APP_NAME} - {text}")
        self.status_action.setText(text)
        self.pause_action.setText("Resume" if self.manager.paused else "Pause")
        self.pause_action.setEnabled(state in (RUNNING, PAUSED))
