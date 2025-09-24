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
