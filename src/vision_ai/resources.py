"""Find bundled files (icons, model) both in the project folder and in an installed app."""

from __future__ import annotations

import sys
from pathlib import Path


def asset_path(relative: str) -> Path | None:
    """`relative` is like 'icons/logo.png' (inside the assets folder)."""
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidates.append(parent / "assets" / relative)
    exe_dir = Path(sys.executable).resolve().parent
    candidates += [exe_dir / "assets" / relative, exe_dir.parent / "assets" / relative]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "assets" / relative)
    for c in candidates:
        if c.is_file():
            return c
    return None
