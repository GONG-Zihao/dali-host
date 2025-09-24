from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QGroupBox, QGridLayout, QRadioButton, QSpinBox, QCheckBox, QLabel,
    QPushButton, QVBoxLayout, QLineEdit
)
from app.gui.widgets.base_panel import BasePanel
from app.i18n import tr, trf


class PanelRW(BasePanel):
    """
    变量读写（自定义命令查询 最小闭环）：
    - 选择地址模式（广播/短址/组址）
    - 输入命令字节（0..255），发送（is_command=1）
    - 尝试接收1字节响应，十六进制与十进制显示
    """
    def __init__(self, controller, statusbar):
        super().__init__(controller, statusbar)
        self._log = logging.getLogger("PanelRW")
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

        # 命令区
        self.box_cmd = QGroupBox()
        cg = QGridLayout(self.box_cmd)
        self.sb_opcode = QSpinBox(); self.sb_opcode.setRange(0, 255); self.sb_opcode.setValue(0x90)
        self.sb_timeout = QSpinBox(); self.sb_timeout.setRange(0, 2000); self.sb_timeout.setValue(300); self.sb_timeout.setSuffix(" ms")
        self.btn_send = QPushButton()
        self.btn_send.clicked.connect(self._on_send)

        self.lbl_opcode = QLabel()
        self.lbl_timeout = QLabel()
        cg.addWidget(self.lbl_opcode, 0, 0); cg.addWidget(self.sb_opcode, 0, 1)
        cg.addWidget(self.lbl_timeout, 0, 2); cg.addWidget(self.sb_timeout, 0, 3)
        cg.addWidget(self.btn_send, 0, 4)
        root.addWidget(self.box_cmd)

        # 结果区
        self.box_out = QGroupBox()
        og = QGridLayout(self.box_out)
        self.le_raw = QLineEdit(); self.le_raw.setReadOnly(True)
        self.le_hex = QLineEdit(); self.le_hex.setReadOnly(True)
        self.le_dec = QLineEdit(); self.le_dec.setReadOnly(True)
        self.lbl_raw = QLabel()
        self.lbl_hex = QLabel()
        self.lbl_dec = QLabel()
        og.addWidget(self.lbl_raw, 0, 0); og.addWidget(self.le_raw, 0, 1, 1, 4)
        og.addWidget(self.lbl_hex, 1, 0); og.addWidget(self.le_hex, 1, 1)
        og.addWidget(self.lbl_dec, 1, 2); og.addWidget(self.le_dec, 1, 3)
        root.addWidget(self.box_out)
        root.addStretch(1)

        # 连接门控：未连接时禁用“发送并接收”
        self.register_send_widgets([self.btn_send])

        self.apply_language()

    # ---------- helpers ----------
    def _read_addr_mode(self) -> tuple[str, int | None, bool]:
        if self.rb_short.isChecked():
            return "short", self.sb_short.value(), False
        if self.rb_group.isChecked():
            return "group", self.sb_group.value(), False
        return "broadcast", None, self.chk_unaddr.isChecked()

    # ---------- actions ----------
    def _on_send(self):
        mode, addr_val, unaddr = self._read_addr_mode()
        opcode = self.sb_opcode.value()
        timeout = self.sb_timeout.value() / 1000.0
        try:
            data = self.ctrl.send_command(mode, opcode, addr_val=addr_val, unaddr=unaddr, timeout=timeout)
            if not data:
                self.le_raw.setText("")
                self.le_hex.setText("")
                self.le_dec.setText("")
                self.show_msg(tr("无响应（超时）", "No response (timeout)"), 3000)
                return
            # 展示
            self.le_raw.setText(data.hex(" "))
            self.le_hex.setText(" ".join(f"{b:02X}" for b in data))
            self.le_dec.setText(" ".join(str(int(b)) for b in data))
            self.show_msg(tr("已发送并收到响应", "Command sent and response received"), 2000)
        except Exception as e:
            self._log.error(tr("发送失败", "Send failed"), exc_info=True)
            self.show_msg(trf("发送失败：{error}", "Send failed: {error}", error=e), 5000)

    def apply_language(self):
        self.box_addr.setTitle(tr("地址选择", "Address selection"))
        self.rb_bcast.setText(tr("广播", "Broadcast"))
        self.chk_unaddr.setText(tr("仅未寻址", "Not addressed only"))
        self.rb_short.setText(tr("短地址", "Short address"))
        self.rb_group.setText(tr("组地址", "Group address"))

        self.box_cmd.setTitle(tr("命令查询（is_command=1）", "Command query (is_command=1)"))
        self.lbl_opcode.setText(tr("命令字节 (0–255)：", "Command byte (0–255):"))
        self.lbl_timeout.setText(tr("接收超时：", "Receive timeout:"))
        self.btn_send.setText(tr("发送并接收", "Send and receive"))

        self.box_out.setTitle(tr("响应", "Response"))
        self.lbl_raw.setText(tr("原始字节流：", "Raw bytes:"))
        self.lbl_hex.setText(tr("HEX：", "HEX:"))
        self.lbl_dec.setText(tr("DEC：", "DEC:"))
