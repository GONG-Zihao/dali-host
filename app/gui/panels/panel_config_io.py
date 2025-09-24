from __future__ import annotations
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QLabel, QPushButton,
    QFileDialog, QCheckBox, QLineEdit, QTextEdit
)

from app.core.io.state_io import load_state, save_state, empty_template, StateFile
from app.core.io.apply import apply_groups, apply_scenes
from app.core.presets import load_user_presets, save_user_presets
from app.i18n import tr, trf


class PanelConfigIO(QWidget):
    """Import/export of group/scene/DT8 presets."""

    def __init__(self, controller, statusbar, root_dir: Path, cfg: dict):
        super().__init__()
        self.ctrl = controller
        self.statusbar = statusbar
        self.root_dir = root_dir
        self.cfg = cfg
        self._loaded: Optional[StateFile] = None

        self._build_ui()
        self.apply_language()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # Import section
        self.box_in = QGroupBox()
        ig = QGridLayout(self.box_in)

        self.le_path = QLineEdit()
        self.btn_browse = QPushButton()
        self.chk_groups = QCheckBox()
        self.chk_clear_others = QCheckBox()
        self.chk_scenes = QCheckBox()
        self.chk_recall = QCheckBox()
        self.chk_presets = QCheckBox()
        self.btn_apply = QPushButton()

        self.btn_browse.clicked.connect(self._browse)
        self.btn_apply.clicked.connect(self._apply)

        ig.addWidget(self.le_path, 0, 0, 1, 3)
        ig.addWidget(self.btn_browse, 0, 3)
        ig.addWidget(self.chk_groups, 1, 0)
        ig.addWidget(self.chk_clear_others, 1, 1)
        ig.addWidget(self.chk_scenes, 2, 0)
        ig.addWidget(self.chk_recall, 2, 1)
        ig.addWidget(self.chk_presets, 3, 0)
        ig.addWidget(self.btn_apply, 4, 3)
        root.addWidget(self.box_in)

        # Export section
        self.box_out = QGroupBox()
        og = QGridLayout(self.box_out)

        self.btn_tpl = QPushButton()
        self.btn_preset = QPushButton()
        self.lbl_info = QLabel()
        self.te_info = QTextEdit(); self.te_info.setReadOnly(True)

        self.btn_tpl.clicked.connect(self._export_template)
        self.btn_preset.clicked.connect(self._export_presets)

        og.addWidget(self.btn_tpl, 0, 0)
        og.addWidget(self.btn_preset, 0, 1)
        og.addWidget(self.lbl_info, 1, 0, 1, 2)
        og.addWidget(self.te_info, 2, 0, 1, 2)
        root.addWidget(self.box_out)
        root.addStretch(1)

    # ------------------------------------------------------------------
    def apply_language(self):
        self.box_in.setTitle(tr("导入并应用", "Import and apply"))
        self.le_path.setPlaceholderText(tr("选择一个 JSON 文件…", "Select a JSON file..."))
        self.btn_browse.setText(tr("浏览…", "Browse..."))
        self.chk_groups.setText(tr("应用 组成员关系", "Apply group memberships"))
        self.chk_clear_others.setText(tr("应用组时清空未列出组", "Clear unlisted groups when applying"))
        self.chk_scenes.setText(tr("应用 场景亮度表", "Apply scene brightness table"))
        self.chk_recall.setText(tr("写入场景后回放验证", "Playback verification after writing"))
        self.chk_presets.setText(tr("导入 DT8 预设（写入用户预设文件）", "Import DT8 presets (write to user preset files)"))
        self.btn_apply.setText(tr("导入并应用", "Import and apply"))

        self.box_out.setTitle(tr("导出", "Export"))
        self.btn_tpl.setText(tr("导出空模板", "Export empty template"))
        self.btn_preset.setText(tr("导出当前预设", "Export current preset"))
        self.lbl_info.setText(tr("最近一次导入解析信息：", "Latest import parse info:"))

    # ------------------------------------------------------------------
    def _show(self, zh: str, en: str, ms: int = 2000, **kwargs):
        message = trf(zh, en, **kwargs)
        try:
            self.statusbar.showMessage(message, ms)
        except Exception:
            pass

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("选择 JSON", "Choose JSON"),
            str(self.root_dir),
            "JSON (*.json)",
        )
        if not path:
            return
        self.le_path.setText(path)
        try:
            state = load_state(Path(path))
            self._loaded = state
            self._render_info(state)
            self._show("已加载 JSON", "JSON loaded", 1200)
        except Exception as exc:
            self._loaded = None
            self.te_info.setPlainText(trf("解析失败：{error}", "Parse failed: {error}", error=exc))
            self._show("解析失败", "Parse failed", 2000)

    def _render_info(self, state: StateFile):
        lines = [f"version: {state.version}"]
        lines.append(trf("groups: {count} 条", "groups: {count}", count=len(state.groups)))
        lines.append(trf("scenes: {count} 条", "scenes: {count}", count=len(state.scenes)))
        lines.append(trf("dt8_presets: {count} 条", "dt8_presets: {count}", count=len(state.dt8_presets)))
        for entry in state.groups[:5]:
            lines.append(f"  short {entry.short} -> groups {entry.groups}")
        for entry in state.scenes[:5]:
            lines.append(f"  short {entry.short} -> levels {entry.levels}")
        for preset in state.dt8_presets[:5]:
            lines.append(f"  preset: {preset.get('name')}")
        self.te_info.setPlainText('\n'.join(lines))

    def _apply(self):
        if not self._loaded:
            self._show("请先加载 JSON", "Load the JSON file first", 2000)
            return
        state = self._loaded
        if self.chk_groups.isChecked() and state.groups:
            apply_groups(self.ctrl, state.groups, clear_others=self.chk_clear_others.isChecked())
        if self.chk_scenes.isChecked() and state.scenes:
            apply_scenes(self.ctrl, state.scenes, recall_after_store=self.chk_recall.isChecked())
        if self.chk_presets.isChecked() and state.dt8_presets is not None:
            user_path = self.root_dir / "数据" / "presets.json"
            save_user_presets(user_path, state.dt8_presets)
        self._show("导入/应用完成", "Import/apply complete", 2500)

    def _export_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("导出空模板", "Export empty template"),
            str(self.root_dir / "数据" / "state_template.json"),
            "JSON (*.json)",
        )
        if not path:
            return
        save_state(Path(path), empty_template())
        self._show("已导出空模板", "Empty template exported", 1500)

    def _export_presets(self):
        user_path = self.root_dir / "数据" / "presets.json"
        presets = load_user_presets(user_path) or self.cfg.get("presets", [])
        state = empty_template()
        state.dt8_presets = presets
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("导出当前预设", "Export current preset"),
            str(self.root_dir / "数据" / "presets_export.json"),
            "JSON (*.json)",
        )
        if not path:
            return
        save_state(Path(path), state)
        self._show("已导出当前预设", "Current preset exported", 1500)
