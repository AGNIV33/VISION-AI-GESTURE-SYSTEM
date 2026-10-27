from __future__ import annotations

import os

import numpy as np
import pytest

from vision_ai.core.types import LM, Hand, HandFrame

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # Qt tests run without a screen


def make_hand(side="right", index_mcp=(0.5, 0.5), thumb_index_gap=0.10, palm=0.09) -> Hand:
    """A fake hand. `palm` = wrist->middle-base in metres; `thumb_index_gap` in metres."""
    world = np.zeros((21, 3), dtype=np.float32)
    world[LM.MIDDLE_MCP] = (0.0, -palm, 0.0)
    world[LM.THUMB_TIP] = (0.0, -0.1, 0.0)
    world[LM.INDEX_TIP] = (thumb_index_gap, -0.1, 0.0)
    # picture points: same shape as the world points, placed at index_mcp
    lm = world + np.array([index_mcp[0], index_mcp[1], 0.0], dtype=np.float32)
    for i in (LM.MIDDLE_MCP, LM.RING_MCP, LM.PINKY_MCP):  # all knuckles at one spot
        lm[i] = lm[LM.INDEX_MCP]
    lm[LM.WRIST] = lm[LM.INDEX_MCP] + np.array([0.0, palm, 0.0], dtype=np.float32)  # keep palm size
    return Hand(side=side, landmarks=lm, world=world, score=0.99)


def make_frame(t, hands=()) -> HandFrame:
    return HandFrame(t=t, done_t=t + 0.03, hands=tuple(hands))


@pytest.fixture
def hand_factory():
    return make_hand
