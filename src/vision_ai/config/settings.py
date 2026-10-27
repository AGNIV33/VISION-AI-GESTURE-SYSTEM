"""User settings: one JSON file in %APPDATA%\\VisionAI\\settings.json (pure Python)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path

from vision_ai.config.calibration import data_dir
from vision_ai.config.defaults import CameraConfig, CursorConfig, GestureConfig, TrackerConfig

log = logging.getLogger(__name__)


@dataclass
class Settings:
    main_hand: str = "right"  # "right" | "left"
    camera_index: int = 0
    mode: str = "absolute"  # "absolute" (hand position = screen position) | "trackpad"
    smoothness: int = 5  # 1..10, higher = steadier but a little slower
    responsiveness: int = 5  # 1..10, higher = less lag on fast moves (a bit more shake)
    sensitivity: int = 5  # 1..10, trackpad mode: how far the cursor goes per hand move
    gestures_off: list[str] = field(default_factory=list)  # gesture ids the user switched off
    two_hand: bool = False  # track 2 hands (needed for two-hand zoom, a bit slower)
    start_with_windows: bool = False
    show_overlay: bool = True  # small ring that flashes on click
    pause_hotkey: bool = True  # Ctrl+Alt+P pauses / resumes from anywhere
    first_run_done: bool = False
    tray_tip_shown: bool = False
    license_key: str = ""


def settings_path() -> Path:
    return data_dir() / "settings.json"


def _clamp(v: object, lo: int, hi: int, default: int) -> int:
    try:
        return min(max(int(v), lo), hi)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return default


def sanitize(s: Settings) -> Settings:
    """Fix out-of-range or wrong-type values (a hand-edited file must not break the app)."""
    d = Settings()
    s.main_hand = s.main_hand if s.main_hand in ("right", "left") else d.main_hand
    s.mode = s.mode if s.mode in ("absolute", "trackpad") else d.mode
    s.camera_index = _clamp(s.camera_index, 0, 9, 0)
    s.smoothness = _clamp(s.smoothness, 1, 10, 5)
    s.responsiveness = _clamp(s.responsiveness, 1, 10, 5)
    s.sensitivity = _clamp(s.sensitivity, 1, 10, 5)
    s.gestures_off = [str(g) for g in s.gestures_off] if isinstance(s.gestures_off, list) else []
    s.license_key = s.license_key if isinstance(s.license_key, str) else ""
    return s


def load(path: Path | None = None) -> Settings:
    path = path or settings_path()
    s = Settings()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            known = {f.name: f for f in fields(Settings)}
            for k, v in data.items():
                if k in known:
                    setattr(s, k, v)
        except (OSError, ValueError, AttributeError) as exc:
            log.warning("ignoring broken settings file %s: %s", path, exc)
            s = Settings()
    return sanitize(s)


def save(s: Settings, path: Path | None = None) -> Path:
    """Write safely: temp file first, then replace, so a crash cannot leave half a file."""
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(sanitize(s)), indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


# --- settings -> the numbers the engine uses ---------------------------------------------


def cursor_params(s: Settings) -> tuple[float, float]:
    """(min_cutoff, beta) for the One Euro filter. The middle (5, 5) is the tuned default."""
    return 1.0 * 1.25 ** (5 - s.smoothness), 0.05 * 1.5 ** (s.responsiveness - 5)


def trackpad_gain(s: Settings) -> float:
    """Screen widths per full box width of hand movement in trackpad mode."""
    return 0.6 * 1.3 ** (s.sensitivity - 5)


def make_configs(
    s: Settings,
) -> tuple[CameraConfig, TrackerConfig, CursorConfig, GestureConfig]:
    from vision_ai.config.calibration import load_gesture_config

    min_cutoff, beta = cursor_params(s)
    camera = replace(CameraConfig(), index=s.camera_index)
    tracker = replace(TrackerConfig(), num_hands=2 if s.two_hand else 1)
    cursor = replace(CursorConfig(), main_hand=s.main_hand, min_cutoff=min_cutoff, beta=beta)
    gestures, _ = load_gesture_config()
    return camera, tracker, cursor, gestures
