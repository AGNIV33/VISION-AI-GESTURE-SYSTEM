"""Only one copy of the app may run. A second launch just wakes up the first one."""

from __future__ import annotations

import getpass

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def _name() -> str:
    return f"VisionAI-{getpass.getuser()}"


class SingleInstance(QObject):
    activated = Signal()  # another copy was started: show the Settings window

    def __init__(self, name: str | None = None) -> None:
        super().__init__()
        self._name = name or _name()
        self._server: QLocalServer | None = None

    def acquire(self) -> bool:
        """True = we are the first copy. False = another copy runs (it was told to show up)."""
        sock = QLocalSocket()
        sock.connectToServer(self._name)
        if sock.waitForConnected(300):
            sock.write(b"show")
            sock.waitForBytesWritten(300)
            sock.disconnectFromServer()
            return False
        QLocalServer.removeServer(self._name)  # a leftover from a crash
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        return self._server.listen(self._name)

    def _on_connection(self) -> None:
        assert self._server is not None
        conn = self._server.nextPendingConnection()
        if conn is not None:
            conn.readyRead.connect(lambda: (conn.readAll(), self.activated.emit()))
            conn.disconnected.connect(conn.deleteLater)

    def release(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None
