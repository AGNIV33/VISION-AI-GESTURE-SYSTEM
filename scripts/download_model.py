"""Download the official Google MediaPipe hand landmarker model.

Run on your Windows PC:  python scripts/download_model.py
Uses only the official Google file (Apache 2.0, commercial use allowed).
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
DEST = Path(__file__).resolve().parent.parent / "assets" / "models" / "hand_landmarker.task"
MIN_BYTES = 1_000_000  # the real file is several MB; smaller means a failed download


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and DEST.stat().st_size >= MIN_BYTES:
        print(f"Already there: {DEST} ({DEST.stat().st_size:,} bytes)")
        return 0
    print(f"Downloading {URL}")
    try:
        tmp = DEST.with_suffix(".part")
        urllib.request.urlretrieve(URL, tmp)
    except OSError as exc:
        print(f"FAILED: {exc}\nCheck your internet, then run this again.")
        return 1
    if tmp.stat().st_size < MIN_BYTES:
        tmp.unlink(missing_ok=True)
        print("FAILED: the downloaded file is too small. Run this again.")
        return 1
    tmp.replace(DEST)
    print(f"Saved: {DEST} ({DEST.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
