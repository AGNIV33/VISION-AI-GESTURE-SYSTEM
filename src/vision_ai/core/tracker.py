"""MediaPipe hand tracking thread."""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np

from vision_ai.config.defaults import TrackerConfig
from vision_ai.core.slot import LatestSlot, RateMeter
from vision_ai.core.types import Frame, Hand, HandFrame

log = logging.getLogger(__name__)

MODEL_NAME = "hand_landmarker.task"


def find_model() -> Path | None:
    """Look for the model: env var, project assets/, then the user data folder."""
    candidates: list[Path] = []
    env = os.environ.get("VISION_AI_MODEL")
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidates.append(parent / "assets" / "models" / MODEL_NAME)
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(Path(local) / "VisionAI" / "models" / MODEL_NAME)
    for c in candidates:
        if c.is_file():
            return c
    return None


def result_to_hands(result) -> tuple[Hand, ...]:
    """Convert a MediaPipe HandLandmarkerResult into our Hand objects.

    The camera image is mirrored BEFORE tracking, so MediaPipe's handedness label
    already matches the user's real hand.
    """
    hands: list[Hand] = []
    for i, lms in enumerate(result.hand_landmarks):
        landmarks = np.array([[p.x, p.y, p.z] for p in lms], dtype=np.float32)
        world = np.array(
            [[p.x, p.y, p.z] for p in result.hand_world_landmarks[i]], dtype=np.float32
        )
        cat = result.handedness[i][0]
        side = "right" if cat.category_name.lower() == "right" else "left"
        hands.append(Hand(side=side, landmarks=landmarks, world=world, score=float(cat.score)))
    return tuple(hands)


def prepare_image(image: np.ndarray, max_width: int) -> np.ndarray:
    """Shrink (keeping the shape) and convert BGR -> RGB for MediaPipe."""
    import cv2

    h, w = image.shape[:2]
    if max_width and w > max_width:
        image = cv2.resize(
            image, (max_width, round(h * max_width / w)), interpolation=cv2.INTER_AREA
        )
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def create_landmarker(model_path: Path, cfg: TrackerConfig):
    """Build a MediaPipe HandLandmarker in VIDEO mode (use as a context manager)."""
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions

    options = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=cfg.num_hands,
        min_hand_detection_confidence=cfg.min_detection_confidence,
        min_hand_presence_confidence=cfg.min_presence_confidence,
        min_tracking_confidence=cfg.min_tracking_confidence,
    )
    return vision.HandLandmarker.create_from_options(options)


class TrackerThread(threading.Thread):
    def __init__(
        self,
        frames: LatestSlot[Frame],
        out: LatestSlot[HandFrame],
        model_path: Path,
        cfg: TrackerConfig,
        keep_image: bool = True,
    ) -> None:
        super().__init__(name="tracker", daemon=True)
        self._in = frames
        self._out = out
        self._model = model_path
        self._cfg = cfg
        self._keep_image = keep_image
        self._stop_evt = threading.Event()
        self.error: str | None = None
        self.fps = RateMeter()
        self.infer_ms = 0.0

    def stop(self) -> None:
        self._stop_evt.set()

    def run(self) -> None:
        try:
            self._loop()
        except Exception as exc:  # report to the UI instead of dying silently
            self.error = f"Tracker crashed: {exc}"
            log.exception("tracker crashed")
        finally:
            self._out.close()

    def _loop(self) -> None:
        import mediapipe as mp

        last_ts = -1
        seq = 0
        with create_landmarker(self._model, self._cfg) as landmarker:
            while not self._stop_evt.is_set():
                got = self._in.get(seq, timeout=0.2)
                if got is None:
                    if self._in.closed:
                        break
                    continue
                frame, seq = got
                rgb = prepare_image(frame.image, self._cfg.input_width)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ts = int(frame.t * 1000)
                if ts <= last_ts:  # MediaPipe needs strictly increasing timestamps
                    ts = last_ts + 1
                last_ts = ts
                t0 = time.monotonic()
                result = landmarker.detect_for_video(mp_image, ts)
                done = time.monotonic()
                self.infer_ms += 0.1 * ((done - t0) * 1000 - self.infer_ms)
                self.fps.tick(done)
                self._out.put(
                    HandFrame(
                        t=frame.t,
                        done_t=done,
                        hands=result_to_hands(result),
                        image=frame.image if self._keep_image else None,
                    )
                )
