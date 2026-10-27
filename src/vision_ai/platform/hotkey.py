"""A global hotkey (works in any app): Ctrl+Alt+P pauses / resumes. Windows only."""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable

log = logging.getLogger(__name__)

MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x0001, 0x0002, 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012
VK_P = 0x50


class GlobalHotkey(threading.Thread):
    def __init__(self, callback: Callable[[], None], vk: int = VK_P) -> None:
        super().__init__(name="hotkey", daemon=True)
        self._cb = callback
        self._vk = vk
        self._tid = 0
        self.error: str | None = None
        self.ready = threading.Event()

    def run(self) -> None:
        if sys.platform != "win32":
            self.error = "Hotkeys only work on Windows"
            self.ready.set()
            return
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self._tid = kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, self._vk):
            self.error = "Ctrl+Alt+P is already used by another program"
            log.warning(self.error)
            self.ready.set()
            return
        self.ready.set()
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    try:
                        self._cb()
                    except Exception:  # never let a callback kill the hotkey thread
                        log.exception("hotkey callback failed")
        finally:
            user32.UnregisterHotKey(None, 1)

    def stop(self) -> None:
        if sys.platform == "win32" and self._tid:
            import ctypes

            ctypes.WinDLL("user32").PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
