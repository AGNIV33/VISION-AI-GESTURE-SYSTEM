"""A one-item mailbox that always holds only the NEWEST item.

Old items are overwritten, so a slow consumer never builds up lag.
"""

from __future__ import annotations

import threading
import time
from typing import Generic, TypeVar

T = TypeVar("T")


class LatestSlot(Generic[T]):
    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._item: T | None = None
        self._seq = 0
        self._closed = False

    def put(self, item: T) -> None:
        with self._cond:
            self._item = item
            self._seq += 1
            self._cond.notify_all()

    def get(self, after_seq: int = 0, timeout: float = 0.5) -> tuple[T, int] | None:
        """Wait for an item newer than `after_seq`. Returns (item, seq) or None."""
        with self._cond:
            self._cond.wait_for(lambda: self._seq > after_seq or self._closed, timeout)
            if self._seq > after_seq and self._item is not None:
                return self._item, self._seq
            return None

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()

    @property
    def closed(self) -> bool:
        return self._closed


class RateMeter:
    """Smoothed events-per-second counter."""

    def __init__(self, smoothing: float = 0.1) -> None:
        self._last: float | None = None
        self._dt: float | None = None
        self._k = smoothing

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        if self._last is not None:
            dt = now - self._last
            self._dt = dt if self._dt is None else self._dt + self._k * (dt - self._dt)
        self._last = now

    @property
    def rate(self) -> float:
        return 0.0 if not self._dt else 1.0 / self._dt
