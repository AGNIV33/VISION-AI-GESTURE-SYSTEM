"""Turns gesture events into real mouse actions."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Protocol

log = logging.getLogger(__name__)


class InputBackend(Protocol):
    def button(self, which: str, down: bool) -> None: ...
    def wheel(self, delta: int, horizontal: bool = False) -> None: ...


class WindowsBackend:
    def button(self, which: str, down: bool) -> None:
        from vision_ai.actions import win_input

        win_input.button(which, down)

    def wheel(self, delta: int, horizontal: bool = False) -> None:
        from vision_ai.actions import win_input

        win_input.wheel(delta, horizontal)


class Dispatcher:
    def __init__(self, backend: InputBackend, on_toggle_pause: Callable[[], None]) -> None:
        self._b = backend
        self._toggle = on_toggle_pause
        self.left_down = False

    def handle(self, events: Iterable[tuple], paused: bool) -> None:
        for ev in events:
            kind = ev[0]
            if kind == "toggle_pause":  # works even while paused, so you can resume
                self._toggle()
                continue
            if paused:
                continue
            try:
                if kind == "click":
                    self._b.button(ev[1], True)
                    self._b.button(ev[1], False)
                elif kind == "down":
                    self._b.button("left", True)
                    self.left_down = True
                elif kind == "up":
                    self.release_all()
                elif kind == "scroll":
                    self._b.wheel(int(ev[1]))
                elif kind == "hscroll":
                    self._b.wheel(int(ev[1]), horizontal=True)
            except OSError as exc:
                log.warning("input failed for %s: %s", ev, exc)

    def release_all(self) -> None:
        """Never leave the mouse button stuck down (pause, quit, hand lost)."""
        if self.left_down:
            self.left_down = False
            try:
                self._b.button("left", False)
            except OSError as exc:
                log.warning("could not release the mouse button: %s", exc)
