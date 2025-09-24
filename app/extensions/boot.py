# app/extensions/boot.py
from __future__ import annotations
import logging
import os, sys, traceback
from PySide6 import QtWidgets, QtGui, QtCore

# Optional i18n
try:
    from app.i18n import i18n
except Exception:  # pragma: no cover
    class _I:
        def t(self, k, fallback=None):
            return fallback or k

        def translate_text(self, text):
            return text

        @property
        def lang(self):
            return "zh"

        @lang.setter
        def lang(self, _v):
            pass

    i18n = _I()


def _tr(text: str) -> str:
    try:
        return i18n.translate_text(text)
    except Exception:
        return text

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
        if m.title() in ("语言", "Language", _tr("语言"), _tr("Language")):
            lang_menu = m; break
    if lang_menu is None:
        lang_menu = mb.addMenu(_tr(i18n.t("menu.language", "语言")))
    else:
        lang_menu.setTitle(_tr(i18n.t("menu.language", lang_menu.title())))

    act_zh = QtGui.QAction(_tr(i18n.t("menu.language.zh", "中文")), win)
    act_en = QtGui.QAction(_tr(i18n.t("menu.language.en", "English")), win)

    def set_lang(lang):
        def _f():
            i18n.load(lang)
            win.setWindowTitle(_tr(i18n.t("app.title", win.windowTitle())))
            _apply_language_to_ui(win)
        return _f
    act_zh.triggered.connect(set_lang("zh"))
    act_en.triggered.connect(set_lang("en"))
    lang_menu.clear()
    lang_menu.addAction(act_zh); lang_menu.addAction(act_en)

def _install_tools_scan(win: QtWidgets.QMainWindow):
    mb = _ensure_menu_bar(win)
    tools_menu = None
    for m in mb.findChildren(QtWidgets.QMenu):
        if m.title() in ("工具", "Tools", _tr("工具"), _tr("Tools")):
            tools_menu = m; break
    if tools_menu is None:
        tools_menu = mb.addMenu(_tr(i18n.t("menu.tools", "工具")))
    else:
        tools_menu.setTitle(_tr(i18n.t("menu.tools", tools_menu.title())))

    act_scan = QtGui.QAction(_tr(i18n.t("menu.tools.scan_gateways", "扫描网关...")), win)
    def open_scan():
        try:
            from app.panels.panel_gateway_scan import GatewayScanDialog
        except Exception:
            QtWidgets.QMessageBox.warning(win, _tr("缺失"), _tr("panel_gateway_scan 未找到"))
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
        super().__init__(_tr(i18n.t("menu.view.log_pane", "日志窗格")), parent)
        self.setObjectName("LogDock")
        self.text = QtWidgets.QPlainTextEdit(self)
        self.text.setReadOnly(True)
        self.setWidget(self.text)
        tb = QtWidgets.QToolBar(self)
        act_export = QtGui.QAction(_tr(i18n.t("action.export_logs", "导出日志")), self)
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


class _DockLogHandler(logging.Handler):
    def __init__(self, dock: _LogDock):
        super().__init__()
        self._dock = dock

    def set_dock(self, dock: _LogDock):
        self._dock = dock

    def emit(self, record: logging.LogRecord):
        dock = self._dock
        if dock is None:
            return
        try:
            msg = self.format(record)
        except Exception:  # pragma: no cover
            msg = record.getMessage()
        QtCore.QTimer.singleShot(0, lambda m=msg: dock.append(m))


_LOG_HANDLER: _DockLogHandler | None = None


def _install_log_pane(win: QtWidgets.QMainWindow):
    docks = [d for d in win.findChildren(QtWidgets.QDockWidget) if d.objectName() == "LogDock"]
    if docks:
        dock = docks[0]
    else:
        dock = _LogDock(win)
        win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock)

    # add a toggle in View menu
    mb = _ensure_menu_bar(win)
    view_menu = None
    for m in mb.findChildren(QtWidgets.QMenu):
        if m.title() in ("视图", "View", _tr("视图"), _tr("View")):
            view_menu = m; break
    if view_menu is None:
        view_menu = mb.addMenu(_tr(i18n.t("menu.view", "视图")))
    else:
        view_menu.setTitle(_tr(i18n.t("menu.view", view_menu.title())))
    if dock.toggleViewAction() not in view_menu.actions():
        view_menu.addAction(dock.toggleViewAction())

    global _LOG_HANDLER
    if _LOG_HANDLER is None:
        handler = _DockLogHandler(dock)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        logging.getLogger().addHandler(handler)
        _LOG_HANDLER = handler
    else:
        _LOG_HANDLER.set_dock(dock)

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
        a_new_group = menu.addAction(_tr("新建组"))
        a_new_light = menu.addAction(_tr("新建灯"))
        a_del = menu.addAction(_tr("删除选中"))
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


def _apply_language_to_ui(win: QtWidgets.QMainWindow):
    """遍历常见控件，将文本替换成当前语言。"""

    def translate_action(action: QtGui.QAction):
        if action is None:
            return
        text = action.text()
        new_text = _tr(text)
        if new_text != text:
            action.setText(new_text)
        tip = action.toolTip()
        if tip:
            new_tip = _tr(tip)
            if new_tip != tip:
                action.setToolTip(new_tip)

    def translate_widget(widget: QtWidgets.QWidget):
        if isinstance(widget, QtWidgets.QTabWidget):
            for idx in range(widget.count()):
                text = widget.tabText(idx)
                new_text = _tr(text)
                if new_text != text:
                    widget.setTabText(idx, new_text)
        elif isinstance(widget, (QtWidgets.QGroupBox, QtWidgets.QDockWidget)):
            text = widget.title() if hasattr(widget, "title") else widget.windowTitle()
            new_text = _tr(text)
            if hasattr(widget, "setTitle"):
                if new_text != text:
                    widget.setTitle(new_text)
            elif hasattr(widget, "setWindowTitle") and new_text != text:
                widget.setWindowTitle(new_text)
        elif isinstance(widget, QtWidgets.QLabel):
            if widget.pixmap() is None:
                text = widget.text()
                if text and not text.startswith("<"):
                    new_text = _tr(text)
                    if new_text != text:
                        widget.setText(new_text)
        elif isinstance(widget, (QtWidgets.QPushButton, QtWidgets.QCheckBox, QtWidgets.QRadioButton, QtWidgets.QToolButton)):
            text = widget.text()
            new_text = _tr(text)
            if new_text != text:
                widget.setText(new_text)
        elif isinstance(widget, QtWidgets.QComboBox):
            for idx in range(widget.count()):
                text = widget.itemText(idx)
                new_text = _tr(text)
                if new_text != text:
                    widget.setItemText(idx, new_text)
        elif isinstance(widget, QtWidgets.QLineEdit):
            placeholder = widget.placeholderText()
            if placeholder:
                new_placeholder = _tr(placeholder)
                if new_placeholder != placeholder:
                    widget.setPlaceholderText(new_placeholder)
        elif isinstance(widget, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            placeholder = widget.placeholderText()
            if placeholder:
                new_placeholder = _tr(placeholder)
                if new_placeholder != placeholder:
                    widget.setPlaceholderText(new_placeholder)
        elif isinstance(widget, QtWidgets.QMenu):
            title = widget.title()
            new_title = _tr(title)
            if new_title != title:
                widget.setTitle(new_title)
            for action in widget.actions():
                translate_action(action)
        elif isinstance(widget, QtWidgets.QTableWidget):
            for col in range(widget.columnCount()):
                item = widget.horizontalHeaderItem(col)
                if item is not None:
                    text = item.text()
                    new_text = _tr(text)
                    if new_text != text:
                        item.setText(new_text)
        elif isinstance(widget, QtWidgets.QTreeWidget):
            header = widget.headerItem()
            if header is not None:
                for col in range(header.columnCount()):
                    text = header.text(col)
                    new_text = _tr(text)
                    if new_text != text:
                        header.setText(col, new_text)

    # 主窗口标题
    win.setWindowTitle(_tr(i18n.t("app.title", win.windowTitle())))

    # 菜单/动作
    for action in win.findChildren(QtGui.QAction):
        translate_action(action)

    # 所有控件
    for widget in win.findChildren(QtWidgets.QWidget):
        translate_widget(widget)
        if hasattr(widget, 'apply_language'):
            try:
                widget.apply_language()
            except Exception:
                traceback.print_exc()

    # 状态栏文本
    status = win.statusBar() if hasattr(win, "statusBar") else None
    if status is not None:
        msg = status.currentMessage()
        if msg:
            new_msg = _tr(msg)
            if new_msg != msg:
                status.showMessage(new_msg)

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
        _apply_language_to_ui(win)
    except Exception:
        traceback.print_exc()
