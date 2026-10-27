"""Entry point:  python -m vision_ai [--check | --debug | --cursor]"""

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
    p.add_argument("--camera", type=int, default=0, help="camera number (default 0)")
    p.add_argument("--backend", choices=["dshow", "msmf", "auto"], help="camera backend")
    p.add_argument("--size", help="camera picture size, for example 640x480")
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
    from vision_ai.core.tracker import find_model

    model = find_model()
    if model is None:
        print("Hand model not found. Run:  python scripts/download_model.py")
        return 2

    from vision_ai.actions import win_input
    from vision_ai.core.pipeline import Pipeline
    from vision_ai.gestures.cursor_controller import CursorController
    from vision_ai.gestures.cursor_mapper import CursorMapper, Rect
    from vision_ai.platform.dpi import enable_dpi_awareness
    from vision_ai.ui.preview import run_preview

    cursor_cfg = replace(CursorConfig(), main_hand=args.main_hand)
    controller = mover = None
    if control:
        if sys.platform != "win32":
            print("Mouse control only works on Windows. Use --debug here.")
            return 2
        enable_dpi_awareness()
        screen = win_input.virtual_screen_rect()
        controller = CursorController(CursorMapper(Rect(*cursor_cfg.box), screen), cursor_cfg)

        def mover(x: int, y: int) -> None:
            win_input.move_abs(x, y, screen)

    else:
        enable_dpi_awareness()

    pipe = Pipeline(camera, TrackerConfig(), cursor_cfg, model, controller, mover)
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
        reason = run_preview(pipe, cursor_cfg.box, control, seconds)
        print(f"Stopped: {reason}")
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
    if args.debug or args.cursor:
        return run_app(args, camera, control=args.cursor)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
