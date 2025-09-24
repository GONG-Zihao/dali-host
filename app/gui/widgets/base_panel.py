from __future__ import annotations
from typing import Iterable
from PySide6.QtWidgets import QWidget, QStatusBar
from app.core.events import bus
from app.i18n import i18n

class BasePanel(QWidget):
    """
    - show_msg(): 安全状态栏提示（不会因状态栏被替换而崩）
    - register_send_widgets(): 注册需要随“连接状态”启/禁的按钮、输入等
    """
    def __init__(self, controller, statusbar: QStatusBar | None):
        super().__init__()
        self.ctrl = controller
        self._statusbar = statusbar
        self._send_widgets: list[QWidget] = []
        bus.connection_changed.connect(self._on_conn_changed)

    # 统一状态栏提示
    def show_msg(self, text: str, ms: int = 2000):
        try:
            sb = self._statusbar or (self.window().statusBar() if self.window() else None)
            if sb:
                if getattr(i18n, "lang", "zh") == "en":
                    text = i18n.translate_text(text)
                sb.showMessage(text, ms)
        except Exception:
            pass

    # 注册需要“随连接状态启/禁”的控件
    def register_send_widgets(self, widgets: Iterable[QWidget]):
        self._send_widgets.extend(widgets)
        self._on_conn_changed(self.ctrl.is_connected())

    def _on_conn_changed(self, connected: bool):
        for w in self._send_widgets:
            try:
                w.setEnabled(bool(connected))
            except Exception:
                pass
