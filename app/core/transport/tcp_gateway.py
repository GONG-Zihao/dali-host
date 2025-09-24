from __future__ import annotations
import socket
import logging
from .base import Transport

class TcpGateway(Transport):
    """简化版 TCP 透传：把2字节DALI前向帧直接写到网关。
    实际网关若有自定义封包，可在此改装（例如加前缀/校验/长度）。
    """
    def __init__(self, host: str, port: int, timeout: float = 0.8):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._log = logging.getLogger("TcpGateway")

    def connect(self) -> None:
        if self._sock:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        s.connect((self.host, self.port))
        self._sock = s
        self._log.info("TCP connected %s:%s", self.host, self.port)

    def disconnect(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None
                self._log.info("TCP disconnected")

    def send(self, frame: bytes) -> None:
        if not self._sock:
            raise RuntimeError("Not connected")
        # 大多数网关支持短包直发；若需要可在此加协议头
        self._log.info("SEND %s", frame.hex(" "))
        self._sock.sendall(frame)

    def recv(self, timeout: float = 0.5) -> bytes | None:
        if not self._sock:
            return None
        self._sock.settimeout(timeout)
        try:
            data = self._sock.recv(1024)
            if data:
                self._log.info("RECV %s", data.hex(" "))
            return data or None
        except socket.timeout:
            return None

    def is_connected(self) -> bool:
        return self._sock is not None
