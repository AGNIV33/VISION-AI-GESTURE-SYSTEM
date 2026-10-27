"""Per-picture hand measurements used by the gesture recognizer.

Uses FLAT (2D) distances in the camera picture. The first version used MediaPipe's 3D
"world" points, but its depth guess is noisy from one webcam: on the owner's PC touching
fingertips measured 0.40-0.68 and overlapped with an open hand (2026-10-27). Touching
fingertips always overlap in the picture, so 2D is the reliable measure.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vision_ai.config.defaults import GestureConfig
from vision_ai.core.types import LM, Hand

EXT, FOLD, UNKNOWN = 1, -1, 0

# (middle joint, tip) for index, middle, ring, pinky
_FINGERS = ((6, 8), (10, 12), (14, 16), (18, 20))


@dataclass(frozen=True)
class HandPose:
    pinch_index: float  # thumb tip to index tip / palm size
    pinch_middle: float  # thumb tip to middle tip / palm size
    fingers: tuple[int, int, int, int]  # index, middle, ring, pinky: EXT / FOLD / UNKNOWN

    @property
    def is_fist(self) -> bool:
        return all(f == FOLD for f in self.fingers)

    @property
    def is_scroll_pose(self) -> bool:
        """Index and middle straight, ring and pinky curled (a 'peace sign')."""
        i, m, r, p = self.fingers
        return i == EXT and m == EXT and r == FOLD and p == FOLD


def _points(hand: Hand) -> np.ndarray:
    """2D points with x stretched by the picture shape, so distances are real."""
    return hand.landmarks[:, :2] * np.array([hand.aspect, 1.0], dtype=np.float32)


def _dist(p: np.ndarray, a: int, b: int) -> float:
    return float(np.linalg.norm(p[a] - p[b]))


def _finger_state(pts: np.ndarray, joint: int, tip: int, cfg: GestureConfig) -> int:
    r = _dist(pts, LM.WRIST, tip) / max(_dist(pts, LM.WRIST, joint), 1e-6)
    if r > cfg.finger_extended:
        return EXT
    if r < cfg.finger_folded:
        return FOLD
    return UNKNOWN


def read_pose(hand: Hand, cfg: GestureConfig) -> HandPose:
    pts = _points(hand)
    palm = max(_dist(pts, LM.WRIST, LM.MIDDLE_MCP), 1e-6)
    fingers = tuple(_finger_state(pts, j, t, cfg) for j, t in _FINGERS)
    return HandPose(
        pinch_index=_dist(pts, LM.THUMB_TIP, LM.INDEX_TIP) / palm,
        pinch_middle=_dist(pts, LM.THUMB_TIP, LM.MIDDLE_TIP) / palm,
        fingers=fingers,  # type: ignore[arg-type]
    )
