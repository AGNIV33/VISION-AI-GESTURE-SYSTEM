"""`python -m vision_ai --check`: tells the user if their PC is ready."""

from __future__ import annotations

import platform
import struct
import sys
import time

from vision_ai.config.defaults import CameraConfig, TrackerConfig

OK, WARN, FAIL = "OK  ", "WARN", "FAIL"


def _line(status: str, name: str, detail: str = "") -> None:
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))


def run_checks(camera: CameraConfig, tracker: TrackerConfig) -> int:
    failed = False

    bits = struct.calcsize("P") * 8
    _line(
        OK if sys.version_info >= (3, 10) and bits == 64 else FAIL,
        "Python",
        f"{platform.python_version()} ({bits}-bit)",
    )
    _line(
        OK if sys.platform == "win32" else WARN,
        "Operating system",
        platform.platform()
        + ("" if sys.platform == "win32" else "  (mouse control needs Windows)"),
    )

    try:
        import cv2
        import mediapipe as mp
        import numpy as np

        _line(
            OK,
            "Libraries",
            f"numpy {np.__version__}, opencv {cv2.__version__}, mediapipe {mp.__version__}",
        )
    except ImportError as exc:
        _line(FAIL, "Libraries", f"{exc}  -> run: pip install -e .")
        return 1

    from vision_ai.core.tracker import create_landmarker, find_model

    model = find_model()
    if model is None:
        _line(FAIL, "Hand model", "not found -> run: python scripts/download_model.py")
        failed = True
    else:
        _line(OK, "Hand model", str(model))

    from vision_ai.core.capture import open_camera

    cap, backend = open_camera(camera)
    if cap is None:
        _line(
            FAIL,
            "Camera",
            f"cannot open camera {camera.index} (close other apps that use it, or try --camera 1)",
        )
        return 1

    try:
        # 1) raw camera speed
        frames, t0, shape = 0, time.monotonic(), None
        while time.monotonic() - t0 < 2.0:
            ok, img = cap.read()
            if ok:
                frames += 1
                shape = img.shape
        secs = time.monotonic() - t0
        if not frames or shape is None:
            _line(FAIL, "Camera", "opened but sent no pictures")
            return 1
        fps = frames / secs
        _line(
            OK if fps >= 25 else WARN,
            "Camera speed",
            f"{fps:.1f} fps at {shape[1]}x{shape[0]} (backend id {backend})"
            + ("" if fps >= 25 else "  -> low; try better light, or --backend msmf"),
        )

        # 2) hand tracking speed
        if model is not None:
            import mediapipe as mp

            print("      Hold your hand in front of the camera for 3 seconds...")
            seen = total = 0
            infer_ms = 0.0
            last_ts = -1
            with create_landmarker(model, tracker) as lm:
                t_end = time.monotonic() + 3.0
                while time.monotonic() < t_end:
                    ok, img = cap.read()
                    if not ok:
                        continue
                    img = cv2.flip(img, 1)
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    ts = max(int(time.monotonic() * 1000), last_ts + 1)
                    last_ts = ts
                    a = time.monotonic()
                    res = lm.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts
                    )
                    infer_ms += (time.monotonic() - a) * 1000
                    total += 1
                    seen += 1 if res.hand_landmarks else 0
            if total:
                avg = infer_ms / total
                _line(OK if avg < 25 else WARN, "Hand tracking speed", f"{avg:.1f} ms per picture")
                _line(
                    OK if seen else WARN,
                    "Hand seen",
                    f"in {seen} of {total} pictures"
                    + ("" if seen else "  -> was your hand in view? check the light"),
                )
    finally:
        cap.release()

    print(
        "\nAll required checks passed."
        if not failed
        else "\nFix the FAIL items above, then run --check again."
    )
    return 1 if failed else 0
