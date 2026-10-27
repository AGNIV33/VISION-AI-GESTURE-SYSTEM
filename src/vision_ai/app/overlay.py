"""A small ring that flashes at the cursor when a gesture clicks (click-through window)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QWidget

SIZE = 96
COLORS = {
    "click": "#5b8cff",
    "right": "#b57bff",
    "down": "#3ecf8e",
    "up": "#3ecf8e",
    "home": "#f5a524",
}
FLASH_MS = 320


class ClickRing(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.resize(SIZE, SIZE)
        self.enabled = True
        self._color = QColor(COLORS["click"])
        self._age = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def on_event(self, ev: tuple) -> None:
        """Connected to the engine's gesture_ran signal."""
        if not self.enabled:
            return
        kind = ev[0]
        if kind == "click":
            key = "right" if ev[1] == "right" else "click"
        elif kind in ("down", "up", "home"):
            key = kind
        else:
            return  # scroll / zoom would flash all the time
        self.flash(COLORS[key])

    def flash(self, color: str) -> None:
        self._color = QColor(color)
        pos = QCursor.pos()
        self.move(pos.x() - SIZE // 2, pos.y() - SIZE // 2)
        self._age = 0
        self.show()
        self.raise_()
        self._timer.start()

    def _tick(self) -> None:
        self._age += 16
        if self._age >= FLASH_MS:
            self._timer.stop()
            self.hide()
        else:
            self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt name)
        k = min(self._age / FLASH_MS, 1.0)
        radius = 10 + 30 * k
        c = QColor(self._color)
        c.setAlphaF(max(0.0, 0.9 * (1.0 - k)))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(c, 4))
        p.drawEllipse(QPointF(SIZE / 2, SIZE / 2), radius, radius)
