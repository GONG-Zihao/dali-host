from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QRadioButton, QSpinBox,
    QCheckBox, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QDateTimeEdit, QFileDialog, QHBoxLayout, QAbstractItemView,
    QDoubleSpinBox
)
from PySide6.QtCore import Qt, QDateTime

from app.core.schedule.manager import ScheduleManager, Task
from app.core.utils.hexutil import parse_pairs, fmt_pair
from app.i18n import tr, trf, i18n

WEEK_LABELS = [
    ("Week一", "Week Mon"),
    ("Week二", "Week Tue"),
    ("Week三", "Week Wed"),
    ("Week四", "Week Thu"),
    ("Week五", "Week Fri"),
    ("Week六", "Week Sat"),
    ("Week日", "Week Sun"),
]


class PanelScheduler(QWidget):
    """Task scheduler panel with i18n support."""

    def __init__(self, controller, statusbar, root_dir: Path):
        super().__init__()
        self.ctrl = controller
        self.statusbar = statusbar
        self.root_dir = root_dir
        self.store_dir = root_dir / "数据" / "schedule"
        self.manager = ScheduleManager(controller, self.store_dir, parent=self)
        self._selected_id: Optional[str] = None

        self._action_items: list[tuple[str, str, str]] = []
        self._sched_items: list[tuple[str, str, str]] = []
        self._week_checks: list[QCheckBox] = []

        self._build_ui()
        self._wire_signals()
        self._refresh_table()
        self.apply_language()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # Table
        self.table = QTableWidget(0, 9)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table)

        # Edit area
        self.box_edit = QGroupBox()
        grid = QGridLayout(self.box_edit)

        self.lbl_name = QLabel("任务名称：")
        self.ed_name = QLineEdit()
        self.cb_enabled = QCheckBox("启用")
        grid.addWidget(self.lbl_name, 0, 0); grid.addWidget(self.ed_name, 0, 1, 1, 3); grid.addWidget(self.cb_enabled, 0, 4)

        # Address target
        self.box_addr = QGroupBox()
        ag = QGridLayout(self.box_addr)
        self.rb_b = QRadioButton("广播"); self.rb_b.setChecked(True)
        self.chk_unaddr = QCheckBox("仅未寻址")
        self.rb_s = QRadioButton("短址"); self.sb_s = QSpinBox(); self.sb_s.setRange(0, 63)
        self.rb_g = QRadioButton("组址"); self.sb_g = QSpinBox(); self.sb_g.setRange(0, 15)
        ag.addWidget(self.rb_b, 0, 0); ag.addWidget(self.chk_unaddr, 0, 1)
        ag.addWidget(self.rb_s, 1, 0); ag.addWidget(self.sb_s, 1, 1)
        ag.addWidget(self.rb_g, 2, 0); ag.addWidget(self.sb_g, 2, 1)
        grid.addWidget(self.box_addr, 1, 0, 3, 2)

        # Action parameters
        self.box_action = QGroupBox()
        ag2 = QGridLayout(self.box_action)
        self.cb_action = QComboBox()
        self._action_items = [
            ("ARC 亮度", "ARC brightness", "arc"),
            ("场景回放", "Scene recall", "scene"),
            ("DT8 色温 Tc", "DT8 Tc", "dt8_tc"),
            ("DT8 xy", "DT8 xy", "dt8_xy"),
            ("DT8 RGBW", "DT8 RGBW", "dt8_rgbw"),
            ("原始帧序列", "Raw frame sequence", "raw"),
        ]
        for zh, _en, key in self._action_items:
            self.cb_action.addItem(zh, key)

        self.cb_action.currentIndexChanged.connect(self._on_action_changed)
        self.sp_arc = QSpinBox(); self.sp_arc.setRange(0, 254); self.sp_arc.setValue(128)
        self.sp_scene = QSpinBox(); self.sp_scene.setRange(0, 15)
        self.sp_k = QSpinBox(); self.sp_k.setRange(1000, 20000); self.sp_k.setValue(4000)
        self.sp_x = QDoubleSpinBox(); self.sp_x.setRange(0.0, 1.0); self.sp_x.setDecimals(4); self.sp_x.setSingleStep(0.0005); self.sp_x.setValue(0.3130)
        self.sp_y = QDoubleSpinBox(); self.sp_y.setRange(0.0, 1.0); self.sp_y.setDecimals(4); self.sp_y.setSingleStep(0.0005); self.sp_y.setValue(0.3290)
        self.sp_r = QSpinBox(); self.sp_r.setRange(0, 254)
        self.sp_g = QSpinBox(); self.sp_g.setRange(0, 254)
        self.sp_b = QSpinBox(); self.sp_b.setRange(0, 254)
        self.sp_w = QSpinBox(); self.sp_w.setRange(0, 254)
        self.ed_raw = QLineEdit(); self.ed_raw.setPlaceholderText("示例：\nFF 21\nC1 08\n或：FF 21; C1 08")

        row = 0
        self.lbl_action = QLabel("类型：")
        self.lbl_arc = QLabel("ARC：")
        self.lbl_scene = QLabel("场景：")
        self.lbl_tc = QLabel("Tc K：")
        self.lbl_xy = QLabel("xy：")
        self.lbl_rgbw = QLabel("RGBW：")
        self.lbl_raw = QLabel("原始帧：")

        ag2.addWidget(self.lbl_action, row, 0); ag2.addWidget(self.cb_action, row, 1, 1, 3); row += 1
        ag2.addWidget(self.lbl_arc, row, 0); ag2.addWidget(self.sp_arc, row, 1); row += 1
        ag2.addWidget(self.lbl_scene, row, 0); ag2.addWidget(self.sp_scene, row, 1); row += 1
        ag2.addWidget(self.lbl_tc, row, 0); ag2.addWidget(self.sp_k, row, 1); row += 1
        ag2.addWidget(self.lbl_xy, row, 0)
        self.line_xy = QHBoxLayout(); self.line_xy.addWidget(self.sp_x); self.line_xy.addWidget(self.sp_y)
        ag2.addLayout(self.line_xy, row, 1, 1, 3); row += 1
        ag2.addWidget(self.lbl_rgbw, row, 0)
        self.line_rgbw = QHBoxLayout()
        for spin in (self.sp_r, self.sp_g, self.sp_b, self.sp_w):
            self.line_rgbw.addWidget(spin)
        ag2.addLayout(self.line_rgbw, row, 1, 1, 3); row += 1
        ag2.addWidget(self.lbl_raw, row, 0); ag2.addWidget(self.ed_raw, row, 1, 1, 3)
        grid.addWidget(self.box_action, 1, 2, 3, 3)

        # Scheduling
        self.box_sched = QGroupBox()
        sg = QGridLayout(self.box_sched)
        self.cb_sched = QComboBox()
        self._sched_items = [
            ("一次性", "One-time", "once"),
            ("间隔", "Interval", "interval"),
            ("每天", "Daily", "daily"),
            ("每周", "Weekly", "weekly"),
        ]
        for zh, _en, key in self._sched_items:
            self.cb_sched.addItem(zh, key)
        self.cb_sched.currentIndexChanged.connect(self._on_sched_changed)

        self.lbl_sched_type = QLabel("类型：")
        self.lbl_once = QLabel("一次性：")
        self.dt_once = QDateTimeEdit(QDateTime.currentDateTime())
        self.dt_once.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_once.setCalendarPopup(True)
        self.lbl_interval = QLabel("间隔：")
        self.sp_every = QSpinBox(); self.sp_every.setRange(100, 24 * 60 * 60 * 1000); self.sp_every.setValue(60000); self.sp_every.setSuffix(" ms")
        self.lbl_time = QLabel("时间（用于每天/每周）：")
        self.sp_hour = QSpinBox(); self.sp_hour.setRange(0, 23)
        self.sp_min = QSpinBox(); self.sp_min.setRange(0, 59)
        self.line_time = QHBoxLayout(); self.line_time.addWidget(self.sp_hour); self.line_time.addWidget(self.sp_min)

        row = 0
        sg.addWidget(self.lbl_sched_type, row, 0); sg.addWidget(self.cb_sched, row, 1, 1, 3); row += 1
        sg.addWidget(self.lbl_once, row, 0); sg.addWidget(self.dt_once, row, 1, 1, 3); row += 1
        sg.addWidget(self.lbl_interval, row, 0); sg.addWidget(self.sp_every, row, 1); row += 1
        sg.addWidget(self.lbl_time, row, 0); sg.addLayout(self.line_time, row, 1); row += 1

        line1 = QHBoxLayout(); line2 = QHBoxLayout()
        self._week_checks.clear()
        for index, (zh, _en) in enumerate(WEEK_LABELS):
            chk = QCheckBox(zh)
            (line1 if index < 4 else line2).addWidget(chk)
            self._week_checks.append(chk)
        sg.addLayout(line1, row, 0, 1, 4); row += 1
        sg.addLayout(line2, row, 0, 1, 4)
        grid.addWidget(self.box_sched, 4, 0, 3, 5)

        # Buttons
        self.btn_new = QPushButton("新建")
        self.btn_save = QPushButton("保存")
        self.btn_del = QPushButton("删除")
        self.btn_toggle = QPushButton("启用/禁用")
        self.btn_run = QPushButton("立即执行")
        self.btn_export = QPushButton("导出任务JSON")
        self.btn_import = QPushButton("导入任务JSON")
        btn_box = QHBoxLayout()
        for btn in (self.btn_new, self.btn_save, self.btn_del, self.btn_toggle, self.btn_run, self.btn_export, self.btn_import):
            btn_box.addWidget(btn)
        grid.addLayout(btn_box, 7, 0, 1, 5)

        root.addWidget(self.box_edit)

    # ------------------------------------------------------------------
    def apply_language(self):
        headers = [
            tr("启用", "Enable"),
            tr("名称", "Name"),
            tr("目标", "Target"),
            tr("动作", "Action"),
            tr("参数", "Parameter"),
            tr("调度", "Scheduling"),
            tr("下次运行", "Run next time"),
            tr("上次运行", "Last run"),
            tr("次数", "Count"),
        ]
        for idx, text in enumerate(headers):
            item = self.table.horizontalHeaderItem(idx)
            if item is None:
                item = QTableWidgetItem()
                self.table.setHorizontalHeaderItem(idx, item)
            item.setText(text)

        self.box_edit.setTitle(tr("编辑任务", "Edit Tasks"))
        self.lbl_name.setText(tr("任务名称：", "Task name:"))
        self.cb_enabled.setText(tr("启用", "Enable"))

        self.box_addr.setTitle(tr("目标", "Target"))
        self.rb_b.setText(tr("广播", "Broadcast"))
        self.chk_unaddr.setText(tr("仅未寻址", "Not addressed only"))
        self.rb_s.setText(tr("短址", "Short address"))
        self.rb_g.setText(tr("组址", "Group address"))

        self.box_action.setTitle(tr("动作", "Action"))
        self.lbl_action.setText(tr("类型：", "Type:"))
        self.lbl_arc.setText(tr("ARC：", "ARC:"))
        self.lbl_scene.setText(tr("场景：", "Scene:"))
        self.lbl_tc.setText(tr("Tc K：", "Tc K:"))
        self.lbl_xy.setText(tr("xy：", "xy:"))
        self.lbl_rgbw.setText(tr("RGBW：", "RGBW:"))
        self.lbl_raw.setText(tr("原始帧：", "Raw frames:"))
        self.ed_raw.setPlaceholderText(tr("示例：\nFF 21\nC1 08\n或：FF 21; C1 08", "Example:\nFF 21\nC1 08\nor: FF 21; C1 08"))
        for index, (zh, en, _key) in enumerate(self._action_items):
            self.cb_action.setItemText(index, tr(zh, en))

        self.box_sched.setTitle(tr("调度", "Scheduling"))
        self.lbl_sched_type.setText(tr("类型：", "Type:"))
        self.lbl_once.setText(tr("一次性：", "One-time:"))
        self.lbl_interval.setText(tr("间隔：", "Interval:"))
        self.lbl_time.setText(tr("时间（用于每天/每周）：", "Time (for daily/weekly):"))
        for index, (zh, en, _key) in enumerate(self._sched_items):
            self.cb_sched.setItemText(index, tr(zh, en))
        for chk, (zh, en) in zip(self._week_checks, WEEK_LABELS):
            chk.setText(tr(zh, en))

        self.btn_new.setText(tr("新建", "New"))
        self.btn_save.setText(tr("保存", "Save"))
        self.btn_del.setText(tr("删除", "Delete"))
        self.btn_toggle.setText(tr("启用/禁用", "Enable/disable"))
        self.btn_run.setText(tr("立即执行", "Execute now"))
        self.btn_export.setText(tr("导出任务JSON", "Export task JSON"))
        self.btn_import.setText(tr("导入任务JSON", "Import task JSON"))

    # ------------------------------------------------------------------
    def _wire_signals(self):
        self.manager.task_updated.connect(lambda _tid: self._refresh_table())
        self.manager.tasks_reloaded.connect(self._refresh_table)
        self.manager.message.connect(lambda s: self._show(s, i18n.translate_text(s), 2500))

        self.table.itemSelectionChanged.connect(self._on_select_row)
        self.btn_new.clicked.connect(self._on_new)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_del.clicked.connect(self._on_del)
        self.btn_toggle.clicked.connect(self._on_toggle)
        self.btn_run.clicked.connect(self._on_run)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_import.clicked.connect(self._on_import)

    # ------------------------------------------------------------------
    def _show(self, zh: str, en: str, ms: int = 2000, **kwargs):
        message = trf(zh, en, **kwargs)
        try:
            self.statusbar.showMessage(message, ms)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _refresh_table(self):
        tasks = self.manager.list()
        self._tasks_cache = tasks
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            values = [
                tr("启用", "Enable") if task.enabled else tr("禁用", "Disable"),
                task.name,
                self._format_target(task),
                self._describe_action(task),
                self._describe_params(task),
                self._describe_schedule(task),
                task.next_run or "-",
                task.last_run or "-",
                str(task.run_count),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))

    def _format_target(self, task: Task) -> str:
        mode_map = {
            "broadcast": tr("广播", "Broadcast"),
            "short": tr("短址", "Short address"),
            "group": tr("组址", "Group address"),
        }
        text = mode_map.get(task.mode, task.mode)
        if task.mode in {"short", "group"} and task.addr_val is not None:
            text += f" #{task.addr_val}"
        if task.mode == "broadcast" and task.unaddr:
            text += f" ({tr('仅未寻址', 'Not addressed only')})"
        return text

    def _describe_action(self, task: Task) -> str:
        name_map = {
            "arc": tr("ARC 亮度", "ARC brightness"),
            "scene": tr("场景回放", "Scene recall"),
            "dt8_tc": tr("DT8 色温 Tc", "DT8 Tc"),
            "dt8_xy": tr("DT8 xy", "DT8 xy"),
            "dt8_rgbw": tr("DT8 RGBW", "DT8 RGBW"),
            "raw": tr("原始帧序列", "Raw frame sequence"),
        }
        return name_map.get(task.action, task.action)

    def _describe_params(self, task: Task) -> str:
        params = task.params or {}
        action = task.action
        if action == "arc":
            return f"ARC={params.get('value', '')}"
        if action == "scene":
            return f"Scene={params.get('scene', '')}"
        if action == "dt8_tc":
            return f"Kelvin={params.get('kelvin', '')}"
        if action == "dt8_xy":
            return f"x={params.get('x', '')}, y={params.get('y', '')}"
        if action == "dt8_rgbw":
            return ", ".join(f"{ch.upper()}={params.get(ch, '')}" for ch in ("r", "g", "b", "w"))
        if action == "raw":
            frames = params.get("frames", [])
            return "; ".join(fmt_pair(*f) for f in frames[:3]) + ("..." if len(frames) > 3 else "")
        return "-"

    def _describe_schedule(self, task: Task) -> str:
        rule = task.schedule or {}
        typ = (rule.get("type") or "").lower()
        if typ == "once":
            return tr("一次性", "One-time") + ": " + (rule.get("datetime") or "-")
        if typ == "interval":
            return tr("间隔", "Interval") + f": {rule.get('every_ms', '')} ms"
        if typ == "daily":
            return tr("每天", "Daily") + f" @ {rule.get('hour', 0):02d}:{rule.get('minute', 0):02d}"
        if typ == "weekly":
            days = rule.get("weekdays", [])
            names = []
            for d in days:
                idx = int(d)
                if 0 <= idx < len(WEEK_LABELS):
                    names.append(tr(*WEEK_LABELS[idx]))
            return tr("每周", "Weekly") + f" {','.join(names)} @ {rule.get('hour', 0):02d}:{rule.get('minute', 0):02d}"
        return "-"

    # ------------------------------------------------------------------
    def _collect_action_params(self) -> Dict[str, Any]:
        action = self.cb_action.currentData()
        if action == "arc":
            return {"value": self.sp_arc.value()}
        if action == "scene":
            return {"scene": self.sp_scene.value()}
        if action == "dt8_tc":
            return {"kelvin": self.sp_k.value()}
        if action == "dt8_xy":
            return {"x": float(self.sp_x.value()), "y": float(self.sp_y.value())}
        if action == "dt8_rgbw":
            return {
                "r": self.sp_r.value(),
                "g": self.sp_g.value(),
                "b": self.sp_b.value(),
                "w": self.sp_w.value(),
            }
        if action == "raw":
            text = self.ed_raw.text().strip()
            if not text:
                return {"frames": []}
            frames = parse_pairs(text)
            return {"frames": [[a, d] for a, d in frames]}
        return {}

    def _apply_action_to_form(self, task: Task):
        params = task.params or {}
        index = self.cb_action.findData(task.action)
        if index >= 0:
            self.cb_action.setCurrentIndex(index)
        if task.action == "arc":
            self.sp_arc.setValue(int(params.get("value", 0)))
        elif task.action == "scene":
            self.sp_scene.setValue(int(params.get("scene", 0)))
        elif task.action == "dt8_tc":
            self.sp_k.setValue(int(params.get("kelvin", 4000)))
        elif task.action == "dt8_xy":
            self.sp_x.setValue(float(params.get("x", 0.313)))
            self.sp_y.setValue(float(params.get("y", 0.329)))
        elif task.action == "dt8_rgbw":
            self.sp_r.setValue(int(params.get("r", 0)))
            self.sp_g.setValue(int(params.get("g", 0)))
            self.sp_b.setValue(int(params.get("b", 0)))
            self.sp_w.setValue(int(params.get("w", 0)))
        elif task.action == "raw":
            frames = params.get("frames", [])
            self.ed_raw.setText("\n".join(fmt_pair(*f) for f in frames))
        self._set_action_fields()

    def _collect_schedule(self) -> Dict[str, Any]:
        typ = self.cb_sched.currentData()
        if typ == "once":
            return {"type": "once", "datetime": self.dt_once.dateTime().toString(Qt.ISODate)}
        if typ == "interval":
            return {"type": "interval", "every_ms": self.sp_every.value()}
        if typ == "daily":
            return {
                "type": "daily",
                "hour": self.sp_hour.value(),
                "minute": self.sp_min.value(),
            }
        if typ == "weekly":
            weekdays = [i for i, chk in enumerate(self._week_checks) if chk.isChecked()]
            return {
                "type": "weekly",
                "hour": self.sp_hour.value(),
                "minute": self.sp_min.value(),
                "weekdays": weekdays,
            }
        return {"type": "once", "datetime": self.dt_once.dateTime().toString(Qt.ISODate)}

    def _apply_schedule_to_form(self, task: Task):
        rule = task.schedule or {}
        typ = rule.get("type", "once")
        index = self.cb_sched.findData(typ)
        if index >= 0:
            self.cb_sched.setCurrentIndex(index)
        if typ == "once":
            dt = rule.get("datetime")
            if dt:
                self.dt_once.setDateTime(QDateTime.fromString(dt, Qt.ISODate))
        elif typ == "interval":
            self.sp_every.setValue(int(rule.get("every_ms", 60000)))
        elif typ in ("daily", "weekly"):
            self.sp_hour.setValue(int(rule.get("hour", 0)))
            self.sp_min.setValue(int(rule.get("minute", 0)))
            if typ == "weekly":
                weekdays = set(int(d) for d in rule.get("weekdays", []))
                for idx, chk in enumerate(self._week_checks):
                    chk.setChecked(idx in weekdays)
        self._set_schedule_fields()

    def _selected_task(self) -> Optional[Task]:
        row = self.table.currentRow()
        if row < 0:
            return None
        if not hasattr(self, "_tasks_cache"):
            return None
        if row >= len(self._tasks_cache):
            return None
        return self._tasks_cache[row]

    def _on_select_row(self):
        task = self._selected_task()
        if not task:
            return
        self._selected_id = task.id
        self.ed_name.setText(task.name)
        self.cb_enabled.setChecked(task.enabled)
        if task.mode == "broadcast":
            self.rb_b.setChecked(True)
        elif task.mode == "short":
            self.rb_s.setChecked(True)
            self.sb_s.setValue(task.addr_val or 0)
        else:
            self.rb_g.setChecked(True)
            self.sb_g.setValue(task.addr_val or 0)
        self.chk_unaddr.setChecked(task.unaddr)

        self._apply_action_to_form(task)
        self._apply_schedule_to_form(task)

    def _clear_form(self):
        self._selected_id = None
        self.ed_name.clear()
        self.cb_enabled.setChecked(True)
        self.rb_b.setChecked(True)
        self.chk_unaddr.setChecked(False)
        self.sp_arc.setValue(128)
        self.sp_scene.setValue(0)
        self.sp_k.setValue(4000)
        self.sp_x.setValue(0.3130)
        self.sp_y.setValue(0.3290)
        self.sp_r.setValue(0)
        self.sp_g.setValue(0)
        self.sp_b.setValue(0)
        self.sp_w.setValue(0)
        self.ed_raw.clear()
        self.cb_action.setCurrentIndex(0)
        self.cb_sched.setCurrentIndex(0)
        for chk in self._week_checks:
            chk.setChecked(False)
        self._set_action_fields()
        self._set_schedule_fields()

    def _on_new(self):
        self._clear_form()
        self.table.clearSelection()

    def _collect_target(self):
        if self.rb_s.isChecked():
            return "short", self.sb_s.value(), False
        if self.rb_g.isChecked():
            return "group", self.sb_g.value(), False
        return "broadcast", None, self.chk_unaddr.isChecked()

    def _on_save(self):
        name = self.ed_name.text().strip()
        if not name:
            self._show("任务名称不能为空", "Task name required", 2000)
            return
        mode, addr_val, unaddr = self._collect_target()
        action = self.cb_action.currentData()
        try:
            params = self._collect_action_params()
        except Exception as exc:
            self._show("原始帧解析失败：{error}", "Raw frame parse failed: {error}", 4000, error=exc)
            return
        schedule = self._collect_schedule()
        enabled = self.cb_enabled.isChecked()

        if self._selected_id:
            self.manager.update(
                self._selected_id,
                name=name,
                enabled=enabled,
                mode=mode,
                addr_val=addr_val,
                unaddr=unaddr,
                action=action,
                params=params,
                schedule=schedule,
            )
            self._show("已保存修改", "Changes saved", 1500)
        else:
            tid = self.manager.create(name, mode, addr_val, unaddr, action, params, schedule, enabled)
            self._selected_id = tid
            self._show("已创建任务", "Task created", 1500)
        self._refresh_table()

    def _on_del(self):
        task = self._selected_task()
        if not task:
            return
        self.manager.delete(task.id)
        self._show("已删除", "Deleted", 1500)
        self._clear_form()
        self._refresh_table()

    def _on_toggle(self):
        task = self._selected_task()
        if not task:
            return
        self.manager.update(task.id, enabled=not task.enabled)
        self._show("启用状态已更新", "Enable state toggled", 1500)
        self._refresh_table()

    def _on_run(self):
        task = self._selected_task()
        if not task:
            return
        self.manager.run_now(task.id)
        self._show("任务执行完成", "Task executed", 1500)
        self._refresh_table()

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("导出任务JSON", "Export task JSON"),
            str(self.manager.store_path),
            "JSON (*.json)",
        )
        if not path:
            return
        data = [t.__dict__ for t in self.manager.list()]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._show("已导出", "Exported", 1500)
        except Exception as exc:
            self._show("导出失败：{error}", "Export failed: {error}", 3000, error=exc)

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("导入任务JSON", "Import task JSON"),
            str(self.manager.store_path.parent),
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            tasks = json.load(open(path, "r", encoding="utf-8"))
            if not isinstance(tasks, list):
                raise ValueError("JSON 顶层需为列表")
            self.manager._tasks.clear()
            for entry in tasks:
                task = Task(**entry)
                self.manager._tasks[task.id] = task
            self.manager.save()
            self.manager.load()
            self._show("已导入", "Imported", 1500)
            self._refresh_table()
        except Exception as exc:
            self._show("导入失败：{error}", "Import failed: {error}", 3000, error=exc)

    # ------------------------------------------------------------------
    def _set_action_fields(self):
        action = self.cb_action.currentData()
        widgets = {
            "arc": [self.lbl_arc, self.sp_arc],
            "scene": [self.lbl_scene, self.sp_scene],
            "dt8_tc": [self.lbl_tc, self.sp_k],
            "dt8_xy": [self.lbl_xy, self.sp_x, self.sp_y],
            "dt8_rgbw": [self.lbl_rgbw, self.sp_r, self.sp_g, self.sp_b, self.sp_w],
            "raw": [self.lbl_raw, self.ed_raw],
        }
        for key, controls in widgets.items():
            show = key == action
            for ctrl in controls:
                ctrl.setVisible(show)

    def _set_schedule_fields(self):
        typ = self.cb_sched.currentData()
        self.lbl_once.setVisible(typ == "once")
        self.dt_once.setVisible(typ == "once")
        self.lbl_interval.setVisible(typ == "interval")
        self.sp_every.setVisible(typ == "interval")
        time_visible = typ in ("daily", "weekly")
        self.lbl_time.setVisible(time_visible)
        for i in range(self.line_time.count()):
            w = self.line_time.itemAt(i).widget()
            if w:
                w.setVisible(time_visible)
        week_visible = typ == "weekly"
        for chk in self._week_checks:
            chk.setVisible(week_visible)

    def _on_action_changed(self):
        self._set_action_fields()

    def _on_sched_changed(self):
        self._set_schedule_fields()

    # Helper methods (selection, CRUD etc.)
    # ...
