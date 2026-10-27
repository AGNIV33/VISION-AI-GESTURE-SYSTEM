"""The brain of the tray app: holds the settings, saves them, applies them everywhere."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from vision_ai.app.engine import EngineManager
from vision_ai.config import settings as st
from vision_ai.licensing import license as lic

log = logging.getLogger(__name__)


class AppController(QObject):
    settings_changed = Signal()
    hotkey_problem = Signal(str)
    _hotkey_pressed = Signal()  # emitted from the hotkey thread, handled on the Qt thread

    def __init__(
        self,
        settings: st.Settings,
        manager: EngineManager,
        save: Callable[[st.Settings], object] = st.save,
        autostart_set: Callable[[bool], bool] | None = None,
        hotkey_factory: Callable[[Callable[[], None]], object] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.manager = manager
        self._save = save
        self._autostart_set = autostart_set
        self._hotkey_factory = hotkey_factory
        self._hotkey = None
        self._hotkey_pressed.connect(manager.toggle_pause)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)  # sliders send many changes: save once they stop
        self._save_timer.timeout.connect(self.flush)
        self._sync_hotkey()

    # --- changes ---------------------------------------------------------------------------

    def update(self, **changes: object) -> None:
        for key, value in changes.items():
            if not hasattr(self.settings, key):
                raise AttributeError(key)
            setattr(self.settings, key, value)
        st.sanitize(self.settings)
        if "start_with_windows" in changes and self._autostart_set is not None:
            if not self._autostart_set(self.settings.start_with_windows):
                log.warning("could not change the Windows startup entry")
                self.settings.start_with_windows = not self.settings.start_with_windows
        if "pause_hotkey" in changes:
            self._sync_hotkey()
        self.manager.apply_settings(self.settings)
        self._save_timer.start()
        self.settings_changed.emit()

    def flush(self) -> None:
        """Write the settings file now (also called when the app quits)."""
        self._save_timer.stop()
        try:
            self._save(self.settings)
        except OSError as exc:
            log.warning("could not save settings: %s", exc)

    # --- license ---------------------------------------------------------------------------

    def activate_license(self, key: str) -> lic.LicenseInfo:
        info = lic.check(key)
        if info.valid or not key.strip():
            self.update(license_key="".join(key.split()))
        return info

    @property
    def license(self) -> lic.LicenseInfo:
        return self.manager.license

    # --- hotkey ----------------------------------------------------------------------------

    def _sync_hotkey(self) -> None:
        if self.settings.pause_hotkey and self._hotkey is None and self._hotkey_factory:
            hk = self._hotkey_factory(self._hotkey_pressed.emit)
            hk.start()  # type: ignore[attr-defined]
            self._hotkey = hk
            ready = getattr(hk, "ready", None)
            if ready is not None and ready.wait(1.0) and getattr(hk, "error", None):
                self.hotkey_problem.emit(str(hk.error))  # type: ignore[attr-defined]
        elif not self.settings.pause_hotkey and self._hotkey is not None:
            self._hotkey.stop()  # type: ignore[attr-defined]
            self._hotkey = None

    def shutdown(self) -> None:
        self.flush()
        if self._hotkey is not None:
            self._hotkey.stop()  # type: ignore[attr-defined]
            self._hotkey = None
        self.manager.stop()
