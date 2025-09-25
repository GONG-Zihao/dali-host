from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.gui.widgets.base_panel import BasePanel
from app.i18n import tr, trf


class PanelInventory(BasePanel):
    """设备读回与导出面板。"""

    def __init__(self, controller, statusbar, root_dir: Path):
        super().__init__(controller, statusbar)
        self.root_dir = root_dir
        self._devices: Dict[int, Dict[str, object]] = {}

        self._build_ui()
        self.apply_language()

    # ------------------ UI ------------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        self.box_actions = QGroupBox()
        act_layout = QHBoxLayout(self.box_actions)
        self.btn_scan = QPushButton()
        self.btn_groups = QPushButton()
        self.btn_scenes = QPushButton()
        self.btn_export = QPushButton()

        act_layout.addWidget(self.btn_scan)
        act_layout.addWidget(self.btn_groups)
        act_layout.addWidget(self.btn_scenes)
        act_layout.addStretch(1)
        act_layout.addWidget(self.btn_export)

        self.btn_scan.clicked.connect(self._scan_devices)

        self.btn_groups.clicked.connect(self._read_groups)
        self.btn_scenes.clicked.connect(self._read_scenes)
        self.btn_export.clicked.connect(self._export_json)

        root.addWidget(self.box_actions)

        self.table = QTableWidget(0, 4, self)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table)
        root.addStretch(1)

        self.register_send_widgets([self.btn_scan, self.btn_groups, self.btn_scenes, self.btn_export])

    # ------------------ Actions ------------------
    def _scan_devices(self):
        found = self.ctrl.scan_devices()
        self._devices = {
            short: {
                "status": True,
                "groups": {},
                "scenes": {},
            }
            for short in found
        }
        self._refresh_table()
        self.show_msg(trf("扫描完成：{count} 台", "Scan finished: {count} device(s)", count=len(found)), 2000)

    def _read_groups(self):
        if not self._devices:
            self.show_msg(tr("请先扫描设备", "Scan devices first"), 2000)
            return
        for short in list(self._devices.keys()):
            groups = self.ctrl.query_groups(short)
            self._devices[short]["groups"] = groups
        self._refresh_table()
        self.show_msg(tr("已读取组成员信息", "Group memberships updated"), 2000)

    def _read_scenes(self):
        if not self._devices:
            self.show_msg(tr("请先扫描设备", "Scan devices first"), 2000)
            return
        for short in list(self._devices.keys()):
            levels = self.ctrl.query_scene_levels(short)
            self._devices[short]["scenes"] = levels
        self._refresh_table()
        self.show_msg(tr("已读取场景亮度", "Scene levels updated"), 2000)

    def _export_json(self):
        if not self._devices:
            self.show_msg(tr("无数据可导出", "No data to export"), 2000)
            return

        data = {
            "version": 1,
            "groups": [],
            "scenes": [],
            "dt8_presets": [],
        }

        for short in sorted(self._devices.keys()):
            info = self._devices[short]
            groups = info.get("groups") or {}
            group_list: List[int] = [g for g, flag in groups.items() if flag]
            if group_list:
                data["groups"].append({"short": short, "groups": group_list})

            levels = info.get("scenes") or {}
            level_map = {str(scene): val for scene, val in levels.items() if val is not None}
            if level_map:
                data["scenes"].append({"short": short, "levels": level_map})

        if not data["groups"] and not data["scenes"]:
            self.show_msg(tr("无有效组/场景数据可导出", "Nothing to export"), 2000)
            return

        default_dir = self.root_dir / "数据"
        default_dir.mkdir(parents=True, exist_ok=True)
        default_name = f"inventory_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.json"
        default_path = default_dir / default_name

        path_str, _ = QFileDialog.getSaveFileName(
            self,
            tr("导出 JSON", "Export JSON"),
            str(default_path),
            "JSON (*.json)",
        )
        if not path_str:
            return

        with open(path_str, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.show_msg(trf("已导出：{path}", "Exported: {path}", path=path_str), 2000)

    # ------------------ Helpers ------------------
    def _refresh_table(self):
        rows = sorted(self._devices.keys())
        self.table.setRowCount(len(rows))
        headers = [
            tr("短址", "Short"),
            tr("状态", "State"),
            tr("组", "Groups"),
            tr("场景", "Scenes"),
        ]
        for idx, text in enumerate(headers):
            self.table.setHorizontalHeaderItem(idx, QTableWidgetItem(text))

        for row, short in enumerate(rows):
            info = self._devices[short]
            groups = info.get("groups") or {}
            scenes = info.get("scenes") or {}

            self.table.setItem(row, 0, QTableWidgetItem(str(short)))
            self.table.setItem(row, 1, QTableWidgetItem(tr("在线", "Online")))
            self.table.setItem(row, 2, QTableWidgetItem(self._format_groups(groups)))
            self.table.setItem(row, 3, QTableWidgetItem(self._format_scenes(scenes)))

        self.table.resizeColumnsToContents()

    @staticmethod
    def _format_groups(groups: Dict[int, int]) -> str:
        active = [str(idx) for idx, flag in sorted(groups.items()) if flag]
        return ", ".join(active) if active else "-"

    @staticmethod
    def _format_scenes(levels: Dict[int, int | None]) -> str:
        entries = []
        for scene, level in sorted(levels.items()):
            if level is None:
                continue
            entries.append(f"{scene}:{level}")
        return ", ".join(entries) if entries else "-"

    # ------------------ Language ------------------
    def apply_language(self):
        self.box_actions.setTitle(tr("设备操作", "Actions"))
        self.btn_scan.setText(tr("扫描", "Scan"))
        self.btn_groups.setText(tr("读取组", "Read groups"))
        self.btn_scenes.setText(tr("读取场景", "Read scenes"))
        self.btn_export.setText(tr("导出 JSON", "Export JSON"))
        self._refresh_table()

        parent = self.parent()
        while parent is not None and not isinstance(parent, QTabWidget):
            parent = parent.parent()
        if isinstance(parent, QTabWidget):
            idx = parent.indexOf(self)
            if idx >= 0:
                parent.setTabText(idx, tr("设备清单", "Inventory"))
