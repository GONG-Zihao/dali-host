from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QRadioButton, QSpinBox,
    QDoubleSpinBox, QCheckBox, QLabel, QPushButton, QFileDialog, QComboBox,
    QHBoxLayout
)
from PySide6.QtCore import Qt, QThread, QDateTime

from app.core.bench.worker import BenchPlan, BenchWorker
from app.gui.widgets.base_panel import BasePanel
from app.i18n import tr, trf, i18n


def _bind_text(widget, zh: str, en: str, store: list):
    widget.setProperty("_zh", zh)
    widget.setProperty("_en", en)
    if hasattr(widget, "setTitle"):
        widget.setTitle(tr(zh, en))
    elif hasattr(widget, "setText"):
        widget.setText(tr(zh, en))
    store.append(widget)


def _apply_bound_text(widgets: list):
    lang = getattr(i18n, "lang", "zh")
    for widget in widgets:
        zh = widget.property("_zh")
        en = widget.property("_en")
        if zh is None or en is None:
            continue
        text = tr(zh, en)
        if hasattr(widget, "setTitle"):
            widget.setTitle(text)
        elif hasattr(widget, "setText"):
            widget.setText(text)


class PanelBenchmark(BasePanel):
    """Benchmark panel for stress testing command sequences."""

    def __init__(self, controller, statusbar, root_dir: Path):
        super().__init__(controller, statusbar)
        self._log = logging.getLogger("PanelBenchmark")
        self.root_dir = root_dir
        self._thread: Optional[QThread] = None
        self._worker: Optional[BenchWorker] = None
        self._last_result: Optional[dict] = None
        self._i18n_widgets: list = []
        self._task_items: list[tuple[str, str, str]] = []
        self._build_ui()
        self.apply_language()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
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

        # 任务与参数
        self.box_task = QGroupBox()
        tg = QGridLayout(self.box_task)
        self.cb_task = QComboBox()
        self._task_items = [
            ("ARC：固定亮度", "ARC: Fixed brightness", "arc_fixed"),
            ("ARC：亮度扫描(lo→hi，步长)", "ARC: Sweep (lo→hi, step)", "arc_sweep"),
            ("场景回放", "Scene recall", "scene_recall"),
            ("DT8：Tc 固定K", "DT8: Fixed Tc", "dt8_tc_fixed"),
            ("DT8：xy 固定", "DT8: Fixed xy", "dt8_xy_fixed"),
            ("DT8：RGBW 固定", "DT8: Fixed RGBW", "dt8_rgbw_fixed"),
        ]
        for zh, _en, key in self._task_items:
            self.cb_task.addItem(zh, key)

        self.sp_arc = QSpinBox(); self.sp_arc.setRange(0, 254); self.sp_arc.setValue(128)
        self.sp_lo = QSpinBox(); self.sp_lo.setRange(0, 254)
        self.sp_hi = QSpinBox(); self.sp_hi.setRange(0, 254); self.sp_hi.setValue(254)
        self.sp_step = QSpinBox(); self.sp_step.setRange(1, 50); self.sp_step.setValue(5)
        self.sp_scene = QSpinBox(); self.sp_scene.setRange(0, 15)
        self.sp_k = QSpinBox(); self.sp_k.setRange(1000, 20000); self.sp_k.setValue(4000)
        self.sp_x = QDoubleSpinBox(); self.sp_x.setDecimals(4); self.sp_x.setRange(0.0, 1.0); self.sp_x.setSingleStep(0.0005); self.sp_x.setValue(0.3130)
        self.sp_y = QDoubleSpinBox(); self.sp_y.setDecimals(4); self.sp_y.setRange(0.0, 1.0); self.sp_y.setSingleStep(0.0005); self.sp_y.setValue(0.3290)
        self.sp_r = QSpinBox(); self.sp_r.setRange(0, 254)
        self.sp_g = QSpinBox(); self.sp_g.setRange(0, 254)
        self.sp_b = QSpinBox(); self.sp_b.setRange(0, 254)
        self.sp_w = QSpinBox(); self.sp_w.setRange(0, 254)
        self.sp_total = QSpinBox(); self.sp_total.setRange(1, 100000); self.sp_total.setValue(100)
        self.sp_interval = QSpinBox(); self.sp_interval.setRange(0, 5000); self.sp_interval.setValue(50); self.sp_interval.setSuffix(" ms")
        self.sp_timeout = QSpinBox(); self.sp_timeout.setRange(0, 5000); self.sp_timeout.setValue(0); self.sp_timeout.setSuffix(" ms")

        self.lbl_task = QLabel("任务：")
        self.lbl_arc = QLabel("ARC：")
        self.lbl_lohi = QLabel("lo/hi/step：")
        self.lbl_scene = QLabel("场景：")
        self.lbl_kelvin = QLabel("Kelvin：")
        self.lbl_xy = QLabel("x / y：")
        self.lbl_rgbw = QLabel("R / G / B / W：")
        self.lbl_total = QLabel("总次数：")
        self.lbl_interval = QLabel("间隔：")
        self.lbl_timeout = QLabel("接收超时（可留0）：")

        row = 0
        tg.addWidget(self.lbl_task, row, 0); tg.addWidget(self.cb_task, row, 1, 1, 3); row += 1
        tg.addWidget(self.lbl_arc, row, 0); tg.addWidget(self.sp_arc, row, 1); row += 1
        tg.addWidget(self.lbl_lohi, row, 0)
        rowbox = QHBoxLayout(); rowbox.addWidget(self.sp_lo); rowbox.addWidget(self.sp_hi); rowbox.addWidget(self.sp_step)
        tg.addLayout(rowbox, row, 1, 1, 3); row += 1
        tg.addWidget(self.lbl_scene, row, 0); tg.addWidget(self.sp_scene, row, 1); row += 1
        tg.addWidget(self.lbl_kelvin, row, 0); tg.addWidget(self.sp_k, row, 1); row += 1
        tg.addWidget(self.lbl_xy, row, 0)
        rowbox2 = QHBoxLayout(); rowbox2.addWidget(self.sp_x); rowbox2.addWidget(self.sp_y)
        tg.addLayout(rowbox2, row, 1, 1, 3); row += 1
        tg.addWidget(self.lbl_rgbw, row, 0)
        rowbox3 = QHBoxLayout()
        for spin in (self.sp_r, self.sp_g, self.sp_b, self.sp_w):
            rowbox3.addWidget(spin)
        tg.addLayout(rowbox3, row, 1, 1, 3); row += 1

        tg.addWidget(self.lbl_total, row, 0); tg.addWidget(self.sp_total, row, 1)
        tg.addWidget(self.lbl_interval, row, 2); tg.addWidget(self.sp_interval, row, 3); row += 1
        tg.addWidget(self.lbl_timeout, row, 0); tg.addWidget(self.sp_timeout, row, 1); row += 1

        self.btn_start = QPushButton()
        self.btn_stop = QPushButton()
        self.btn_export = QPushButton()
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_export.clicked.connect(self._on_export)
        tg.addWidget(self.btn_start, row, 1); tg.addWidget(self.btn_stop, row, 2); tg.addWidget(self.btn_export, row, 3)

        root.addWidget(self.box_task)

        # 统计信息
        self.box_stat = QGroupBox()
        sg = QGridLayout(self.box_stat)
        self.lb_sent = QLabel("0")
        self.lb_ok = QLabel("0")
        self.lb_err = QLabel("0")
        self.lb_last = QLabel("0.0 ms")
        self.lb_avg = QLabel("0.0 ms")
        self.lb_min = QLabel("0.0 ms")
        self.lb_max = QLabel("0.0 ms")
        self.lbl_sent = QLabel("Sent:")
        self.lbl_ok = QLabel("OK:")
        self.lbl_err = QLabel("Err:")
        self.lbl_last = QLabel("Last:")
        self.lbl_avg = QLabel("Avg:")
        self.lbl_min = QLabel("Min:")
        self.lbl_max = QLabel("Max:")
        sg.addWidget(self.lbl_sent, 0, 0); sg.addWidget(self.lb_sent, 0, 1)
        sg.addWidget(self.lbl_ok, 0, 2); sg.addWidget(self.lb_ok, 0, 3)
        sg.addWidget(self.lbl_err, 0, 4); sg.addWidget(self.lb_err, 0, 5)
        sg.addWidget(self.lbl_last, 1, 0); sg.addWidget(self.lb_last, 1, 1)
        sg.addWidget(self.lbl_avg, 1, 2); sg.addWidget(self.lb_avg, 1, 3)
        sg.addWidget(self.lbl_min, 1, 4); sg.addWidget(self.lb_min, 1, 5)
        sg.addWidget(self.lbl_max, 1, 6); sg.addWidget(self.lb_max, 1, 7)
        root.addWidget(self.box_stat)
        root.addStretch(1)

        # 连接门控
        self.register_send_widgets([self.btn_start])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _read_addr(self):
        if self.rb_s.isChecked():
            return "short", self.sb_s.value(), False
        if self.rb_g.isChecked():
            return "group", self.sb_g.value(), False
        return "broadcast", None, self.chk_unaddr.isChecked()

    def _build_plan(self) -> BenchPlan:
        mode, addr_val, unaddr = self._read_addr()
        task = self.cb_task.currentData()
        params: Dict[str, Any] = {}
        if task == "arc_fixed":
            params = {"arc": self.sp_arc.value()}
        elif task == "arc_sweep":
            params = {"lo": self.sp_lo.value(), "hi": self.sp_hi.value(), "step": self.sp_step.value()}
        elif task == "scene_recall":
            params = {"scene": self.sp_scene.value()}
        elif task == "dt8_tc_fixed":
            params = {"kelvin": self.sp_k.value()}
        elif task == "dt8_xy_fixed":
            params = {"x": self.sp_x.value(), "y": self.sp_y.value()}
        elif task == "dt8_rgbw_fixed":
            params = {"r": self.sp_r.value(), "g": self.sp_g.value(), "b": self.sp_b.value(), "w": self.sp_w.value()}
        return BenchPlan(
            mode=mode,
            addr_val=addr_val,
            unaddr=unaddr,
            task=task,
            params=params,
            total=self.sp_total.value(),
            interval_ms=self.sp_interval.value(),
            recv_timeout_ms=self.sp_timeout.value(),
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_start(self):
        if self._thread and self._thread.isRunning():
            return
        plan = self._build_plan()
        worker = BenchWorker(self.ctrl, plan, self.root_dir)
        worker.signals.status.connect(self._on_status)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)

        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.signals.finished.connect(thread.quit)
        worker.signals.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._worker = worker
        self._thread = thread
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.show_msg(tr("压力测试开始", "Stress test started"), 1500)
        thread.start()

    def _on_stop(self):
        if self._worker:
            self._worker.stop()
            self.show_msg(tr("正在停止…", "Stopping..."), 1200)
        self.btn_stop.setEnabled(False)

    def _on_status(self, payload: dict):
        self.lb_sent.setText(str(payload.get("sent", 0)))
        self.lb_ok.setText(str(payload.get("ok", 0)))
        self.lb_err.setText(str(payload.get("err", 0)))
        self.lb_last.setText(f"{payload.get('last_ms', 0.0):.1f} ms")
        self.lb_avg.setText(f"{payload.get('avg_ms', 0.0):.1f} ms")
        self.lb_min.setText(f"{payload.get('min_ms', 0.0):.1f} ms")
        self.lb_max.setText(f"{payload.get('max_ms', 0.0):.1f} ms")
        tooltip = payload.get("last_log")
        if tooltip:
            self.lb_last.setToolTip(tooltip)

    def _on_finished(self, result: dict):
        self._last_result = result
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(bool(result))
        self.show_msg(tr("压力测试完成", "Stress test finished"), 2000)

    def _on_error(self, message: str):
        self.show_msg(trf("加载任务失败：{error}", "Benchmark error: {error}", error=message), 4000)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(False)

    def _on_export(self):
        if not self._last_result:
            return
        default = self.root_dir / "数据" / "bench" / f"bench_{i18n.lang}_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.csv"
        default.parent.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, tr("导出CSV", "Export CSV"), str(default), "CSV (*.csv)")
        if not path:
            return
        header = ["timestamp", "sent", "ok", "err", "avg_ms", "min_ms", "max_ms"]
        rows = self._last_result.get("rows", [])
        lines = [",".join(header)]
        for row in rows:
            lines.append(
                ",".join(str(row.get(key, "")) for key in header)
            )
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.show_msg(trf("已导出：{path}", "Exported to {path}", path=path), 2000)

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------
    def apply_language(self):
        _bind_text(self.box_addr, "地址选择", "Address selection", self._i18n_widgets)
        _bind_text(self.rb_b, "广播", "Broadcast", self._i18n_widgets)
        _bind_text(self.chk_unaddr, "仅未寻址", "Not addressed only", self._i18n_widgets)
        _bind_text(self.rb_s, "短地址", "Short address", self._i18n_widgets)
        _bind_text(self.rb_g, "组地址", "Group address", self._i18n_widgets)

        _bind_text(self.box_task, "压力任务", "Stress tasks", self._i18n_widgets)
        _bind_text(self.lbl_task, "任务：", "Task:", self._i18n_widgets)
        _bind_text(self.lbl_arc, "ARC：", "ARC:", self._i18n_widgets)
        _bind_text(self.lbl_lohi, "lo/hi/step：", "lo/hi/step:", self._i18n_widgets)
        _bind_text(self.lbl_scene, "场景：", "Scene:", self._i18n_widgets)
        _bind_text(self.lbl_kelvin, "Kelvin：", "Kelvin:", self._i18n_widgets)
        _bind_text(self.lbl_xy, "x / y：", "x / y:", self._i18n_widgets)
        _bind_text(self.lbl_rgbw, "R / G / B / W：", "R / G / B / W:", self._i18n_widgets)
        _bind_text(self.lbl_total, "总次数：", "Total count:", self._i18n_widgets)
        _bind_text(self.lbl_interval, "间隔：", "Interval:", self._i18n_widgets)
        _bind_text(self.lbl_timeout, "接收超时（可留0）：", "Receive timeout (leave 0 to skip):", self._i18n_widgets)
        _bind_text(self.btn_start, "开始", "Start", self._i18n_widgets)
        _bind_text(self.btn_stop, "停止", "Stop", self._i18n_widgets)
        _bind_text(self.btn_export, "导出CSV", "Export CSV", self._i18n_widgets)

        _bind_text(self.box_stat, "实时统计", "Real-time statistics", self._i18n_widgets)
        _bind_text(self.lbl_sent, "Sent:", "Sent:", self._i18n_widgets)
        _bind_text(self.lbl_ok, "OK:", "OK:", self._i18n_widgets)
        _bind_text(self.lbl_err, "Err:", "Errors:", self._i18n_widgets)
        _bind_text(self.lbl_last, "Last:", "Last:", self._i18n_widgets)
        _bind_text(self.lbl_avg, "Avg:", "Avg:", self._i18n_widgets)
        _bind_text(self.lbl_min, "Min:", "Min:", self._i18n_widgets)
        _bind_text(self.lbl_max, "Max:", "Max:", self._i18n_widgets)

        # Combo items
        for index, (zh, en, _key) in enumerate(self._task_items):
            self.cb_task.setItemText(index, tr(zh, en))

        _apply_bound_text(self._i18n_widgets)
