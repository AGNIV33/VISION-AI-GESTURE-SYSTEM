"""Per-picture hand measurements used by the gesture recognizer."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vision_ai.config.defaults import GestureConfig
from vision_ai.core.types import LM, Hand
from vision_ai.gestures.features import pinch_ratio

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


def _finger_state(hand: Hand, joint: int, tip: int, cfg: GestureConfig) -> int:
    wrist = hand.world[LM.WRIST]
    d_tip = float(np.linalg.norm(hand.world[tip] - wrist))
    d_joint = max(float(np.linalg.norm(hand.world[joint] - wrist)), 1e-6)
    r = d_tip / d_joint
    if r > cfg.finger_extended:
        return EXT
    if r < cfg.finger_folded:
        return FOLD
    return UNKNOWN


def read_pose(hand: Hand, cfg: GestureConfig) -> HandPose:
    fingers = tuple(_finger_state(hand, j, t, cfg) for j, t in _FINGERS)
    return HandPose(
        pinch_index=pinch_ratio(hand, LM.THUMB_TIP, LM.INDEX_TIP),
        pinch_middle=pinch_ratio(hand, LM.THUMB_TIP, LM.MIDDLE_TIP),
        fingers=fingers,  # type: ignore[arg-type]
    )
