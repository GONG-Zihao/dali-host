"""占位的本地 API 框架。后续可根据需要实现 REST/WebSocket 服务。"""

from __future__ import annotations


class LocalAPIServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 5589):
        self.host = host
        self.port = port

    def start(self):  # pragma: no cover - 未实现
        raise NotImplementedError("Local API server 尚未实现")

    def stop(self):  # pragma: no cover - 未实现
        raise NotImplementedError("Local API server 尚未实现")

