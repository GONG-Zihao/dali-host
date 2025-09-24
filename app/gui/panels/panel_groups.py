from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QRadioButton, QSpinBox,
    QCheckBox, QLabel, QPushButton
)
from app.gui.widgets.base_panel import BasePanel
from app.i18n import tr, trf


class PanelGroups(BasePanel):
    """组管理：加入/移除 group(0..15)。"""
    def __init__(self, controller, statusbar):
        super().__init__(controller, statusbar)
        self._log = logging.getLogger("PanelGroups")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # 目标选择（短址/广播；不建议对组地址本身操作）
        self.box_target = QGroupBox()
        tg = QGridLayout(self.box_target)
        self.rb_bcast = QRadioButton(); self.rb_bcast.setChecked(True)
        self.chk_unaddr = QCheckBox()
        self.rb_short = QRadioButton()
        self.sb_short = QSpinBox(); self.sb_short.setRange(0, 63)
        tg.addWidget(self.rb_bcast, 0, 0); tg.addWidget(self.chk_unaddr, 0, 1)
        tg.addWidget(self.rb_short, 1, 0); tg.addWidget(self.sb_short, 1, 1)
        root.addWidget(self.box_target)

        # 组操作
        self.box_grp = QGroupBox()
        gg = QGridLayout(self.box_grp)
        self.sb_group = QSpinBox(); self.sb_group.setRange(0, 15)
        self.btn_add = QPushButton()
        self.btn_del = QPushButton()
        self.btn_add.clicked.connect(lambda: self._do("add"))
        self.btn_del.clicked.connect(lambda: self._do("remove"))

        self.lbl_group = QLabel()
        gg.addWidget(self.lbl_group, 0, 0); gg.addWidget(self.sb_group, 0, 1)
        gg.addWidget(self.btn_add, 0, 2); gg.addWidget(self.btn_del, 0, 3)
        root.addWidget(self.box_grp)
        root.addStretch(1)

        # 连接门控
        self.register_send_widgets([self.btn_add, self.btn_del])

        self.apply_language()

    def _read_target(self):
        if self.rb_short.isChecked():
            return "short", self.sb_short.value(), False
        return "broadcast", None, self.chk_unaddr.isChecked()

    def _do(self, action: str):
        mode, addr_val, unaddr = self._read_target()
        g = self.sb_group.value()
        try:
            if action == "add":
                self.ctrl.group_add(mode, g, addr_val=addr_val, unaddr=unaddr)
                self.show_msg(trf("已加入组{group}", "Added to group {group}", group=g), 2000)
            else:
                self.ctrl.group_remove(mode, g, addr_val=addr_val, unaddr=unaddr)
                self.show_msg(trf("已从组{group}移除", "Removed from group {group}", group=g), 2000)
        except Exception as e:
            self._log.error(tr("组操作失败", "Group operation failed"), exc_info=True)
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    def apply_language(self):
        self.box_target.setTitle(tr("目标选择（建议为短地址或广播）", "Target selection (recommended for short or broadcast)"))
        self.rb_bcast.setText(tr("广播", "Broadcast"))
        self.chk_unaddr.setText(tr("仅未寻址", "Not addressed only"))
        self.rb_short.setText(tr("短地址", "Short address"))

        self.box_grp.setTitle(tr("组操作", "Group operation"))
        self.lbl_group.setText(tr("组号(0–15)：", "Group (0–15):"))
        self.btn_add.setText(tr("加入组", "Join group"))
        self.btn_del.setText(tr("从组移除", "Remove from group"))
