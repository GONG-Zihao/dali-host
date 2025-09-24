from __future__ import annotations
from abc import ABC, abstractmethod
import time
import logging

class Transport(ABC):
    """传输抽象层：屏蔽 TCP/串口/HID 差异。"""

    @abstractmethod
    def connect(self) -> None: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def send(self, frame: bytes) -> None: ...
    @abstractmethod
    def recv(self, timeout: float = 0.5) -> bytes | None: ...
    @abstractmethod
    def is_connected(self) -> bool: ...

class MockTransport(Transport):
    """用于GUI联调与自动化测试的假设备。"""
    def __init__(self):
        self._connected = False
        self._log = logging.getLogger("MockTransport")
        self._last_sent: bytes | None = None

    def connect(self) -> None:
        self._connected = True
        self._log.info("Mock connected")

    def disconnect(self) -> None:
        self._connected = False
        self._log.info("Mock disconnected")

    def send(self, frame: bytes) -> None:
        self._last_sent = bytes(frame)
        self._log.info("SEND %s", frame.hex(" "))

    def recv(self, timeout: float = 0.5) -> bytes | None:
        import time
        time.sleep(min(timeout, 0.05))
        # 简单可重复的模拟：回一个1字节校验 (addr ^ data)
        if self._last_sent:
            b = (self._last_sent[0] ^ self._last_sent[1]) & 0xFF
            return bytes([b])
        return None

    def is_connected(self) -> bool:
        return self._connected
