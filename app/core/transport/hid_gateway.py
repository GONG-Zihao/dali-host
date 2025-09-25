from __future__ import annotations

from .base import Transport


class HidGateway(Transport):
    """占位 HID Transport，实现留待未来拓展。"""

    def __init__(self, vendor_id: int | None = None, product_id: int | None = None, timeout: float = 0.8):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.timeout = timeout

    def connect(self) -> None:  # pragma: no cover - 未实现
        raise NotImplementedError("HidGateway 仍未实现")

    def disconnect(self) -> None:  # pragma: no cover - 未实现
        raise NotImplementedError("HidGateway 仍未实现")

    def send(self, frame: bytes) -> None:  # pragma: no cover - 未实现
        raise NotImplementedError("HidGateway 仍未实现")

    def recv(self, timeout: float = 0.5) -> bytes | None:  # pragma: no cover - 未实现
        raise NotImplementedError("HidGateway 仍未实现")

    def is_connected(self) -> bool:
        return False

