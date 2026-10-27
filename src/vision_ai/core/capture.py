"""Camera capture thread. Keeps only the newest frame."""

from __future__ import annotations

import logging
import threading
import time

from vision_ai.config.defaults import CameraConfig
from vision_ai.core.slot import LatestSlot, RateMeter
from vision_ai.core.types import Frame

log = logging.getLogger(__name__)


def _backend_ids(name: str) -> list[int]:
    import cv2

    table = {
        "dshow": [cv2.CAP_DSHOW, cv2.CAP_MSMF],
        "msmf": [cv2.CAP_MSMF, cv2.CAP_DSHOW],
        "auto": [cv2.CAP_ANY],
    }
    return table.get(name, [cv2.CAP_ANY])


def _apply_settings(cap, cfg: CameraConfig) -> None:
    import cv2

    # MJPG is what lets most webcams deliver 30 fps at higher sizes.
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)
    cap.set(cv2.CAP_PROP_FPS, cfg.fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)


def camera_info(cap) -> tuple[str, int, int, float]:
    """What the camera really accepted: (format, width, height, fps it reports)."""
    import cv2

    code = int(cap.get(cv2.CAP_PROP_FOURCC))
    fmt = "".join(chr((code >> (8 * i)) & 0xFF) for i in range(4)) if code > 0 else "?"
    fmt = fmt if fmt.isprintable() else "?"
    return (
        fmt.strip() or "?",
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        float(cap.get(cv2.CAP_PROP_FPS)),
    )


def open_camera(cfg: CameraConfig, fallback: bool = True):
    """Open the camera, trying the preferred backend first (and the other one if
    `fallback`). Returns (capture, backend_id).

    The settings are passed when opening (more reliable than setting them afterwards).
    If the camera still gives a different size, they are applied again the old way."""
    import cv2

    params = [
        cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"),
        cv2.CAP_PROP_FRAME_WIDTH, cfg.width,
        cv2.CAP_PROP_FRAME_HEIGHT, cfg.height,
        cv2.CAP_PROP_FPS, cfg.fps,
    ]  # fmt: skip
    ids = _backend_ids(cfg.backend)
    for backend in ids if fallback else ids[:1]:
        cap = None
        try:
            cap = cv2.VideoCapture(cfg.index, backend, params)
        except (cv2.error, TypeError):
            cap = None
        if cap is None or not cap.isOpened():
            if cap is not None:
                cap.release()
            cap = cv2.VideoCapture(cfg.index, backend)
            if not cap.isOpened():
                cap.release()
                continue
            _apply_settings(cap, cfg)
        elif int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) != cfg.width:
            _apply_settings(cap, cfg)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap, backend
    return None, None


class CaptureThread(threading.Thread):
    def __init__(self, out: LatestSlot[Frame], cfg: CameraConfig) -> None:
        super().__init__(name="capture", daemon=True)
        self._out = out
        self._cfg = cfg
        self._stop_evt = threading.Event()
        self.opened = threading.Event()
        self.error: str | None = None
        self.fps = RateMeter()
        self.size: tuple[int, int] = (0, 0)
        self.brightness: float = 128.0  # 0 (black) .. 255; updated twice a second

    def stop(self) -> None:
        self._stop_evt.set()

    def run(self) -> None:
        import cv2

        cap, _ = open_camera(self._cfg)
        if cap is None:
            self.error = f"Cannot open camera {self._cfg.index} (is another app using it?)"
            log.error(self.error)
            self.opened.set()
            self._out.close()
            return
        self.opened.set()
        failures = 0
        count = 0
        try:
            while not self._stop_evt.is_set():
                ok, image = cap.read()
                t = time.monotonic()
                if not ok or image is None:
                    failures += 1
                    if failures > 30:
                        self.error = "Camera stopped sending frames (unplugged?)"
                        log.error(self.error)
                        break
                    time.sleep(0.01)
                    continue
                failures = 0
                if self._cfg.mirror:
                    image = cv2.flip(image, 1)
                self.size = (image.shape[1], image.shape[0])
                self.fps.tick(t)
                count += 1
                if count % 15 == 0:  # cheap: look at 1 pixel in 256
                    self.brightness = float(image[::16, ::16].mean())
                self._out.put(Frame(t=t, image=image))
        finally:
            cap.release()
            self._out.close()
