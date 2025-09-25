# app/experimental/panel_addr_alloc.py
from __future__ import annotations

from PySide6 import QtWidgets, QtCore


class AddressAllocPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PanelAddrAlloc")
        self.setWindowTitle("地址分配策略")
        layout = QtWidgets.QVBoxLayout(self)
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(["二分搜索法", "随机冲突解析", "预分配映射"])
        layout.addWidget(self.combo)
        self.btn_run = QtWidgets.QPushButton("模拟执行")
        layout.addWidget(self.btn_run)
        self.out = QtWidgets.QPlainTextEdit()
        self.out.setReadOnly(True)
        layout.addWidget(self.out)
        self.btn_run.clicked.connect(self._simulate)

    def _simulate(self):
        idx = self.combo.currentIndex()
        msg = ["执行：二分搜索法", "执行：随机冲突解析", "执行：预分配映射"][idx]
        self.out.appendPlainText(msg)

