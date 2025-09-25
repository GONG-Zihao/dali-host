from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QSlider,
    QGroupBox,
    QGridLayout,
    QSpinBox,
)
from PySide6.QtCore import Qt
from app.gui.widgets.base_panel import BasePanel
from app.gui.widgets.address_target import AddressTargetWidget
from app.i18n import tr, trf


class PanelDimming(BasePanel):
    """
    基本调光（ARC 0..254）：
    - 地址选择（广播/短址/组址）
    - 滑条 + 数字框联动
    - 快捷：最暗/中间/最亮
    - 发送
    """
    def __init__(self, controller, statusbar):
        super().__init__(controller, statusbar)
        self._log = logging.getLogger("PanelDimming")
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)

        self.addr_widget = AddressTargetWidget(self)
        root.addWidget(self.addr_widget)

        # 调光区
        self.box_dim = QGroupBox()
        dg = QGridLayout(self.box_dim)
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(0, 254); self.slider.setValue(128)
        self.spin = QSpinBox(); self.spin.setRange(0, 254); self.spin.setValue(128)
        # 双向联动
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)

        self.btn_min = QPushButton()
        self.btn_mid = QPushButton()
        self.btn_max = QPushButton()
        self.btn_send = QPushButton()

        # 快捷：先同步 UI，再发送
        def _set_and_send(v: int):
            self.spin.setValue(int(v))
            self._send_arc(int(v))

        self.btn_min.clicked.connect(lambda: _set_and_send(0))
        self.btn_mid.clicked.connect(lambda: _set_and_send(128))
        self.btn_max.clicked.connect(lambda: _set_and_send(254))
        self.btn_send.clicked.connect(lambda: self._send_arc(self.spin.value()))

        self.lbl_brightness = QLabel()
        dg.addWidget(self.lbl_brightness, 0, 0)
        dg.addWidget(self.slider, 0, 1, 1, 3)
        dg.addWidget(self.spin,   0, 4)
        dg.addWidget(self.btn_min, 1, 1)
        dg.addWidget(self.btn_mid, 1, 2)
        dg.addWidget(self.btn_max, 1, 3)
        dg.addWidget(self.btn_send, 1, 4)
        root.addWidget(self.box_dim)
        root.addStretch(1)

        # 连接门控：未连接时禁用发送类按钮
        self.register_send_widgets([self.btn_send, self.btn_min, self.btn_mid, self.btn_max])

        self.apply_language()

    # ---------- helpers ----------
    # ---------- actions ----------
    def _send_arc(self, val: int):
        # 确保UI一致
        if self.spin.value() != val:
            self.spin.setValue(int(val))
        mode = self.addr_widget.mode()
        addr_val = self.addr_widget.addr_value()
        unaddr = self.addr_widget.unaddressed()
        try:
            self.ctrl.send_arc(mode, int(val), addr_val=addr_val, unaddr=unaddr)
            self.show_msg(trf("已发送 ARC={value}", "Sent ARC={value}", value=int(val)), 2000)
        except Exception as e:
            self._log.error(tr("发送ARC失败", "ARC send failed"), exc_info=True)
            self.show_msg(trf("发送失败：{error}", "Send failed: {error}", error=e), 5000)

    # ---------- language ----------
    def apply_language(self):
        self.addr_widget.apply_language()

        self.box_dim.setTitle(tr("亮度（ARC 0–254）", "Brightness (ARC 0–254)"))
        self.lbl_brightness.setText(tr("亮度：", "Brightness:"))
        self.btn_min.setText(tr("最暗(0)", "Darkest (0)"))
        self.btn_mid.setText(tr("中间(128)", "Middle (128)"))
        self.btn_max.setText(tr("最亮(254)", "Brightest (254)"))
        self.btn_send.setText(tr("发送", "Send"))
