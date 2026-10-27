"""A widget that shows the camera picture with the hand skeleton (from the running pipeline)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

from vision_ai.app.engine import EngineManager
from vision_ai.config.defaults import CursorConfig


class CameraView(QLabel):
    output = Signal(object)  # each new EngineOutput (the wizard listens to this)

    def __init__(
        self, manager: EngineManager, width: int = 480, info: bool = False, parent=None
    ) -> None:
        super().__init__(parent)
        self._info = info
        self._manager = manager
        self._seq = 0
        self._pipe_id = 0
        self.last_output = None
        self.setMinimumSize(width, int(width * 0.5625))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:#000; border-radius:10px;")
        self._idle_text = "Waiting for the camera..."
        self.setText(self._idle_text)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # noqa: N802
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        pipe = self._manager.pipeline
        if pipe is None:
            if self.pixmap().isNull():
                self.setText(self._manager.message or self._idle_text)
            return
        if id(pipe) != self._pipe_id:  # the pipeline was restarted: start counting again
            self._pipe_id, self._seq = id(pipe), 0
        got = pipe.output.get(self._seq, timeout=0.0)
        if got is None:
            return
        out, self._seq = got
        self.last_output = out
        self.output.emit(out)
        if out.frame.image is None:
            return
        from vision_ai.ui.preview import draw

        box = pipe.controller.cfg.box if pipe.controller is not None else CursorConfig().box
        img = draw(out, pipe, box, controlling=False, tuning=False, info=self._info)
        h, w = img.shape[:2]
        qimg = QImage(img.data, w, h, img.strides[0], QImage.Format.Format_BGR888).copy()
        pm = QPixmap.fromImage(qimg).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(pm)
