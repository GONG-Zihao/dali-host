# app/experimental/panel_gateway_scan.py
from __future__ import annotations

from PySide6 import QtWidgets


class GatewayScanDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("扫描网关")
        self.resize(480, 360)
        layout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["ID", "IP", "状态"])
        layout.addWidget(self.table)
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        layout.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        form = QtWidgets.QFormLayout()
        self.edt_timeout = QtWidgets.QSpinBox()
        self.edt_timeout.setRange(1, 60)
        self.edt_timeout.setValue(5)
        self.chk_autoscan = QtWidgets.QCheckBox("扫描后自动搜灯")
        layout.insertLayout(0, form)
        form.addRow("超时(s)", self.edt_timeout)
        form.addRow("", self.chk_autoscan)

        self._dummy_fill()

    def _dummy_fill(self):
        # placeholder; real impl should probe network
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QtWidgets.QTableWidgetItem("GW-0001"))
        self.table.setItem(0, 1, QtWidgets.QTableWidgetItem("192.168.1.100"))
        self.table.setItem(0, 2, QtWidgets.QTableWidgetItem("在线"))

