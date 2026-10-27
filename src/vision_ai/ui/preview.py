"""Debug preview window (OpenCV). The real Qt UI comes in Phase 6."""

from __future__ import annotations

import time

import numpy as np

from vision_ai.core.pipeline import EngineOutput, Pipeline
from vision_ai.core.types import LM

HAND_EDGES = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
)

PREVIEW_WIDTH = 640

WINDOW = "Vision AI debug  (Esc/Q = quit, P = pause/resume mouse control)"


def draw(
    out: EngineOutput,
    pipeline: Pipeline,
    box: tuple[float, float, float, float],
    controlling: bool,
) -> np.ndarray:
    import cv2

    image = out.frame.image
    h, w = image.shape[:2]
    if w > PREVIEW_WIDTH:  # a smaller window is much cheaper to draw
        h = round(h * PREVIEW_WIDTH / w)
        w = PREVIEW_WIDTH
        image = cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA)
    else:
        image = image.copy()

    bx, by, bw, bh = box
    cv2.rectangle(
        image,
        (int(bx * w), int(by * h)),
        (int((bx + bw) * w), int((by + bh) * h)),
        (255, 200, 80),
        1,
    )

    for hand in out.frame.hands:
        pts = [(int(p[0] * w), int(p[1] * h)) for p in hand.landmarks]
        for a, b in HAND_EDGES:
            cv2.line(image, pts[a], pts[b], (80, 220, 80), 2)
        for p in pts:
            cv2.circle(image, p, 3, (255, 255, 255), -1)
        aim = pts[LM.INDEX_MCP]
        cv2.circle(image, aim, 8, (0, 140, 255), 2)
        cv2.putText(
            image,
            hand.side,
            (pts[LM.WRIST][0], pts[LM.WRIST][1] + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2,
        )

    lines = [
        f"camera {pipeline.capture.fps.rate:4.1f} fps"
        f"   tracker {pipeline.tracker.fps.rate:4.1f} fps",
        f"delay camera->tracked {out.frame.latency_s * 1000:4.0f} ms"
        f"   inference {pipeline.tracker.infer_ms:4.1f} ms",
        f"hands: {len(out.frame.hands)}"
        + (f"   pinch(thumb-index): {out.pinch:.2f}" if out.pinch is not None else ""),
    ]
    if controlling:
        lines.append("MOUSE CONTROL: ON" if pipeline.control_enabled else "MOUSE CONTROL: PAUSED")
    else:
        lines.append("tracking only (mouse not controlled)")
    for i, text in enumerate(lines):
        cv2.putText(image, text, (8, 20 + 20 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(
            image, text, (8, 20 + 20 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
        )
    return image


def run_preview(
    pipeline: Pipeline,
    box: tuple[float, float, float, float],
    controlling: bool,
    seconds: float = 0.0,
) -> str:
    """Show the window until the user quits, an error happens, or `seconds` pass.
    Returns the reason it stopped."""
    import cv2

    start = time.monotonic()
    seq = 0
    shown = False  # the window may report 'not visible' until the first picture is drawn
    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    while True:
        got = pipeline.output.get(seq, timeout=0.1)
        if got is not None:
            out, seq = got
            if out.frame.image is not None:
                cv2.imshow(WINDOW, draw(out, pipeline, box, controlling))
                shown = True
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q"), ord("Q")):
            return "closed by user"
        if key in (ord("p"), ord("P")) and controlling:
            pipeline.set_control_enabled(not pipeline.control_enabled)
        if shown and cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
            return "window closed"
        err = pipeline.first_error()
        if err:
            return err
        if seconds and time.monotonic() - start >= seconds:
            return f"time limit ({seconds:.0f} s) reached"
