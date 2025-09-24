from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QRadioButton, QSpinBox,
    QCheckBox, QLabel, QPushButton, QSlider
)
from PySide6.QtCore import Qt
from app.gui.widgets.base_panel import BasePanel
from app.i18n import tr, trf


class PanelDt8Tc(BasePanel):
    """DT8 / Tc 色温控制（以 Kelvin 输入，内部换算 Mirek）"""
    def __init__(self, controller, statusbar, tc_cfg: dict | None = None):
        super().__init__(controller, statusbar)
        self._log = logging.getLogger("PanelDt8Tc")
        self.tc_cfg = tc_cfg or {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # 地址选择
        self.box_addr = QGroupBox()
        ag = QGridLayout(self.box_addr)
        self.rb_b = QRadioButton(); self.rb_b.setChecked(True)
        self.chk_unaddr = QCheckBox()
        self.rb_s = QRadioButton(); self.sb_s = QSpinBox(); self.sb_s.setRange(0, 63)
        self.rb_g = QRadioButton(); self.sb_g = QSpinBox(); self.sb_g.setRange(0, 15)
        ag.addWidget(self.rb_b, 0, 0); ag.addWidget(self.chk_unaddr, 0, 1)
        ag.addWidget(self.rb_s, 1, 0); ag.addWidget(self.sb_s, 1, 1)
        ag.addWidget(self.rb_g, 2, 0); ag.addWidget(self.sb_g, 2, 1)
        root.addWidget(self.box_addr)

        # Tc 设置
        kmin = int(self.tc_cfg.get("kelvin_min", 1700))
        kmax = int(self.tc_cfg.get("kelvin_max", 8000))
        self.box_tc = QGroupBox()
        tg = QGridLayout(self.box_tc)
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(kmin, kmax)
        self.spinK  = QSpinBox(); self.spinK.setRange(kmin, kmax); self.spinK.setValue(4000)
        self.spinM  = QSpinBox(); self.spinM.setRange(1, 65534); self.spinM.setReadOnly(True)

        # 同步 & 初始换算
        self.slider.valueChanged.connect(self.spinK.setValue)
        self.spinK.valueChanged.connect(self.slider.setValue)
        self.spinK.valueChanged.connect(self._update_mirek)
        self._update_mirek(self.spinK.value())

        self.btn_send = QPushButton()
        self.btn_send.clicked.connect(self._on_send)

        self.lbl_k = QLabel()
        self.lbl_m = QLabel()
        tg.addWidget(self.lbl_k, 0, 0); tg.addWidget(self.slider, 0, 1, 1, 4); tg.addWidget(self.spinK, 0, 5)
        tg.addWidget(self.lbl_m, 1, 0); tg.addWidget(self.spinM, 1, 1)
        tg.addWidget(self.btn_send, 1, 5)
        root.addWidget(self.box_tc)
        root.addStretch(1)

        # 连接门控
        self.register_send_widgets([self.btn_send])

    def _addr(self):
        if self.rb_s.isChecked():
            return "short", self.sb_s.value(), False
        if self.rb_g.isChecked():
            return "group", self.sb_g.value(), False
        return "broadcast", None, self.chk_unaddr.isChecked()

    def _update_mirek(self, k: int):
        try:
            m = max(1, min(65534, int(round(1_000_000 / float(k)))))
            self.spinM.blockSignals(True)
            self.spinM.setValue(m)
            self.spinM.blockSignals(False)
        except Exception:
            pass

    def _on_send(self):
        mode, addr_val, unaddr = self._addr()
        k = self.spinK.value()
        try:
            out = self.ctrl.dt8_set_tc_kelvin(mode, k, addr_val=addr_val, unaddr=unaddr)
            self.show_msg(trf("已设置 Tc={kelvin}K（{mirek} Mirek）", "Set Tc={kelvin}K ({mirek} Mirek)", kelvin=out['kelvin'], mirek=out['mirek']), 2500)
        except Exception as e:
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    def apply_language(self):
        self.box_addr.setTitle(tr("地址选择", "Address selection"))
        self.rb_b.setText(tr("广播", "Broadcast"))
        self.chk_unaddr.setText(tr("仅未寻址", "Not addressed only"))
        self.rb_s.setText(tr("短地址", "Short address"))
        self.rb_g.setText(tr("组地址", "Group address"))

        self.box_tc.setTitle(tr("色温（Kelvin）→ Mirek", "Color temperature (Kelvin) → Mirek"))
        self.lbl_k.setText(tr("K：", "K:"))
        self.lbl_m.setText(tr("Mirek：", "Mirek:"))
        self.btn_send.setText(tr("设置色温", "Set color temperature"))
