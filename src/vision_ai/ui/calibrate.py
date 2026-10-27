"""`python -m vision_ai --calibrate`: measure YOUR open-hand and pinch numbers."""

from __future__ import annotations

import time

from vision_ai.config import calibration
from vision_ai.core.pipeline import Pipeline
from vision_ai.gestures.calibrator import Calibrator
from vision_ai.ui.preview import draw


def run_calibration(pipeline: Pipeline, box) -> int:
    import cv2

    window = "Vision AI calibration"
    cal = Calibrator()
    seq = 0
    last_step = -1
    while not cal.done:
        got = pipeline.output.get(seq, timeout=0.1)
        if got is not None:
            out, seq = got
            cal.feed(time.monotonic(), out.pose)
            if cal.index != last_step and not cal.done:
                last_step = cal.index
            cur = cal.current
            if cur is not None and out.frame.image is not None:
                img = draw(out, pipeline, box, controlling=False)
                left = cal.seconds_left(time.monotonic())
                cv2.rectangle(
                    img, (0, img.shape[0] - 50), (img.shape[1], img.shape[0]), (0, 0, 0), -1
                )
                cv2.putText(img, f"{cur[1]}  ({left:.0f})", (10, img.shape[0] - 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)  # fmt: skip
                cv2.imshow(window, img)
        if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
            print("Calibration cancelled.")
            return 1
    cv2.destroyWindow(window)
    res = cal.result()
    for line in res.lines:
        print("  " + line)
    if not res.ok:
        return 1
    print(f"Saved: {calibration.save(res.values)}")
    return 0
