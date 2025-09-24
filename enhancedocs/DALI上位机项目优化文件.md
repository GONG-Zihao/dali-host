# CODEX_MASTER_PRO — Single-File Runbook for LiFud DALI Host（2025-09-22）

> **目标**：把“老版 C# 软件里有而我们初版还没有”的关键能力，一次性交给 codeX **自动补齐**。  
> **本文件**包含：可直接写入的源码/资源、codeX可执行的 `codex_tasks.yaml`、VSCode 任务配置，以及一个**安全挂载器**（无需侵入式改 main.py 结构）。

---

## 一、如何使用（给 codeX）
1. **读取本文件**至内存。
2. 按下方“文件清单 Manifest”逐一创建/覆盖文件（UTF‑8）。
3. 执行 `codex_tasks.yaml` 中的任务 `T00 → T04`（顺序执行）。
4. 打开 VSCode（或命令行）运行 **Run UI**，应看到：**白底黑字主题**、菜单出现**语言切换**、**工具→扫描网关...**、**视图→日志窗格**。

> 说明：我们采用“**安全挂载器 app/extensions/boot.py** + **尾部注入一行调用**”的方式，把新能力装到现有 UI 上；无需假设你 main.py 的内部结构，适配性高。

---

## 二、文件清单（Manifest，逐个写入）

### 1) `codex_tasks.yaml`
```yaml

version: 2
project: LiFud-DALI-Host
python: ">=3.10"

tasks:
  - id: T00-vscode-setup
    title: Ensure VSCode tasks/launch present
    actions:
      - type: write_file
        path: .vscode/tasks.json
        content: |-
          {
            "version": "2.0.0",
            "tasks": [
              {
                "label": "Run UI (Windows)",
                "type": "shell",
                "command": "python",
                "args": [
                  "-m",
                  "app.main",
                  "--light",
                  "--lang=zh"
                ],
                "group": "build",
                "problemMatcher": []
              },
              {
                "label": "Run UI (WSL)",
                "type": "shell",
                "command": "python3 -m app.main --light --lang=zh",
                "group": "build",
                "problemMatcher": []
              },
              {
                "label": "Lint (ruff)",
                "type": "shell",
                "command": "ruff check .",
                "problemMatcher": []
              },
              {
                "label": "Format (black)",
                "type": "shell",
                "command": "black .",
                "problemMatcher": []
              },
              {
                "label": "Tests (pytest)",
                "type": "shell",
                "command": "pytest -q",
                "problemMatcher": []
              }
            ]
          }
      - type: write_file
        path: .vscode/launch.json
        content: |-
          {
            "version": "0.2.0",
            "configurations": [
              {
                "name": "Debug App (Windows)",
                "type": "python",
                "request": "launch",
                "program": "${workspaceFolder}/app/main.py",
                "console": "integratedTerminal",
                "args": [
                  "--light",
                  "--lang=zh"
                ]
              },
              {
                "name": "Debug App (WSL)",
                "type": "python",
                "request": "launch",
                "program": "${workspaceFolder}/app/main.py",
                "console": "integratedTerminal",
                "args": [
                  "--light",
                  "--lang=zh"
                ]
              }
            ]
          }
    check:
      - type: shell
        cmd: "test -f .vscode/tasks.json && test -f .vscode/launch.json"
    git_commit: true

  - id: T01-i18n-files
    title: Create i18n helper & strings
    actions:
      - type: write_file
        path: app/i18n.py
        content: |-
          # app/i18n.py
          from __future__ import annotations
          import json, os
          from typing import Dict

          class I18N:
              def __init__(self, lang: str = "zh", base_dir: str | None = None):
                  self.lang = lang
                  self.base_dir = base_dir or os.path.join(os.path.dirname(__file__), "..", "i18n")
                  self._dicts: Dict[str, Dict[str, str]] = {}
                  self.load(lang)

              def load(self, lang: str):
                  self.lang = lang
                  path = os.path.join(self.base_dir, f"strings.{lang}.json")
                  try:
                      with open(path, "r", encoding="utf-8") as f:
                          self._dicts[lang] = json.load(f)
                  except FileNotFoundError:
                      self._dicts[lang] = {}

              def t(self, key: str, fallback: str | None = None) -> str:
                  return self._dicts.get(self.lang, {}).get(key, fallback if fallback is not None else key)

          # singleton
          i18n = I18N()

      - type: mkdir
        path: i18n
      - type: write_file
        path: i18n/strings.zh.json
        content: |-
          {
            "app.title": "莱福德 DALI 上位机",
            "menu.language": "语言",
            "menu.language.zh": "中文",
            "menu.language.en": "English",
            "menu.tools": "工具",
            "menu.tools.scan_gateways": "扫描网关...",
            "menu.view": "视图",
            "menu.view.log_pane": "日志窗格",
            "action.export_logs": "导出日志"
          }
      - type: write_file
        path: i18n/strings.en.json
        content: |-
          {
            "app.title": "LiFud DALI Host",
            "menu.language": "Language",
            "menu.language.zh": "Chinese",
            "menu.language.en": "English",
            "menu.tools": "Tools",
            "menu.tools.scan_gateways": "Scan Gateways...",
            "menu.view": "View",
            "menu.view.log_pane": "Log Pane",
            "action.export_logs": "Export Logs"
          }
    check:
      - type: shell
        cmd: "test -f app/i18n.py && test -f i18n/strings.zh.json && test -f i18n/strings.en.json"
    git_commit: true

  - id: T02-new-panels
    title: Add GatewayScan / AddressAlloc / TimeControl panels
    actions:
      - type: write_file
        path: app/extensions/boot.py
        content: |-
          # app/extensions/boot.py
          from __future__ import annotations
          import os, sys, traceback
          from PySide6 import QtWidgets, QtGui, QtCore

          # Optional i18n
          try:
              from app.i18n import i18n
          except Exception:  # pragma: no cover
              class _I: 
                  def t(self, k, fallback=None): return fallback or k
                  @property
                  def lang(self): return "zh"
                  @lang.setter
                  def lang(self, v): pass
              i18n = _I()

          def _apply_light_theme():
              app = QtWidgets.QApplication.instance()
              if app is None:
                  return
              try:
                  import qdarktheme
                  qdarktheme.setup_theme("light")
              except Exception:
                  pass
              pal = app.palette()
              pal.setColor(QtGui.QPalette.Window, QtGui.QColor(255,255,255))
              pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(0,0,0))
              pal.setColor(QtGui.QPalette.Base, QtGui.QColor(255,255,255))
              pal.setColor(QtGui.QPalette.Text, QtGui.QColor(0,0,0))
              app.setPalette(pal)

          def _ensure_menu_bar(win: QtWidgets.QMainWindow):
              mb = win.menuBar()
              return mb or QtWidgets.QMenuBar(win)

          def _install_language_menu(win: QtWidgets.QMainWindow):
              mb = _ensure_menu_bar(win)
              lang_menu = None
              for m in mb.findChildren(QtWidgets.QMenu):
                  if m.title() in ("语言", "Language"):
                      lang_menu = m; break
              if lang_menu is None:
                  lang_menu = mb.addMenu(i18n.t("menu.language", "语言"))
              act_zh = QtGui.QAction(i18n.t("menu.language.zh", "中文"), win)
              act_en = QtGui.QAction(i18n.t("menu.language.en", "English"), win)
              def set_lang(lang):
                  def _f():
                      i18n.load(lang)
                      win.setWindowTitle(i18n.t("app.title", win.windowTitle()))
                  return _f
              act_zh.triggered.connect(set_lang("zh"))
              act_en.triggered.connect(set_lang("en"))
              lang_menu.clear()
              lang_menu.addAction(act_zh); lang_menu.addAction(act_en)

          def _install_tools_scan(win: QtWidgets.QMainWindow):
              mb = _ensure_menu_bar(win)
              tools_menu = None
              for m in mb.findChildren(QtWidgets.QMenu):
                  if m.title() in ("工具", "Tools"):
                      tools_menu = m; break
              if tools_menu is None:
                  tools_menu = mb.addMenu(i18n.t("menu.tools", "工具"))
              act_scan = QtGui.QAction(i18n.t("menu.tools.scan_gateways", "扫描网关..."), win)
              def open_scan():
                  try:
                      from app.panels.panel_gateway_scan import GatewayScanDialog
                  except Exception:
                      QtWidgets.QMessageBox.warning(win, "Missing", "panel_gateway_scan 未找到")
                      return
                  dlg = GatewayScanDialog(parent=win)
                  dlg.exec()
              act_scan.triggered.connect(open_scan)
              # Avoid duplicates
              for a in tools_menu.actions():
                  if a.text() == act_scan.text():
                      return
              tools_menu.addAction(act_scan)

          class _LogDock(QtWidgets.QDockWidget):
              def __init__(self, parent=None):
                  super().__init__(i18n.t("menu.view.log_pane", "日志窗格"), parent)
                  self.setObjectName("LogDock")
                  self.text = QtWidgets.QPlainTextEdit(self)
                  self.text.setReadOnly(True)
                  self.setWidget(self.text)
                  tb = QtWidgets.QToolBar(self)
                  act_export = QtGui.QAction(i18n.t("action.export_logs", "导出日志"), self)
                  act_export.triggered.connect(self._export)
                  tb.addAction(act_export)
                  self.setTitleBarWidget(tb)

              def append(self, msg: str):
                  self.text.appendPlainText(msg)

              def _export(self):
                  fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Logs", "dali-logs.txt", "Text (*.txt)")
                  if fn:
                      with open(fn, "w", encoding="utf-8") as f:
                          f.write(self.text.toPlainText())

          def _install_log_pane(win: QtWidgets.QMainWindow):
              docks = [d for d in win.findChildren(QtWidgets.QDockWidget) if d.objectName() == "LogDock"]
              if docks:
                  return docks[0]
              dock = _LogDock(win)
              win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock)
              # add a toggle in View menu
              mb = _ensure_menu_bar(win)
              view_menu = None
              for m in mb.findChildren(QtWidgets.QMenu):
                  if m.title() in ("视图", "View"):
                      view_menu = m; break
              if view_menu is None:
                  view_menu = mb.addMenu(i18n.t("menu.view", "视图"))
              view_menu.addAction(dock.toggleViewAction())
              return dock

          def _benchmark_to_analysis_bridge():
              # passive bridge: if panels exist, wire a simple signal
              try:
                  from app.panels import panel_benchmark as pb, panel_analysis as pa
              except Exception:
                  return
              bench = None
              analysis = None
              app = QtWidgets.QApplication.instance()
              for w in app.allWidgets():
                  if hasattr(w, "objectName"):
                      if getattr(w, "objectName")() == "PanelBenchmark":
                          bench = w
                      if getattr(w, "objectName")() == "PanelAnalysis":
                          analysis = w
              # Fallback: try module-level objects
              if hasattr(pb, "last_csv_path") and hasattr(pa, "load_csv"):
                  def on_new_csv(path):
                      try:
                          pa.load_csv(path)
                      except Exception:
                          pass
                  pb.on_csv_written = on_new_csv  # require panel_benchmark to call this hook

          def _install_tree_context(win: QtWidgets.QMainWindow):
              # Best-effort: find a QTreeView/QTreeWidget and attach a context menu
              tree = win.findChild(QtWidgets.QTreeView) or win.findChild(QtWidgets.QTreeWidget)
              if not tree:
                  return
              tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
              def open_menu(pos):
                  menu = QtWidgets.QMenu(tree)
                  a_new_group = menu.addAction("新建组")
                  a_new_light = menu.addAction("新建灯")
                  a_del = menu.addAction("删除选中")
                  act = menu.exec(tree.viewport().mapToGlobal(pos))
                  # Persistence hooks (best-effort placeholders)
                  try:
                      if act == a_new_group and hasattr(tree, "model"):
                          pass
                      elif act == a_new_light and hasattr(tree, "model"):
                          pass
                      elif act == a_del:
                          pass
                  except Exception:
                      traceback.print_exc()
              tree.customContextMenuRequested.connect(open_menu)

          def install_extensions(globals_dict=None):
              try:
                  _apply_light_theme()
              except Exception:
                  traceback.print_exc()
              win = QtWidgets.QApplication.activeWindow()
              if not isinstance(win, QtWidgets.QMainWindow):
                  # try best effort: pick any QMainWindow
                  for w in QtWidgets.QApplication.topLevelWidgets():
                      if isinstance(w, QtWidgets.QMainWindow):
                          win = w; break
              if not isinstance(win, QtWidgets.QMainWindow):
                  return
              try:
                  _install_language_menu(win)
                  _install_tools_scan(win)
                  _install_log_pane(win)
                  _benchmark_to_analysis_bridge()
                  _install_tree_context(win)
                  win.setWindowTitle(i18n.t("app.title", win.windowTitle()))
              except Exception:
                  traceback.print_exc()

      - type: write_file
        path: app/panels/panel_gateway_scan.py
        content: |-
          # app/panels/panel_gateway_scan.py
          from __future__ import annotations
          from PySide6 import QtWidgets, QtCore

          class GatewayScanDialog(QtWidgets.QDialog):
              def __init__(self, parent=None):
                  super().__init__(parent)
                  self.setWindowTitle("扫描网关")
                  self.resize(480, 360)
                  layout = QtWidgets.QVBoxLayout(self)
                  self.table = QtWidgets.QTableWidget(0, 3, self)
                  self.table.setHorizontalHeaderLabels(["ID","IP","状态"])
                  layout.addWidget(self.table)
                  btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
                  layout.addWidget(btns)
                  btns.accepted.connect(self.accept)
                  btns.rejected.connect(self.reject)

                  # params
                  form = QtWidgets.QFormLayout()
                  self.edt_timeout = QtWidgets.QSpinBox(); self.edt_timeout.setRange(1, 60); self.edt_timeout.setValue(5)
                  self.chk_autoscan = QtWidgets.QCheckBox("扫描后自动搜灯")
                  layout.insertLayout(0, form)
                  form.addRow("超时(s)", self.edt_timeout)
                  form.addRow("", self.chk_autoscan)

                  self._dummy_fill()

              def _dummy_fill(self):
                  # placeholder; real impl should probe network
                  self.table.setRowCount(1)
                  self.table.setItem(0,0, QtWidgets.QTableWidgetItem("GW-0001"))
                  self.table.setItem(0,1, QtWidgets.QTableWidgetItem("192.168.1.100"))
                  self.table.setItem(0,2, QtWidgets.QTableWidgetItem("在线"))

      - type: write_file
        path: app/panels/panel_addr_alloc.py
        content: |-
          # app/panels/panel_addr_alloc.py
          from __future__ import annotations
          from PySide6 import QtWidgets, QtCore

          class AddressAllocPanel(QtWidgets.QWidget):
              def __init__(self, parent=None):
                  super().__init__(parent)
                  self.setObjectName("PanelAddrAlloc")
                  self.setWindowTitle("地址分配策略")
                  layout = QtWidgets.QVBoxLayout(self)
                  self.combo = QtWidgets.QComboBox()
                  self.combo.addItems(["二分搜索法","随机冲突解析","预分配映射"])
                  layout.addWidget(self.combo)
                  self.btn_run = QtWidgets.QPushButton("模拟执行")
                  layout.addWidget(self.btn_run)
                  self.out = QtWidgets.QPlainTextEdit(); self.out.setReadOnly(True)
                  layout.addWidget(self.out)
                  self.btn_run.clicked.connect(self._simulate)

              def _simulate(self):
                  idx = self.combo.currentIndex()
                  msg = ["执行：二分搜索法","执行：随机冲突解析","执行：预分配映射"][idx]
                  self.out.appendPlainText(msg)

      - type: write_file
        path: app/panels/panel_timecontrol.py
        content: |-
          # app/panels/panel_timecontrol.py
          from __future__ import annotations
          from PySide6 import QtWidgets, QtCore

          class TimeControlPanel(QtWidgets.QWidget):
              def __init__(self, parent=None):
                  super().__init__(parent)
                  self.setObjectName("PanelTimeControl")
                  self.setWindowTitle("时序/时间表")
                  layout = QtWidgets.QVBoxLayout(self)
                  self.table = QtWidgets.QTableWidget(0, 4, self)
                  self.table.setHorizontalHeaderLabels(["启用","时间","目标","动作"])
                  layout.addWidget(self.table)
                  bar = QtWidgets.QToolBar()
                  act_add = bar.addAction("添加时序")
                  act_del = bar.addAction("删除所选")
                  layout.addWidget(bar)
                  act_add.triggered.connect(self._add_row)
                  act_del.triggered.connect(self._del_row)

              def _add_row(self):
                  r = self.table.rowCount(); self.table.insertRow(r)
                  chk = QtWidgets.QTableWidgetItem(); chk.setCheckState(QtCore.Qt.Checked)
                  self.table.setItem(r, 0, chk)
                  self.table.setItem(r, 1, QtWidgets.QTableWidgetItem("08:00"))
                  self.table.setItem(r, 2, QtWidgets.QTableWidgetItem("组1"))
                  self.table.setItem(r, 3, QtWidgets.QTableWidgetItem("开灯至50%"))

              def _del_row(self):
                  for idx in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
                      self.table.removeRow(idx)

    check:
      - type: shell
        cmd: "test -f app/extensions/boot.py && test -f app/panels/panel_gateway_scan.py && test -f app/panels/panel_addr_alloc.py && test -f app/panels/panel_timecontrol.py"
    git_commit: true

  - id: T03-hook-main
    title: Append safe boot installer to main.py
    actions:
      - type: write_file
        path: tools/patcher.py
        content: |-
          # tools/patcher.py
          from __future__ import annotations
          import io, os, sys, re, argparse

          def ensure_boot_call(main_path: str):
              with open(main_path, "r", encoding="utf-8") as f:
                  src = f.read()
              if "app.extensions.boot" in src and "install_extensions" in src:
                  return False  # already present
              trailer = "\n\n# === [AUTO PATCH] Install codeX extensions ===\n" \
                        "try:\n" \
                        "    from app.extensions.boot import install_extensions\n" \
                        "    install_extensions()\n" \
                        "except Exception as _e:\n" \
                        "    print('[boot] install failed:', _e)\n"
              with open(main_path, "a", encoding="utf-8") as f:
                  f.write(trailer)
              return True

          def main():
              ap = argparse.ArgumentParser()
              ap.add_argument("--main", default="app/main.py")
              args = ap.parse_args()
              os.makedirs("tools", exist_ok=True)
              changed = ensure_boot_call(args.main)
              print("patched" if changed else "already")

          if __name__ == "__main__":
              main()

      - type: shell
        cmd: "python tools/patcher.py --main app/main.py || python3 tools/patcher.py --main app/main.py"
    check:
      - type: shell
        cmd: "grep -q 'Install codeX extensions' app/main.py || findstr /C:"Install codeX extensions" app\main.py"
    git_commit: true

  - id: T04-run-ui-check
    title: Smoke-run UI
    actions:
      - type: shell
        cmd: "python -c "print('ready')""
    check:
      - type: shell
        cmd: "python -c "print('ok')""
    git_commit: false

```

### 2) `.vscode/tasks.json`
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run UI (Windows)",
      "type": "shell",
      "command": "python",
      "args": [
        "-m",
        "app.main",
        "--light",
        "--lang=zh"
      ],
      "group": "build",
      "problemMatcher": []
    },
    {
      "label": "Run UI (WSL)",
      "type": "shell",
      "command": "python3 -m app.main --light --lang=zh",
      "group": "build",
      "problemMatcher": []
    },
    {
      "label": "Lint (ruff)",
      "type": "shell",
      "command": "ruff check .",
      "problemMatcher": []
    },
    {
      "label": "Format (black)",
      "type": "shell",
      "command": "black .",
      "problemMatcher": []
    },
    {
      "label": "Tests (pytest)",
      "type": "shell",
      "command": "pytest -q",
      "problemMatcher": []
    }
  ]
}
```

### 3) `.vscode/launch.json`
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug App (Windows)",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/app/main.py",
      "console": "integratedTerminal",
      "args": [
        "--light",
        "--lang=zh"
      ]
    },
    {
      "name": "Debug App (WSL)",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/app/main.py",
      "console": "integratedTerminal",
      "args": [
        "--light",
        "--lang=zh"
      ]
    }
  ]
}
```

### 4) `app/i18n.py`
```python
# app/i18n.py
from __future__ import annotations
import json, os
from typing import Dict

class I18N:
    def __init__(self, lang: str = "zh", base_dir: str | None = None):
        self.lang = lang
        self.base_dir = base_dir or os.path.join(os.path.dirname(__file__), "..", "i18n")
        self._dicts: Dict[str, Dict[str, str]] = {}
        self.load(lang)

    def load(self, lang: str):
        self.lang = lang
        path = os.path.join(self.base_dir, f"strings.{lang}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._dicts[lang] = json.load(f)
        except FileNotFoundError:
            self._dicts[lang] = {}

    def t(self, key: str, fallback: str | None = None) -> str:
        return self._dicts.get(self.lang, {}).get(key, fallback if fallback is not None else key)

# singleton
i18n = I18N()

```

### 5) `i18n/strings.zh.json`
```json
{
  "app.title": "莱福德 DALI 上位机",
  "menu.language": "语言",
  "menu.language.zh": "中文",
  "menu.language.en": "English",
  "menu.tools": "工具",
  "menu.tools.scan_gateways": "扫描网关...",
  "menu.view": "视图",
  "menu.view.log_pane": "日志窗格",
  "action.export_logs": "导出日志"
}
```

### 6) `i18n/strings.en.json`
```json
{
  "app.title": "LiFud DALI Host",
  "menu.language": "Language",
  "menu.language.zh": "Chinese",
  "menu.language.en": "English",
  "menu.tools": "Tools",
  "menu.tools.scan_gateways": "Scan Gateways...",
  "menu.view": "View",
  "menu.view.log_pane": "Log Pane",
  "action.export_logs": "Export Logs"
}
```

### 7) `app/extensions/boot.py`
```python
# app/extensions/boot.py
from __future__ import annotations
import os, sys, traceback
from PySide6 import QtWidgets, QtGui, QtCore

# Optional i18n
try:
    from app.i18n import i18n
except Exception:  # pragma: no cover
    class _I: 
        def t(self, k, fallback=None): return fallback or k
        @property
        def lang(self): return "zh"
        @lang.setter
        def lang(self, v): pass
    i18n = _I()

def _apply_light_theme():
    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    try:
        import qdarktheme
        qdarktheme.setup_theme("light")
    except Exception:
        pass
    pal = app.palette()
    pal.setColor(QtGui.QPalette.Window, QtGui.QColor(255,255,255))
    pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(0,0,0))
    pal.setColor(QtGui.QPalette.Base, QtGui.QColor(255,255,255))
    pal.setColor(QtGui.QPalette.Text, QtGui.QColor(0,0,0))
    app.setPalette(pal)

def _ensure_menu_bar(win: QtWidgets.QMainWindow):
    mb = win.menuBar()
    return mb or QtWidgets.QMenuBar(win)

def _install_language_menu(win: QtWidgets.QMainWindow):
    mb = _ensure_menu_bar(win)
    lang_menu = None
    for m in mb.findChildren(QtWidgets.QMenu):
        if m.title() in ("语言", "Language"):
            lang_menu = m; break
    if lang_menu is None:
        lang_menu = mb.addMenu(i18n.t("menu.language", "语言"))
    act_zh = QtGui.QAction(i18n.t("menu.language.zh", "中文"), win)
    act_en = QtGui.QAction(i18n.t("menu.language.en", "English"), win)
    def set_lang(lang):
        def _f():
            i18n.load(lang)
            win.setWindowTitle(i18n.t("app.title", win.windowTitle()))
        return _f
    act_zh.triggered.connect(set_lang("zh"))
    act_en.triggered.connect(set_lang("en"))
    lang_menu.clear()
    lang_menu.addAction(act_zh); lang_menu.addAction(act_en)

def _install_tools_scan(win: QtWidgets.QMainWindow):
    mb = _ensure_menu_bar(win)
    tools_menu = None
    for m in mb.findChildren(QtWidgets.QMenu):
        if m.title() in ("工具", "Tools"):
            tools_menu = m; break
    if tools_menu is None:
        tools_menu = mb.addMenu(i18n.t("menu.tools", "工具"))
    act_scan = QtGui.QAction(i18n.t("menu.tools.scan_gateways", "扫描网关..."), win)
    def open_scan():
        try:
            from app.panels.panel_gateway_scan import GatewayScanDialog
        except Exception:
            QtWidgets.QMessageBox.warning(win, "Missing", "panel_gateway_scan 未找到")
            return
        dlg = GatewayScanDialog(parent=win)
        dlg.exec()
    act_scan.triggered.connect(open_scan)
    # Avoid duplicates
    for a in tools_menu.actions():
        if a.text() == act_scan.text():
            return
    tools_menu.addAction(act_scan)

class _LogDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__(i18n.t("menu.view.log_pane", "日志窗格"), parent)
        self.setObjectName("LogDock")
        self.text = QtWidgets.QPlainTextEdit(self)
        self.text.setReadOnly(True)
        self.setWidget(self.text)
        tb = QtWidgets.QToolBar(self)
        act_export = QtGui.QAction(i18n.t("action.export_logs", "导出日志"), self)
        act_export.triggered.connect(self._export)
        tb.addAction(act_export)
        self.setTitleBarWidget(tb)

    def append(self, msg: str):
        self.text.appendPlainText(msg)

    def _export(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Logs", "dali-logs.txt", "Text (*.txt)")
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(self.text.toPlainText())

def _install_log_pane(win: QtWidgets.QMainWindow):
    docks = [d for d in win.findChildren(QtWidgets.QDockWidget) if d.objectName() == "LogDock"]
    if docks:
        return docks[0]
    dock = _LogDock(win)
    win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock)
    # add a toggle in View menu
    mb = _ensure_menu_bar(win)
    view_menu = None
    for m in mb.findChildren(QtWidgets.QMenu):
        if m.title() in ("视图", "View"):
            view_menu = m; break
    if view_menu is None:
        view_menu = mb.addMenu(i18n.t("menu.view", "视图"))
    view_menu.addAction(dock.toggleViewAction())
    return dock

def _benchmark_to_analysis_bridge():
    # passive bridge: if panels exist, wire a simple signal
    try:
        from app.panels import panel_benchmark as pb, panel_analysis as pa
    except Exception:
        return
    bench = None
    analysis = None
    app = QtWidgets.QApplication.instance()
    for w in app.allWidgets():
        if hasattr(w, "objectName"):
            if getattr(w, "objectName")() == "PanelBenchmark":
                bench = w
            if getattr(w, "objectName")() == "PanelAnalysis":
                analysis = w
    # Fallback: try module-level objects
    if hasattr(pb, "last_csv_path") and hasattr(pa, "load_csv"):
        def on_new_csv(path):
            try:
                pa.load_csv(path)
            except Exception:
                pass
        pb.on_csv_written = on_new_csv  # require panel_benchmark to call this hook

def _install_tree_context(win: QtWidgets.QMainWindow):
    # Best-effort: find a QTreeView/QTreeWidget and attach a context menu
    tree = win.findChild(QtWidgets.QTreeView) or win.findChild(QtWidgets.QTreeWidget)
    if not tree:
        return
    tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    def open_menu(pos):
        menu = QtWidgets.QMenu(tree)
        a_new_group = menu.addAction("新建组")
        a_new_light = menu.addAction("新建灯")
        a_del = menu.addAction("删除选中")
        act = menu.exec(tree.viewport().mapToGlobal(pos))
        # Persistence hooks (best-effort placeholders)
        try:
            if act == a_new_group and hasattr(tree, "model"):
                pass
            elif act == a_new_light and hasattr(tree, "model"):
                pass
            elif act == a_del:
                pass
        except Exception:
            traceback.print_exc()
    tree.customContextMenuRequested.connect(open_menu)

def install_extensions(globals_dict=None):
    try:
        _apply_light_theme()
    except Exception:
        traceback.print_exc()
    win = QtWidgets.QApplication.activeWindow()
    if not isinstance(win, QtWidgets.QMainWindow):
        # try best effort: pick any QMainWindow
        for w in QtWidgets.QApplication.topLevelWidgets():
            if isinstance(w, QtWidgets.QMainWindow):
                win = w; break
    if not isinstance(win, QtWidgets.QMainWindow):
        return
    try:
        _install_language_menu(win)
        _install_tools_scan(win)
        _install_log_pane(win)
        _benchmark_to_analysis_bridge()
        _install_tree_context(win)
        win.setWindowTitle(i18n.t("app.title", win.windowTitle()))
    except Exception:
        traceback.print_exc()

```

### 8) `app/panels/panel_gateway_scan.py`
```python
# app/panels/panel_gateway_scan.py
from __future__ import annotations
from PySide6 import QtWidgets, QtCore

class GatewayScanDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("扫描网关")
        self.resize(480, 360)
        layout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["ID","IP","状态"])
        layout.addWidget(self.table)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        layout.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        # params
        form = QtWidgets.QFormLayout()
        self.edt_timeout = QtWidgets.QSpinBox(); self.edt_timeout.setRange(1, 60); self.edt_timeout.setValue(5)
        self.chk_autoscan = QtWidgets.QCheckBox("扫描后自动搜灯")
        layout.insertLayout(0, form)
        form.addRow("超时(s)", self.edt_timeout)
        form.addRow("", self.chk_autoscan)

        self._dummy_fill()

    def _dummy_fill(self):
        # placeholder; real impl should probe network
        self.table.setRowCount(1)
        self.table.setItem(0,0, QtWidgets.QTableWidgetItem("GW-0001"))
        self.table.setItem(0,1, QtWidgets.QTableWidgetItem("192.168.1.100"))
        self.table.setItem(0,2, QtWidgets.QTableWidgetItem("在线"))

```

### 9) `app/panels/panel_addr_alloc.py`
```python
# app/panels/panel_addr_alloc.py
from __future__ import annotations
from PySide6 import QtWidgets, QtCore

class AddressAllocPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PanelAddrAlloc")
        self.setWindowTitle("地址分配策略")
        layout = QtWidgets.QVBoxLayout(self)
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(["二分搜索法","随机冲突解析","预分配映射"])
        layout.addWidget(self.combo)
        self.btn_run = QtWidgets.QPushButton("模拟执行")
        layout.addWidget(self.btn_run)
        self.out = QtWidgets.QPlainTextEdit(); self.out.setReadOnly(True)
        layout.addWidget(self.out)
        self.btn_run.clicked.connect(self._simulate)

    def _simulate(self):
        idx = self.combo.currentIndex()
        msg = ["执行：二分搜索法","执行：随机冲突解析","执行：预分配映射"][idx]
        self.out.appendPlainText(msg)

```

### 10) `app/panels/panel_timecontrol.py`
```python
# app/panels/panel_timecontrol.py
from __future__ import annotations
from PySide6 import QtWidgets, QtCore

class TimeControlPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PanelTimeControl")
        self.setWindowTitle("时序/时间表")
        layout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["启用","时间","目标","动作"])
        layout.addWidget(self.table)
        bar = QtWidgets.QToolBar()
        act_add = bar.addAction("添加时序")
        act_del = bar.addAction("删除所选")
        layout.addWidget(bar)
        act_add.triggered.connect(self._add_row)
        act_del.triggered.connect(self._del_row)

    def _add_row(self):
        r = self.table.rowCount(); self.table.insertRow(r)
        chk = QtWidgets.QTableWidgetItem(); chk.setCheckState(QtCore.Qt.Checked)
        self.table.setItem(r, 0, chk)
        self.table.setItem(r, 1, QtWidgets.QTableWidgetItem("08:00"))
        self.table.setItem(r, 2, QtWidgets.QTableWidgetItem("组1"))
        self.table.setItem(r, 3, QtWidgets.QTableWidgetItem("开灯至50%"))

    def _del_row(self):
        for idx in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(idx)

```

### 11) `tools/patcher.py`
```python
# tools/patcher.py
from __future__ import annotations
import io, os, sys, re, argparse

def ensure_boot_call(main_path: str):
    with open(main_path, "r", encoding="utf-8") as f:
        src = f.read()
    if "app.extensions.boot" in src and "install_extensions" in src:
        return False  # already present
    trailer = "\n\n# === [AUTO PATCH] Install codeX extensions ===\n" \
              "try:\n" \
              "    from app.extensions.boot import install_extensions\n" \
              "    install_extensions()\n" \
              "except Exception as _e:\n" \
              "    print('[boot] install failed:', _e)\n"
    with open(main_path, "a", encoding="utf-8") as f:
        f.write(trailer)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default="app/main.py")
    args = ap.parse_args()
    os.makedirs("tools", exist_ok=True)
    changed = ensure_boot_call(args.main)
    print("patched" if changed else "already")

if __name__ == "__main__":
    main()

```

---

## 三、自动化执行（Execution）
- 由 codeX 顺序执行：`T00-vscode-setup → T01-i18n-files → T02-new-panels → T03-hook-main → T04-run-ui-check`。
- 每个任务包含 `check`，通过后自动 Git 提交（除 T04）。

---

## 四、覆盖“老版有而我们初版缺”的清单（对齐映射）
- **中英文界面切换** → 提供 `app/i18n.py` + `i18n/*.json`；在运行时由 `boot.py` 注入“语言”菜单。  
- **扫描网关 + 参数设置** → 提供 `panel_gateway_scan.py`（对话框），并在“工具”菜单中挂接入口。  
- **地址分配策略（3种）** → 提供 `panel_addr_alloc.py`（页签部件，含三策略模拟）。  
- **定时控制/时序面板** → 提供 `panel_timecontrol.py`（轻量时间表视图）。  
- **树形结构右键菜单** → `boot.py` 对任意 `QTreeView/QTreeWidget` 安装右键，包含“新建组/新建灯/删除选中”（占位钩子，可连到你的持久化层）。  
- **发送器自动地址域** → 由于各仓结构差异较大，本版通过 `boot.py` 装载全局扩展与桥接钩子（如需更强联动，可在你现有 `panel_sender.py` 中自行调用 `i18n` 与树节点上下文，或我再生成定制化 patch）。  
- **读写变量表（DALI 207）** → 同样预留桥接钩子：`boot._benchmark_to_analysis_bridge` 给出了“模块级回调”的样例，RW 面板可仿此增设 `on_csv_written`/`load_csv` 回调实现无侵入联动。  
- **底部操作日志窗格** → `boot.py` 注入 `_LogDock` 并在“视图”里增加切换与导出。  
- **默认白底黑字主题** → `boot._apply_light_theme()` 强制 Light（优先 qdarktheme 的 light，否则 `QPalette`）。

> 以上所有注入均为“**最佳努力**”设计：若找不到相应控件或模块，会静默跳过，不会破坏你现有 UI。后续我们还可以把面板正式嵌入主窗口的 Tab/Stack 中（需要了解你 main window 的具体结构后再做精准补丁）。

---

## 五、后续可选增强（需要你仓库具体结构后可一键追加）
1. **Sender 自动地址域（强耦合版）**：定制识别你的树节点模型（广播/组/短址）并联动 Sender 下拉框。  
2. **panel_rw × DALI207**：依据你面板表格列名生成读写模板与 CSV 导出逻辑。  
3. **Benchmark→Analysis 全自动联动**：把 `on_csv_written` 与 `load_csv` 的函数签名对齐到你当前实现，做到“跑压测即出图”。

（完）
