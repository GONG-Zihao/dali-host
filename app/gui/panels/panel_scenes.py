from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QRadioButton, QSpinBox,
    QCheckBox, QLabel, QPushButton
)
from app.gui.widgets.base_panel import BasePanel
from app.i18n import tr, trf


class PanelScenes(BasePanel):
    """场景管理：回放 / 保存（写入亮度）/ 移除。"""
    def __init__(self, controller, statusbar):
        super().__init__(controller, statusbar)
        self._log = logging.getLogger("PanelScenes")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # 地址选择（可短址/组址/广播）
        self.box_addr = QGroupBox()
        ag = QGridLayout(self.box_addr)
        self.rb_bcast = QRadioButton()
        self.rb_bcast.setChecked(True)
        self.chk_unaddr = QCheckBox()
        self.rb_short = QRadioButton()
        self.sb_short = QSpinBox(); self.sb_short.setRange(0, 63)
        self.rb_group = QRadioButton()
        self.sb_group = QSpinBox(); self.sb_group.setRange(0, 15)
        ag.addWidget(self.rb_bcast, 0, 0); ag.addWidget(self.chk_unaddr, 0, 1)
        ag.addWidget(self.rb_short, 1, 0); ag.addWidget(self.sb_short, 1, 1)
        ag.addWidget(self.rb_group, 2, 0); ag.addWidget(self.sb_group, 2, 1)
        root.addWidget(self.box_addr)

        # 场景操作
        self.box_sc = QGroupBox()
        sg = QGridLayout(self.box_sc)
        self.sb_scene = QSpinBox(); self.sb_scene.setRange(0, 15)
        self.sb_level = QSpinBox(); self.sb_level.setRange(0, 254); self.sb_level.setValue(128)

        self.btn_recall = QPushButton()
        self.btn_store  = QPushButton()
        self.btn_remove = QPushButton()

        self.btn_recall.clicked.connect(self._on_recall)
        self.btn_store.clicked.connect(self._on_store)
        self.btn_remove.clicked.connect(self._on_remove)

        self.lbl_scene = QLabel()
        self.lbl_level = QLabel()
        sg.addWidget(self.lbl_scene, 0, 0); sg.addWidget(self.sb_scene, 0, 1)
        sg.addWidget(self.lbl_level, 0, 2); sg.addWidget(self.sb_level, 0, 3)
        sg.addWidget(self.btn_recall, 1, 1); sg.addWidget(self.btn_store, 1, 2); sg.addWidget(self.btn_remove, 1, 3)
        root.addWidget(self.box_sc)
        root.addStretch(1)

        # 连接门控
        self.register_send_widgets([self.btn_recall, self.btn_store, self.btn_remove])

        self.apply_language()

    def _addr(self):
        if self.rb_short.isChecked():
            return "short", self.sb_short.value(), False
        if self.rb_group.isChecked():
            return "group", self.sb_group.value(), False
        return "broadcast", None, self.chk_unaddr.isChecked()

    def _on_recall(self):
        mode, addr_val, unaddr = self._addr()
        scene = self.sb_scene.value()
        try:
            self.ctrl.scene_recall(mode, scene, addr_val=addr_val, unaddr=unaddr)
            self.show_msg(trf("已回放场景{scene}", "Scene {scene} recalled", scene=scene), 2000)
        except Exception as e:
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    def _on_store(self):
        mode, addr_val, unaddr = self._addr()
        scene = self.sb_scene.value()
        level = self.sb_level.value()
        try:
            self.ctrl.scene_store_level(mode, scene, level, addr_val=addr_val, unaddr=unaddr)
            self.show_msg(trf("已保存 场景{scene} ← 亮度{level}", "Scene {scene} saved with brightness {level}", scene=scene, level=level), 2500)
        except Exception as e:
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    def _on_remove(self):
        mode, addr_val, unaddr = self._addr()
        scene = self.sb_scene.value()
        try:
            self.ctrl.scene_remove(mode, scene, addr_val=addr_val, unaddr=unaddr)
            self.show_msg(trf("已移除 场景{scene}", "Scene {scene} removed", scene=scene), 2000)
        except Exception as e:
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    def apply_language(self):
        self.box_addr.setTitle(tr("地址选择", "Address selection"))
        self.rb_bcast.setText(tr("广播", "Broadcast"))
        self.chk_unaddr.setText(tr("仅未寻址", "Not addressed only"))
        self.rb_short.setText(tr("短地址", "Short address"))
        self.rb_group.setText(tr("组地址", "Group address"))

        self.box_sc.setTitle(tr("场景操作", "Scene operation"))
        self.lbl_scene.setText(tr("场景(0–15)：", "Scene (0–15):"))
        self.lbl_level.setText(tr("保存亮度(0–254)：", "Brightness to save (0–254):"))
        self.btn_recall.setText(tr("回放场景", "Recall scene"))
        self.btn_store.setText(tr("保存为场景（写入亮度）", "Store scene (write brightness)"))
        self.btn_remove.setText(tr("移除场景", "Remove scene"))
