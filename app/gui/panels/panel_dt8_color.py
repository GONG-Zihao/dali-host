from __future__ import annotations
import logging
from typing import Dict, List, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QDoubleSpinBox,
    QSpinBox,
    QSlider,
)
from PySide6.QtCore import Qt
from app.gui.widgets.base_panel import BasePanel
from app.gui.widgets.address_target import AddressTargetWidget
from app.i18n import tr, trf, i18n


class PanelDt8Color(BasePanel):
    """DT8 色彩：xy 与 RGBW 两种方式 + 预设色板"""
    def __init__(self, controller, statusbar, ops_cfg: dict | None = None, presets: List[dict] | None = None):
        super().__init__(controller, statusbar)
        self._log = logging.getLogger("PanelDt8Color")
        self.ops_cfg = ops_cfg or {}
        self.presets = presets or []
        self._rgbw: Dict[str, tuple[QSlider, QSpinBox, QPushButton]] = {}
        self._send_buttons: List[QPushButton] = []  # 用于连接门控
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)

        self.addr_widget = AddressTargetWidget(self)
        root.addWidget(self.addr_widget)

        # Tabs：xy / RGBW
        self.tabs = QTabWidget()
        self.xy_tab = self._build_xy_tab()
        self.rgbw_tab = self._build_rgbw_tab()
        self.tabs.addTab(self.xy_tab, "xy")
        self.tabs.addTab(self.rgbw_tab, "RGBW")
        root.addWidget(self.tabs)

        # 预设色板
        self.presets_box = self._build_presets()
        root.addWidget(self.presets_box)
        root.addStretch(1)

        # 连接门控：注册所有发送类按钮
        self.register_send_widgets(self._send_buttons)

    def _addr(self):
        return (
            self.addr_widget.mode(),
            self.addr_widget.addr_value(),
            self.addr_widget.unaddressed(),
        )

    # ---------- xy ----------
    def _build_xy_tab(self):
        w = QWidget(); g = QGridLayout(w)
        self.sp_x = QDoubleSpinBox(); self.sp_y = QDoubleSpinBox()
        for sp in (self.sp_x, self.sp_y):
            sp.setDecimals(4); sp.setRange(0.0, 1.0); sp.setSingleStep(0.0005)
        self.sp_x.setValue(0.313); self.sp_y.setValue(0.329)  # 近似D65
        self.lbl_x = QLabel()
        self.lbl_y = QLabel()
        self.btn_set_xy = QPushButton()
        self.btn_set_xy.clicked.connect(self._apply_xy)
        g.addWidget(self.lbl_x, 0, 0); g.addWidget(self.sp_x, 0, 1)
        g.addWidget(self.lbl_y, 0, 2); g.addWidget(self.sp_y, 0, 3)
        g.addWidget(self.btn_set_xy, 0, 4)
        self._send_buttons.append(self.btn_set_xy)
        return w

    def _apply_xy(self):
        mode, addr_val, unaddr = self._addr()
        x, y = self.sp_x.value(), self.sp_y.value()
        try:
            out = self.ctrl.dt8_set_xy(mode, x, y, addr_val=addr_val, unaddr=unaddr)
            self.show_msg(
                trf(
                    "已设置 xy=({x:.4f},{y:.4f}) → ({ux},{uy})",
                    "Set xy=({x:.4f},{y:.4f}) → ({ux},{uy})",
                    x=out['x'], y=out['y'], ux=out['x_u16'], uy=out['y_u16']
                ),
                2500,
            )
        except Exception as e:
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    # ---------- RGBW ----------
    def _build_rgbw_tab(self):
        w = QWidget(); g = QGridLayout(w)

        self._rgbw_labels: Dict[str, QLabel] = {}

        def add_channel_row(row: int, label: str):
            slider = QSlider(Qt.Horizontal); slider.setRange(0, 254); slider.setValue(0)
            spin   = QSpinBox(); spin.setRange(0, 254)
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            btn = QPushButton()
            btn.clicked.connect(lambda l=label: self._apply_single_primary(l.lower()))
            lbl = QLabel()
            g.addWidget(lbl,    row, 0)
            g.addWidget(slider, row, 1, 1, 2)
            g.addWidget(spin,   row, 3)
            g.addWidget(btn,    row, 4)
            self._rgbw[label.lower()] = (slider, spin, btn)
            self._rgbw_labels[label.lower()] = lbl
            self._send_buttons.append(btn)

        # 固定通道
        row = 0
        for ch in ["R", "G", "B", "W"]:
            add_channel_row(row, ch); row += 1
        # 额外通道（如配置定义了 a/f）
        prim = (self.ops_cfg.get("dt8_set_primary") or {})
        for ch in ["A", "F"]:
            if ch.lower() in prim:
                add_channel_row(row, ch); row += 1

        self.btn_all = QPushButton()
        self.btn_all.clicked.connect(self._apply_all_rgbw)
        g.addWidget(self.btn_all, row, 3)
        self._send_buttons.append(self.btn_all)
        return w

    def _apply_single_primary(self, ch: str):
        mode, addr_val, unaddr = self._addr()
        _, spin, _btn = self._rgbw[ch]
        val = spin.value()
        try:
            out = self.ctrl.dt8_set_primary(mode, ch, val, addr_val=addr_val, unaddr=unaddr)
            self.show_msg(
                trf("已设置 {channel}={level}", "Set {channel}={level}", channel=ch.upper(), level=out['level']),
                2000,
            )
        except Exception as e:
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    def _apply_all_rgbw(self):
        mode, addr_val, unaddr = self._addr()
        try:
            for ch, (_sl, sp, _btn) in self._rgbw.items():
                self.ctrl.dt8_set_primary(mode, ch, sp.value(), addr_val=addr_val, unaddr=unaddr)
            self.show_msg(tr("已发送全部通道", "All channels sent"), 2000)
        except Exception as e:
            self.show_msg(trf("失败：{error}", "Failed: {error}", error=e), 5000)

    # ---------- 预设色板 ----------
    def _build_presets(self):
        box = QGroupBox()
        g = QGridLayout(box)
        col_per_row = 4
        if not self.presets:
            self.lbl_no_preset = QLabel("（在 配置/dali.yaml 的 presets: 添加你的色板，或导入 JSON）")
            g.addWidget(self.lbl_no_preset, 0, 0, 1, 4)
            return box

        self.preset_buttons: List[QPushButton] = []
        for i, p in enumerate(self.presets):
            original = p.get("name", f"预设{i+1}")
            btn = QPushButton(original)
            btn.setProperty("preset_name", original)
            btn.clicked.connect(lambda _=False, preset=p: self._apply_preset(preset))
            r, c = divmod(i, col_per_row)
            g.addWidget(btn, r, c)
            self._send_buttons.append(btn)
            self.preset_buttons.append(btn)
        return box

    def _apply_preset(self, p: Dict[str, Any]):
        mode, addr_val, unaddr = self._addr()
        try:
            m = (p.get("mode") or "").lower()
            if m == "rgbw":
                vals = p.get("values", {})
                for ch, (sl, sp, _btn) in self._rgbw.items():
                    if ch in vals:
                        sp.setValue(int(vals[ch]))
                for ch, val in vals.items():
                    if ch in self._rgbw:
                        self.ctrl.dt8_set_primary(mode, ch, int(val), addr_val=addr_val, unaddr=unaddr)
                self.show_msg(trf("已应用预设：{name}", "Preset applied: {name}", name=p.get('name')), 2200)
            elif m == "xy":
                vals = p.get("values", {})
                x, y = float(vals.get("x", 0.313)), float(vals.get("y", 0.329))
                self.sp_x.setValue(x); self.sp_y.setValue(y)
                self.ctrl.dt8_set_xy(mode, x, y, addr_val=addr_val, unaddr=unaddr)
                self.show_msg(trf("已应用预设：{name} (xy)", "Preset applied: {name} (xy)", name=p.get('name')), 2200)
            elif m == "tc":
                k = int(p.get("kelvin", 4000))
                out = self.ctrl.dt8_set_tc_kelvin(mode, k, addr_val=addr_val, unaddr=unaddr)
                self.show_msg(trf("已应用预设：{name}（{kelvin}K）", "Preset applied: {name} ({kelvin}K)", name=p.get('name'), kelvin=out['kelvin']), 2200)
            else:
                self.show_msg(tr("未知预设类型", "Unknown preset type"), 3000)
        except Exception as e:
            self.show_msg(trf("预设失败：{error}", "Preset failed: {error}", error=e), 5000)

    def apply_language(self):
        self.addr_widget.apply_language()

        idx = self.tabs.indexOf(self.xy_tab)
        if idx >= 0:
            self.tabs.setTabText(idx, tr("xy", "xy"))
        idx = self.tabs.indexOf(self.rgbw_tab)
        if idx >= 0:
            self.tabs.setTabText(idx, tr("RGBW", "RGBW"))

        self.lbl_x.setText(tr("x ∈ [0,1]：", "x ∈ [0,1]:"))
        self.lbl_y.setText(tr("y ∈ [0,1]：", "y ∈ [0,1]:"))
        self.btn_set_xy.setText(tr("设置 xy", "Set xy"))

        channel_labels = {
            "r": ("R：", "R:"),
            "g": ("G：", "G:"),
            "b": ("B：", "B:"),
            "w": ("W：", "W:"),
            "a": ("A：", "A:"),
            "f": ("F：", "F:"),
        }
        for ch, lbl in self._rgbw_labels.items():
            zh, en = channel_labels.get(ch, (f"{ch.upper()}：", f"{ch.upper()}:"))
            lbl.setText(tr(zh, en))
        for ch, (_slider, _spin, btn) in self._rgbw.items():
            btn.setText(tr(f"发送{ch.upper()}", f"Send {ch.upper()}"))

        self.btn_all.setText(tr("发送全部", "Send all"))

        self.presets_box.setTitle(tr("预设色板", "Preset color palette"))
        if hasattr(self, "lbl_no_preset"):
            self.lbl_no_preset.setText(tr("（在 配置/dali.yaml 的 presets: 添加你的色板，或导入 JSON）",
                                         "(Add palettes in config/dali.yaml presets or import JSON)"))

        preset_map = {
            "红": "Red",
            "绿": "Green",
            "蓝": "Blue",
            "暖白(2700K)": "Warm white (2700K)",
            "中性白(4000K)": "Neutral white (4000K)",
            "冷白(6500K)": "Cool white (6500K)",
            "演示红": "Demo red",
        }
        for btn in getattr(self, "preset_buttons", []):
            orig = btn.property("preset_name") or btn.text()
            if getattr(i18n, "lang", "zh") == "en":
                btn.setText(preset_map.get(orig, orig))
            else:
                btn.setText(orig)
