"""`python -m vision_ai --calibrate`: measure YOUR open-hand and pinch numbers."""

from __future__ import annotations

import time

from vision_ai.config import calibration
from vision_ai.core.pipeline import Pipeline
from vision_ai.ui.preview import draw

STEPS = (
    ("open", "Hold your hand OPEN, fingers apart", 4.0),
    ("index", "TOUCH thumb + INDEX finger tips and hold", 4.0),
    ("open2", "OPEN your hand again", 3.0),
    ("middle", "TOUCH thumb + MIDDLE finger tips and hold", 4.0),
)
SETTLE_S = 1.0  # ignore the first second of each step while you change your hand


def run_calibration(pipeline: Pipeline, box) -> int:
    import cv2

    window = "Vision AI calibration"
    values: dict[str, list[tuple[float, float]]] = {name: [] for name, _, _ in STEPS}
    seq = 0
    for name, text, secs in STEPS:
        start = time.monotonic()
        while time.monotonic() - start < secs:
            got = pipeline.output.get(seq, timeout=0.1)
            if got is not None:
                out, seq = got
                elapsed = time.monotonic() - start
                if out.pose is not None and elapsed > SETTLE_S:
                    values[name].append((out.pose.pinch_index, out.pose.pinch_middle))
                if out.frame.image is not None:
                    img = draw(out, pipeline, box, controlling=False)
                    left = secs - elapsed
                    cv2.rectangle(img, (0, img.shape[0] - 50), (img.shape[1], img.shape[0]),
                                  (0, 0, 0), -1)  # fmt: skip
                    cv2.putText(img, f"{text}  ({left:.0f})", (10, img.shape[0] - 18),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)  # fmt: skip
                    cv2.imshow(window, img)
            if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
                print("Calibration cancelled.")
                return 1
        print(f"  {name}: {len(values[name])} pictures with a hand")
    cv2.destroyWindow(window)

    open_idx = [v[0] for v in values["open"] + values["open2"]]
    open_mid = [v[1] for v in values["open"] + values["open2"]]
    pinch_idx = [v[0] for v in values["index"]]
    pinch_mid = [v[1] for v in values["middle"]]

    def show(label: str, vals: list[float]) -> None:
        if vals:
            print(f"  {label}: lowest {min(vals):.2f}, highest {max(vals):.2f}")

    show("open hand  (thumb-index)", open_idx)
    show("index pinch (thumb-index)", pinch_idx)
    show("open hand  (thumb-middle)", open_mid)
    show("middle pinch (thumb-middle)", pinch_mid)

    idx = calibration.thresholds(open_idx, pinch_idx)
    mid = calibration.thresholds(open_mid, pinch_mid)
    if idx is None:
        print("Could not tell your open hand from your pinch. Use better light, keep your")
        print("hand inside the blue box, and run --calibrate again.")
        return 1
    result = {
        "pinch_on": idx[0],
        "pinch_off": idx[1],
        "arm_on": idx[2],
        "arm_off": idx[3],
    }
    if mid is not None:
        result.update({"mid_pinch_on": mid[0], "mid_pinch_off": mid[1]})
    else:
        print("Middle-finger pinch was unclear; right click keeps the default numbers.")
    path = calibration.save({k: round(v, 3) for k, v in result.items()})
    print(f"Saved: {path}")
    print(f"Click when thumb-index is below {idx[0]:.2f}, release above {idx[1]:.2f}.")
    return 0
