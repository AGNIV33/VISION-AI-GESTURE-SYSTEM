"""Entry point. No arguments = tray app; --check, --debug, --cursor, --calibrate = tools."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace

from vision_ai.config.defaults import CameraConfig, CursorConfig, TrackerConfig


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vision_ai", description="Webcam hand-gesture control")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="test camera, model and speed")
    mode.add_argument("--debug", action="store_true", help="show hand tracking (mouse NOT moved)")
    mode.add_argument("--cursor", action="store_true", help="show tracking AND move the mouse")
    mode.add_argument("--calibrate", action="store_true", help="measure your pinch numbers")
    p.add_argument("--background", action="store_true", help="tray app: start hidden")
    p.add_argument("--camera", type=int, default=0, help="camera number (default 0)")
    p.add_argument("--backend", choices=["dshow", "msmf", "auto"], help="camera backend")
    p.add_argument("--size", help="camera picture size, for example 640x480")
    p.add_argument("--hands", type=int, choices=[1, 2], default=1, help="hands to track")
    p.add_argument("--main-hand", choices=["right", "left"], default="right")
    p.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="auto-stop after N seconds (default 60 with --cursor, 0 = never)",
    )
    p.add_argument("--verbose", action="store_true")
    return p


def run_app(args: argparse.Namespace, camera: CameraConfig, control: bool) -> int:
    """The developer tools: --debug, --cursor, --calibrate (OpenCV window)."""
    from vision_ai.core.tracker import find_model

    model = find_model()
    if model is None:
        print("Hand model not found. Run:  python scripts/download_model.py")
        return 2

    from vision_ai.config.calibration import load_gesture_config
    from vision_ai.core.runtime import build_pipeline
    from vision_ai.platform.dpi import enable_dpi_awareness
    from vision_ai.ui.preview import run_preview

    cursor_cfg = replace(CursorConfig(), main_hand=args.main_hand)
    gesture_cfg, calibrated = load_gesture_config()
    if not calibrated and not args.calibrate:
        print("Tip: run  python -m vision_ai --calibrate  once so clicks fit your hand.")
    enable_dpi_awareness()
    tracker_cfg = replace(TrackerConfig(), num_hands=args.hands)

    def on_pause(paused: bool) -> None:
        print("Paused (make a fist again to resume)" if paused else "Resumed")

    try:
        pipe = build_pipeline(
            camera, tracker_cfg, cursor_cfg, gesture_cfg, model,
            control=control, on_pause_changed=on_pause,
        )  # fmt: skip
    except OSError as exc:
        print(f"{exc}. Use --debug here.")
        return 2
    pipe.start()
    try:
        pipe.capture.opened.wait(timeout=15)
        if pipe.capture.error:
            print(pipe.capture.error)
            return 1
        seconds = args.seconds if args.seconds is not None else (60.0 if control else 0.0)
        if control:
            print("Mouse control is ON. Stop with Esc/Q in the preview window, or Ctrl+C here.")
            if seconds:
                print(f"It stops by itself after {seconds:.0f} seconds (change with --seconds).")
        if args.calibrate:
            from vision_ai.ui.calibrate import run_calibration

            return run_calibration(pipe, cursor_cfg.box)
        reason, summary = run_preview(pipe, cursor_cfg.box, control, seconds)
        print(f"Stopped: {reason}")
        print(f"SPEED SUMMARY: {summary}")
        return 0 if reason in ("closed by user", "window closed") or "time limit" in reason else 1
    except KeyboardInterrupt:
        print("Stopped: Ctrl+C")
        return 0
    finally:
        pipe.stop()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    camera = CameraConfig(index=args.camera)
    if args.backend:
        camera = replace(camera, backend=args.backend)
    if args.size:
        try:
            w, h = (int(v) for v in args.size.lower().split("x"))
        except ValueError:
            parser.error("--size must look like 640x480")
        camera = replace(camera, width=w, height=h)

    if args.check:
        from vision_ai.core.checks import run_checks

        return run_checks(camera, TrackerConfig())
    if args.debug or args.cursor or args.calibrate:
        return run_app(args, camera, control=args.cursor)
    from vision_ai.app.main import run

    return run(background=args.background)


if __name__ == "__main__":
    sys.exit(main())
