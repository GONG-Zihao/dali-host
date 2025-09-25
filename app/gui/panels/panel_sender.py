from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QComboBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QTextEdit,
    QSpinBox,
)
from PySide6.QtCore import Qt, QDateTime

from app.gui.widgets.base_panel import BasePanel
from app.gui.widgets.address_target import AddressTargetWidget
from app.core.utils.hexutil import parse_pairs, fmt_pair
from app.core.config import load_yaml
from app.core.dali.frames import addr_broadcast, addr_short, addr_group
from app.i18n import tr, trf


class PanelSender(BasePanel):
    """Command sender: quick commands / raw frames / history."""

    def __init__(self, controller, statusbar, root_dir: Path):
        super().__init__(controller, statusbar)
        self.root_dir = root_dir
        self._commands: List[dict] = []
        self._history: List[dict] = []
        self._history_path = root_dir / "数据" / "sender" / "history.json"
        self._history_path.parent.mkdir(parents=True, exist_ok=True)

        self._build_ui()
        self._load_commands()
        self._load_history()
        self.apply_language()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        self.addr_widget = AddressTargetWidget(self)
        root.addWidget(self.addr_widget)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_quick = self._build_tab_quick()
        self.tab_raw = self._build_tab_raw()
        self.tab_hist = self._build_tab_history()
        self.tabs.addTab(self.tab_quick, "快捷命令")
        self.tabs.addTab(self.tab_raw, "自定义帧")
        self.tabs.addTab(self.tab_hist, "历史记录")
        root.addWidget(self.tabs)
        root.addStretch(1)

        # 连接门控
        self.register_send_widgets([self.btn_send_quick, self.btn_send_raw])

    def _build_tab_quick(self) -> QWidget:
        w = QWidget(); g = QGridLayout(w)
        self.cb_cmd = QComboBox()
        self.sb_param = QSpinBox(); self.sb_param.setRange(0, 255); self.sb_param.setEnabled(False)
        self.le_preview = QLineEdit(); self.le_preview.setReadOnly(True)

        self.cb_cmd.currentIndexChanged.connect(self._on_cmd_changed)
        self.sb_param.valueChanged.connect(self._preview_quick)

        self.btn_send_quick = QPushButton()
        self.btn_send_quick.clicked.connect(self._send_quick)

        self.lbl_cmd = QLabel("命令：")
        self.lbl_param = QLabel("参数：")
        self.lbl_preview = QLabel("预览（addr data）：")

        g.addWidget(self.lbl_cmd, 0, 0); g.addWidget(self.cb_cmd, 0, 1, 1, 3)
        g.addWidget(self.lbl_param, 1, 0); g.addWidget(self.sb_param, 1, 1)
        g.addWidget(self.lbl_preview, 2, 0); g.addWidget(self.le_preview, 2, 1, 1, 3)
        g.addWidget(self.btn_send_quick, 3, 3)
        return w

    def _build_tab_raw(self) -> QWidget:
        w = QWidget(); g = QGridLayout(w)
        self.te_raw = QTextEdit()
        self.lbl_raw_hint = QLabel("两字节帧（多帧用分号或换行分隔）：")
        self.te_raw.setPlaceholderText("示例：\nFF 21\nC1 08\n或：FF 21; C1 08")
        self.btn_send_raw = QPushButton()
        self.btn_send_raw.clicked.connect(self._send_raw_seq)

        g.addWidget(self.lbl_raw_hint, 0, 0, 1, 2)
        g.addWidget(self.te_raw, 1, 0, 1, 2)
        g.addWidget(self.btn_send_raw, 2, 1)
        return w

    def _build_tab_history(self) -> QWidget:
        w = QWidget(); g = QGridLayout(w)
        self.list = QListWidget()
        self.btn_replay = QPushButton()
        self.btn_delete = QPushButton()
        self.btn_clear = QPushButton()
        self.btn_export = QPushButton()
        self.btn_import = QPushButton()

        self.btn_replay.clicked.connect(self._replay)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_export.clicked.connect(self._export)
        self.btn_import.clicked.connect(self._import)

        g.addWidget(self.list, 0, 0, 1, 5)
        g.addWidget(self.btn_replay, 1, 1)
        g.addWidget(self.btn_delete, 1, 2)
        g.addWidget(self.btn_clear, 1, 3)
        g.addWidget(self.btn_export, 2, 3)
        g.addWidget(self.btn_import, 2, 4)
        return w

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _addr_byte(self, is_command: bool) -> int:
        mode = self.addr_widget.mode()
        value = self.addr_widget.addr_value()
        unaddr = self.addr_widget.unaddressed()
        if mode == "short" and value is not None:
            return addr_short(value, is_command=is_command)
        if mode == "group" and value is not None:
            return addr_group(value, is_command=is_command)
        return addr_broadcast(is_command=is_command, unaddressed=unaddr)

    def _current_cmd(self) -> Optional[dict]:
        idx = self.cb_cmd.currentIndex()
        if idx < 0 or idx >= len(self._commands):
            return None
        return self._commands[idx]

    # ------------------------------------------------------------------
    # Quick tab logic
    # ------------------------------------------------------------------
    def _on_cmd_changed(self):
        cmd = self._current_cmd()
        if not cmd:
            return
        cmd_type = (cmd.get("type") or "").lower()
        if cmd_type == "base_plus_param":
            self.sb_param.setEnabled(True)
            self.sb_param.setMinimum(int(cmd.get("min", 0)))
            self.sb_param.setMaximum(int(cmd.get("max", 255)))
        else:
            self.sb_param.setEnabled(False)
        self._preview_quick()

    def _preview_quick(self):
        cmd = self._current_cmd()
        if not cmd:
            self.le_preview.clear()
            return
        cmd_type = (cmd.get("type") or "").lower()
        if cmd_type == "arc":
            addr = self._addr_byte(is_command=False)
            data = int(cmd.get("value", 0)) & 0xFF
        elif cmd_type == "base_plus_param":
            addr = self._addr_byte(is_command=True)
            data = (int(cmd.get("base", 0)) + int(self.sb_param.value())) & 0xFF
        else:
            self.le_preview.clear()
            return
        self.le_preview.setText(fmt_pair(addr, data))

    def _send_quick(self):
        cmd = self._current_cmd()
        if not cmd:
            return
        cmd_type = (cmd.get("type") or "").lower()
        if cmd_type == "arc":
            addr = self._addr_byte(is_command=False)
            data = int(cmd.get("value", 0)) & 0xFF
        elif cmd_type == "base_plus_param":
            addr = self._addr_byte(is_command=True)
            data = (int(cmd.get("base", 0)) + int(self.sb_param.value())) & 0xFF
        else:
            self.show_msg(tr("不支持的命令类型", "Unsupported command type"), 2000)
            return

        self.ctrl.send_raw(addr, data)
        label = str(cmd.get("name", "cmd"))
        if cmd_type == "base_plus_param":
            label += f"({self.sb_param.value()})"
        self._push_history([(addr, data)], label)
        self.show_msg(trf("已发送：{frame}", "Sent: {frame}", frame=fmt_pair(addr, data)), 1800)

    # ------------------------------------------------------------------
    # Raw tab logic
    # ------------------------------------------------------------------
    def _send_raw_seq(self):
        text = self.te_raw.toPlainText().strip()
        if not text:
            return
        try:
            pairs = parse_pairs(text)
        except Exception as exc:
            self.show_msg(trf("解析失败：{error}", "Parse failed: {error}", error=exc), 4000)
            return
        for addr, data in pairs:
            self.ctrl.send_raw(addr, data)
        self._push_history(pairs, "RAW")
        self.show_msg(trf("已发送 {count} 帧", "Sent {count} frame(s)", count=len(pairs)), 2000)

    # ------------------------------------------------------------------
    # History tab logic
    # ------------------------------------------------------------------
    def _push_history(self, frames: List[tuple[int, int]], label: str):
        item = {
            "ts": QDateTime.currentDateTime().toString(Qt.ISODate),
            "label": label,
            "frames": [[a, d] for a, d in frames],
        }
        self._history.append(item)
        self._append_item_to_list(item)
        self._save_history()

    def _append_item_to_list(self, item: Dict):
        text = f"[{item['ts']}] {item.get('label', '')}: " + "; ".join(fmt_pair(a, d) for a, d in item["frames"])
        QListWidgetItem(text, self.list)

    def _replay(self):
        row = self.list.currentRow()
        if row < 0:
            return
        item = self._history[row]
        for addr, data in item["frames"]:
            self.ctrl.send_raw(int(addr), int(data))
        self.show_msg(tr("已重放", "Replayed"), 1500)

    def _delete(self):
        row = self.list.currentRow()
        if row < 0:
            return
        del self._history[row]
        self.list.takeItem(row)
        self._save_history()

    def _clear(self):
        self._history.clear()
        self.list.clear()
        self._save_history()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("导出历史为JSON", "Export history as JSON"),
            str(self._history_path),
            "JSON (*.json)",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._history, f, ensure_ascii=False, indent=2)
        self.show_msg(tr("已导出", "Exported"), 1500)

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("导入JSON为历史", "Import JSON as history"),
            str(self._history_path.parent),
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            data = json.load(open(path, "r", encoding="utf-8"))
        except Exception as exc:
            self.show_msg(trf("导入失败：{error}", "Import failed: {error}", error=exc), 4000)
            return
        if not isinstance(data, list):
            self.show_msg(tr("JSON格式应为列表", "JSON must be a list"), 2500)
            return
        self._history.extend(data)
        self.list.clear()
        for item in self._history:
            self._append_item_to_list(item)
        self._save_history()
        self.show_msg(tr("已导入", "Imported"), 1500)

    # ------------------------------------------------------------------
    # Data persistence
    # ------------------------------------------------------------------
    def _load_commands(self):
        path = self.root_dir / "配置" / "commands.yaml"
        if path.exists():
            cfg = load_yaml(path)
            self._commands = list(cfg.get("commands", [])) if cfg else []
        else:
            self._commands = []
        self.cb_cmd.clear()
        for cmd in self._commands:
            self.cb_cmd.addItem(cmd.get("name", "cmd"))
        if self._commands:
            self._on_cmd_changed()

    def _save_history(self):
        try:
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_history(self):
        if self._history_path.exists():
            try:
                self._history = json.load(open(self._history_path, "r", encoding="utf-8")) or []
            except Exception:
                self._history = []
        for item in self._history:
            self._append_item_to_list(item)

    # ------------------------------------------------------------------
    # Language refresh
    # ------------------------------------------------------------------
    def apply_language(self):
        self.addr_widget.apply_language()

        idx = self.tabs.indexOf(self.tab_quick)
        if idx >= 0:
            self.tabs.setTabText(idx, tr("快捷命令", "Quick Command"))
        idx = self.tabs.indexOf(self.tab_raw)
        if idx >= 0:
            self.tabs.setTabText(idx, tr("自定义帧", "Custom frames"))
        idx = self.tabs.indexOf(self.tab_hist)
        if idx >= 0:
            self.tabs.setTabText(idx, tr("历史记录", "History"))

        self.lbl_cmd.setText(tr("命令：", "Command:"))
        self.lbl_param.setText(tr("参数：", "Parameter:"))
        self.lbl_preview.setText(tr("预览（addr data）：", "Preview (addr data):"))
        self.btn_send_quick.setText(tr("发送", "Send"))

        self.lbl_raw_hint.setText(tr("两字节帧（多帧用分号或换行分隔）：", "Each frame is two bytes (use semicolon/newline to separate)"))
        self.te_raw.setPlaceholderText(
            tr(
                "示例：\nFF 21\nC1 08\n或：FF 21; C1 08",
                "Example:\nFF 21\nC1 08\nor: FF 21; C1 08",
            )
        )
        self.btn_send_raw.setText(tr("发送帧/序列", "Send frames"))

        self.btn_replay.setText(tr("重放", "Replay"))
        self.btn_delete.setText(tr("删除", "Delete"))
        self.btn_clear.setText(tr("清空", "Clear"))
        self.btn_export.setText(tr("导出JSON", "Export JSON"))
        self.btn_import.setText(tr("导入JSON", "Import JSON"))
