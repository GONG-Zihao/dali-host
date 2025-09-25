from __future__ import annotations

from .base import Transport


class SerialGateway(Transport):
    """占位 Serial Transport，实现留待未来拓展。"""

    def __init__(self, port: str, baudrate: int = 19200, timeout: float = 0.8):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

    def connect(self) -> None:  # pragma: no cover - 未实现
        raise NotImplementedError("SerialGateway 仍未实现")

    def disconnect(self) -> None:  # pragma: no cover - 未实现
        raise NotImplementedError("SerialGateway 仍未实现")

    def send(self, frame: bytes) -> None:  # pragma: no cover - 未实现
        raise NotImplementedError("SerialGateway 仍未实现")

    def recv(self, timeout: float = 0.5) -> bytes | None:  # pragma: no cover - 未实现
        raise NotImplementedError("SerialGateway 仍未实现")

    def is_connected(self) -> bool:
        return False

