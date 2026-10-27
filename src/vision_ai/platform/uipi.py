"""Windows blocks input sent to windows that run "as administrator" (UIPI).
Detect that so the app can tell the user instead of silently doing nothing."""

from __future__ import annotations

import sys


def _is_elevated_pid(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    adv.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    adv.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    proc = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not proc:
        return False  # cannot even open it: most likely a protected / elevated process
    try:
        token = wintypes.HANDLE()
        if not adv.OpenProcessToken(proc, 0x0008, ctypes.byref(token)):  # TOKEN_QUERY
            return False
        try:
            elevated = wintypes.DWORD()
            size = wintypes.DWORD()
            ok = adv.GetTokenInformation(  # TokenElevation = 20
                token, 20, ctypes.byref(elevated), ctypes.sizeof(elevated), ctypes.byref(size)
            )
            return bool(ok and elevated.value)
        finally:
            k32.CloseHandle(token)
    finally:
        k32.CloseHandle(proc)


def foreground_blocks_us() -> bool:
    """True if the window in front runs as administrator while we do not."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        if ctypes.windll.shell32.IsUserAnAdmin():
            return False  # we are admin too: nothing is blocked
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return _is_elevated_pid(pid.value) if pid.value else False
    except Exception:  # best effort only
        return False
