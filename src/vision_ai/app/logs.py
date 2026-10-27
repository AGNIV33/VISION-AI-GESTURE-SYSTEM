"""Log file for the tray app: %APPDATA%\\VisionAI\\logs\\vision-ai.log (3 x 1 MB)."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from vision_ai.config.calibration import data_dir


def log_path() -> Path:
    return data_dir() / "logs" / "vision-ai.log"


def setup(verbose: bool = False) -> Path:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.addHandler(handler)
    return path
