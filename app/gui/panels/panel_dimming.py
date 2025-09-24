from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QGroupBox, QGridLayout, QRadioButton, QSpinBox, QCheckBox, QLabel,
    QPushButton, QVBoxLayout, QSlider
)
from PySide6.QtCore import Qt
from app.gui.widgets.base_panel import BasePanel
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

        # 地址区
        self.box_addr = QGroupBox()
        g = QGridLayout(self.box_addr)
        self.rb_bcast = QRadioButton()
        self.rb_bcast.setChecked(True)
        self.chk_unaddr = QCheckBox()
        self.rb_short = QRadioButton()
        self.sb_short = QSpinBox(); self.sb_short.setRange(0, 63)
        self.rb_group = QRadioButton()
        self.sb_group = QSpinBox(); self.sb_group.setRange(0, 15)

        g.addWidget(self.rb_bcast, 0, 0); g.addWidget(self.chk_unaddr, 0, 1)
        g.addWidget(self.rb_short, 1, 0); g.addWidget(self.sb_short, 1, 1)
        g.addWidget(self.rb_group, 2, 0); g.addWidget(self.sb_group, 2, 1)
        root.addWidget(self.box_addr)

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
    def _read_addr_mode(self) -> tuple[str, int | None, bool]:
        if self.rb_short.isChecked():
            return "short", self.sb_short.value(), False
        if self.rb_group.isChecked():
            return "group", self.sb_group.value(), False
        return "broadcast", None, self.chk_unaddr.isChecked()

    # ---------- actions ----------
    def _send_arc(self, val: int):
        # 确保UI一致
        if self.spin.value() != val:
            self.spin.setValue(int(val))
        mode, addr_val, unaddr = self._read_addr_mode()
        try:
            self.ctrl.send_arc(mode, int(val), addr_val=addr_val, unaddr=unaddr)
            self.show_msg(trf("已发送 ARC={value}", "Sent ARC={value}", value=int(val)), 2000)
        except Exception as e:
            self._log.error(tr("发送ARC失败", "ARC send failed"), exc_info=True)
            self.show_msg(trf("发送失败：{error}", "Send failed: {error}", error=e), 5000)

    # ---------- language ----------
    def apply_language(self):
        self.box_addr.setTitle(tr("地址选择", "Address selection"))
        self.rb_bcast.setText(tr("广播", "Broadcast"))
        self.chk_unaddr.setText(tr("仅未寻址", "Not addressed only"))
        self.rb_short.setText(tr("短地址", "Short address"))
        self.rb_group.setText(tr("组地址", "Group address"))

        self.box_dim.setTitle(tr("亮度（ARC 0–254）", "Brightness (ARC 0–254)"))
        self.lbl_brightness.setText(tr("亮度：", "Brightness:"))
        self.btn_min.setText(tr("最暗(0)", "Darkest (0)"))
        self.btn_mid.setText(tr("中间(128)", "Middle (128)"))
        self.btn_max.setText(tr("最亮(254)", "Brightest (254)"))
        self.btn_send.setText(tr("发送", "Send"))
