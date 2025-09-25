from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QGridLayout,
    QSpinBox,
    QLabel,
    QPushButton,
)
from app.gui.widgets.base_panel import BasePanel
from app.gui.widgets.address_target import AddressTargetWidget
from app.i18n import tr, trf


class PanelScenes(BasePanel):
    """场景管理：回放 / 保存（写入亮度）/ 移除。"""
    def __init__(self, controller, statusbar):
        super().__init__(controller, statusbar)
        self._log = logging.getLogger("PanelScenes")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        self.addr_widget = AddressTargetWidget(self)
        root.addWidget(self.addr_widget)

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

    def _on_recall(self):
        mode = self.addr_widget.mode()
        addr_val = self.addr_widget.addr_value()
        unaddr = self.addr_widget.unaddressed()
        scene = self.sb_scene.value()
        try:
            self.ctrl.scene_recall(mode, scene, addr_val=addr_val, unaddr=unaddr)
            self.show_msg(trf("已回放场景{scene}", "Scene {scene} recalled", scene=scene), 2000)
        except Exception as e:
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    def _on_store(self):
        mode = self.addr_widget.mode()
        addr_val = self.addr_widget.addr_value()
        unaddr = self.addr_widget.unaddressed()
        scene = self.sb_scene.value()
        level = self.sb_level.value()
        try:
            self.ctrl.scene_store_level(mode, scene, level, addr_val=addr_val, unaddr=unaddr)
            self.show_msg(trf("已保存 场景{scene} ← 亮度{level}", "Scene {scene} saved with brightness {level}", scene=scene, level=level), 2500)
        except Exception as e:
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    def _on_remove(self):
        mode = self.addr_widget.mode()
        addr_val = self.addr_widget.addr_value()
        unaddr = self.addr_widget.unaddressed()
        scene = self.sb_scene.value()
        try:
            self.ctrl.scene_remove(mode, scene, addr_val=addr_val, unaddr=unaddr)
            self.show_msg(trf("已移除 场景{scene}", "Scene {scene} removed", scene=scene), 2000)
        except Exception as e:
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    def apply_language(self):
        self.addr_widget.apply_language()

        self.box_sc.setTitle(tr("场景操作", "Scene operation"))
        self.lbl_scene.setText(tr("场景(0–15)：", "Scene (0–15):"))
        self.lbl_level.setText(tr("保存亮度(0–254)：", "Brightness to save (0–254):"))
        self.btn_recall.setText(tr("回放场景", "Recall scene"))
        self.btn_store.setText(tr("保存为场景（写入亮度）", "Store scene (write brightness)"))
        self.btn_remove.setText(tr("移除场景", "Remove scene"))
