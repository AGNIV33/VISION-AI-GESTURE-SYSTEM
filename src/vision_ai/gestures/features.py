"""Hand measurements that do not depend on how far the hand is from the camera.

Distances use MediaPipe WORLD landmarks (metres, 3D) and are divided by the palm size,
so a pinch gives the same number near or far from the camera.
"""

from __future__ import annotations

import numpy as np

from vision_ai.core.types import LM, Hand

_EPS = 1e-6


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def palm_size(hand: Hand) -> float:
    """Wrist to middle-finger base, in metres."""
    return _dist(hand.world[LM.WRIST], hand.world[LM.MIDDLE_MCP])


def pinch_ratio(hand: Hand, a: int = LM.THUMB_TIP, b: int = LM.INDEX_TIP) -> float:
    """Distance between two landmarks divided by palm size (0 = touching)."""
    return _dist(hand.world[a], hand.world[b]) / max(palm_size(hand), _EPS)
