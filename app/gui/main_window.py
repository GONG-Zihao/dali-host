from __future__ import annotations
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QMessageBox, QApplication
)
from PySide6.QtGui import QAction
import logging

from app.core.controller import Controller
from app.core.config import get_app_config
from pathlib import Path
from app.i18n import i18n


def _tr_static(text: str, en_fallback: str | None = None) -> str:
    try:
        lang = getattr(i18n, "lang", "zh")
        if lang == "zh":
            return text
        translated = i18n.translate_text(text)
        if translated == text and en_fallback:
            return en_fallback
        return translated
    except Exception:
        return en_fallback or text

# 面板
from .panels.panel_dimming import PanelDimming
from PySide6.QtWidgets import QWidget  # 占位其余Tab
from .panels.panel_rw import PanelRW
from .panels.panel_groups import PanelGroups
from .panels.panel_scenes import PanelScenes
from .panels.panel_dt8_tc import PanelDt8Tc
from .panels.panel_dt8_color import PanelDt8Color
from .panels.panel_benchmark import PanelBenchmark
from .panels.panel_sender import PanelSender
from .panels.panel_inventory import PanelInventory
from .panels.panel_scheduler import PanelScheduler
from .panels.panel_config_io import PanelConfigIO
from app.core.presets import combined_presets
from app.core.events import bus
from .panels.panel_analysis import PanelAnalysis

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(i18n.t("app.title", _tr_static("DALI上位机")))
        self._log = logging.getLogger("GUI")

        # 配置&控制器
        root_dir = Path(__file__).resolve().parents[2]
        self._cfg = get_app_config(root_dir)
        self.ctrl = Controller(self._cfg)

        self._init_ui()

    def _init_ui(self):
        # 1) 先创建并设置状态栏——后续不再替换
        status = QStatusBar()
        self.setStatusBar(status)

        # 2) 再创建Tab和各个面板，并把 status 传进去
        self.tabs = QTabWidget()
        self.panel_dimming = PanelDimming(self.ctrl, status)
        self.tabs.addTab(self.panel_dimming, _tr_static("调光"))
        self.panel_rw = PanelRW(self.ctrl, status)
        self.tabs.addTab(self.panel_rw, _tr_static("变量读写"))
        tc_cfg = self._cfg.get("tc", {})
        self.tabs.addTab(PanelDt8Tc(self.ctrl, status, tc_cfg), _tr_static("色温（DT8 Tc）"))
        # 色彩（DT8）
        ops_cfg = self._cfg.get("ops", {})
        self.tabs.addTab(PanelScenes(self.ctrl, status), _tr_static("场景管理"))
        self.tabs.addTab(PanelGroups(self.ctrl, status), _tr_static("组管理"))
        root_dir = Path(__file__).resolve().parents[2]
        presets_all = combined_presets(root_dir, self._cfg)
        self.tabs.addTab(PanelDt8Color(self.ctrl, status, ops_cfg, presets_all), _tr_static("色彩（DT8）"))
        self.tabs.addTab(PanelSender(self.ctrl, status, root_dir), _tr_static("指令发送"))
        self.tabs.addTab(PanelInventory(self.ctrl, status, root_dir),_tr_static("设备清单", "Inventory"))

        self.tabs.addTab(PanelBenchmark(self.ctrl, status, root_dir), _tr_static("压力测试"))
        self.tabs.addTab(PanelAnalysis(self.ctrl, status, root_dir), _tr_static("数据分析"))
        self.tabs.addTab(PanelScheduler(self.ctrl, status, root_dir), _tr_static("定时任务"))
        self.tabs.addTab(PanelConfigIO(self.ctrl, status, root_dir, self._cfg), _tr_static("配置导入导出"))
        self.setCentralWidget(self.tabs)

        self._update_status()
        # 工具菜单
        menu_tools = self.menuBar().addMenu(_tr_static("工具"))
        self.act_connect = QAction(_tr_static("连接"), self)
        self.act_connect.triggered.connect(self._on_connect)
        self.act_disconnect = QAction(_tr_static("断开"), self)
        self.act_disconnect.triggered.connect(self._on_disconnect)
        menu_tools.addAction(self.act_connect)
        menu_tools.addAction(self.act_disconnect)

        # 帮助菜单
        menu_help = self.menuBar().addMenu(_tr_static("帮助"))
        act_about = QAction(_tr_static("关于"), self)
        act_about.triggered.connect(self._on_about)
        menu_help.addAction(act_about)

    def _update_status(self):
        st = i18n.t("status.connected", _tr_static("已连接")) if self.ctrl.is_connected() else i18n.t("status.disconnected", _tr_static("未连接"))
        self.statusBar().showMessage(i18n.t("status.message", "状态：{status}").format(status=st))

    def _on_connect(self):
        try:
            self.ctrl.connect()
            bus.connection_changed.emit(True)  # ← 广播“已连接”
            self.statusBar().showMessage(i18n.t("status.connected", _tr_static("已连接")), 1500)
            self._update_status()
        except Exception as e:
            self.statusBar().showMessage(i18n.t("status.connect.failed", "连接失败：{error}").format(error=e), 3000)

    def _on_disconnect(self):
        try:
            self.ctrl.disconnect()
        finally:
            bus.connection_changed.emit(False)  # ← 广播“未连接”
            self.statusBar().showMessage(i18n.t("status.disconnected.brief", _tr_static("已断开")), 1500)
            self._update_status()

    def _on_about(self):
        QMessageBox.information(
            self,
            i18n.t("dialog.about.title", _tr_static("关于")),
            i18n.t("dialog.about.body", _tr_static("DALI上位机（Python + Qt）\\n当前阶段：最小可用闭环（调光)"))
        )
