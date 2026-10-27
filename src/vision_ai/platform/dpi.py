"""Make Windows give us real pixel coordinates on scaled screens (125%, 150%...)."""

from __future__ import annotations

import ctypes
import sys


def enable_dpi_awareness() -> bool:
    """Call once at startup, before creating any window. Returns True if it was set."""
    if sys.platform != "win32":
        return False
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return True
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor (Windows 8.1+)
        return True
    except (AttributeError, OSError):
        return False
