"""Turns gesture events into real mouse actions."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Protocol

from vision_ai.licensing.features import gesture_for_event

log = logging.getLogger(__name__)


class InputBackend(Protocol):
    def button(self, which: str, down: bool) -> None: ...
    def wheel(self, delta: int, horizontal: bool = False) -> None: ...
    def key(self, name: str, down: bool) -> None: ...


class WindowsBackend:
    def button(self, which: str, down: bool) -> None:
        from vision_ai.actions import win_input

        win_input.button(which, down)

    def wheel(self, delta: int, horizontal: bool = False) -> None:
        from vision_ai.actions import win_input

        win_input.wheel(delta, horizontal)

    def key(self, name: str, down: bool) -> None:
        from vision_ai.actions import win_input

        win_input.key(name, down)


class Dispatcher:
    """`allowed(gesture_id)` says if a gesture may run (plan + user switches). None = all."""

    def __init__(
        self,
        backend: InputBackend,
        on_toggle_pause: Callable[[], None],
        allowed: Callable[[str], bool] | None = None,
        on_event: Callable[[tuple], None] | None = None,
    ) -> None:
        self._b = backend
        self._toggle = on_toggle_pause
        self._allowed = allowed or (lambda _g: True)
        self._on_event = on_event  # lets the UI flash a ring (called for events that ran)
        self.left_down = False
        self._drag_denied = False

    def handle(self, events: Iterable[tuple], paused: bool) -> None:
        for ev in events:
            kind = ev[0]
            if kind == "toggle_pause":  # works while paused, so you can always resume
                if paused or self._allowed("pause"):
                    self._toggle()
                continue
            if paused:
                continue
            gesture = gesture_for_event(ev)
            if gesture is not None and not self._allowed(gesture):
                self._denied(ev)
                continue
            try:
                self._run(ev)
            except OSError as exc:
                log.warning("input failed for %s: %s", ev, exc)
                continue
            if self._on_event is not None:
                self._on_event(ev)

    def _denied(self, ev: tuple) -> None:
        """A gesture that is off (free plan or switched off). A held pinch that would have
        been a drag still gives a plain click on release, so the user is never stuck."""
        if ev[0] == "down":
            self._drag_denied = True
        elif ev[0] == "up" and self._drag_denied:
            self._drag_denied = False
            self._run(("click", "left"))

    def _run(self, ev: tuple) -> None:
        kind = ev[0]
        if kind == "click":
            self._b.button(ev[1], True)
            self._b.button(ev[1], False)
        elif kind == "down":
            self._b.button("left", True)
            self.left_down = True
        elif kind == "up":
            self._drag_denied = False
            self.release_all()
        elif kind == "scroll":
            self._b.wheel(int(ev[1]))
        elif kind == "hscroll":
            self._b.wheel(int(ev[1]), horizontal=True)
        elif kind in ("zoom", "zoom2"):  # Ctrl + wheel: zoom in browsers, Photos, Word, PDF...
            self._with_keys(("ctrl",), lambda: self._b.wheel(int(ev[1])))
        elif kind == "home":  # Task View
            self._with_keys(("win",), lambda: self._tap_key("tab"))

    def _tap_key(self, name: str) -> None:
        self._b.key(name, True)
        self._b.key(name, False)

    def _with_keys(self, keys: tuple[str, ...], action: Callable[[], None]) -> None:
        pressed: list[str] = []
        try:
            for k in keys:
                self._b.key(k, True)
                pressed.append(k)
            action()
        finally:
            for k in reversed(pressed):
                try:
                    self._b.key(k, False)
                except OSError as exc:
                    log.warning("could not release key %s: %s", k, exc)

    def release_all(self) -> None:
        """Never leave the mouse button stuck down (pause, quit, hand lost)."""
        if self.left_down:
            self.left_down = False
            try:
                self._b.button("left", False)
            except OSError as exc:
                log.warning("could not release the mouse button: %s", exc)
