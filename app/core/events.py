from __future__ import annotations
from PySide6.QtCore import QObject, Signal

class EventBus(QObject):
    connection_changed = Signal(bool)  # True=已连接，False=未连接

bus = EventBus()
