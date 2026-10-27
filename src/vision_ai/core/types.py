"""Data shared between threads."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class LM:
    """MediaPipe hand landmark indices (21 points)."""

    WRIST = 0
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_TIP = 20


@dataclass(frozen=True)
class Hand:
    side: str  # "left" or "right" as the USER sees their own hand
    landmarks: np.ndarray  # (21, 3) image-normalized: x, y in 0..1 (mirrored view), z relative
    world: np.ndarray  # (21, 3) metres, origin near the hand centre
    score: float  # handedness confidence
    aspect: float = 1.0  # picture width / height (x and y are scaled separately)


PALM_POINTS = (LM.INDEX_MCP, LM.MIDDLE_MCP, LM.RING_MCP, LM.PINKY_MCP)


def aim_point(hand: Hand) -> tuple[float, float]:
    """Steady aim spot: the middle of the four knuckles. Averaging 4 points cancels most
    of the random shake of a single point, and pinching does not move it."""
    p = hand.landmarks[list(PALM_POINTS), :2].mean(axis=0)
    return float(p[0]), float(p[1])


@dataclass(frozen=True)
class HandFrame:
    t: float  # time the camera frame was grabbed (time.monotonic)
    done_t: float  # time tracking finished
    hands: tuple[Hand, ...]
    image: np.ndarray | None = None  # mirrored BGR frame (only kept for the preview)

    @property
    def latency_s(self) -> float:
        return self.done_t - self.t

    def hand(self, side: str) -> Hand | None:
        for h in self.hands:
            if h.side == side:
                return h
        return None


@dataclass(frozen=True)
class Frame:
    t: float
    image: np.ndarray  # BGR
