from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QRadioButton,
    QSpinBox,
)

from app.i18n import tr


class AddressTargetWidget(QGroupBox):
    """统一的 DALI 寻址选择组件。"""

    changed = Signal()

    def __init__(self, parent=None, title: str | None = None):
        super().__init__(title or tr("地址选择", "Address selection"), parent)

        self.rb_broadcast = QRadioButton(self)
        self.chk_unaddressed = QCheckBox(self)
        self.rb_short = QRadioButton(self)
        self.sb_short = QSpinBox(self)
        self.sb_short.setRange(0, 63)
        self.rb_group = QRadioButton(self)
        self.sb_group = QSpinBox(self)
        self.sb_group.setRange(0, 15)

        layout = QGridLayout(self)
        layout.addWidget(self.rb_broadcast, 0, 0)
        layout.addWidget(self.chk_unaddressed, 0, 1)
        layout.addWidget(self.rb_short, 1, 0)
        layout.addWidget(self.sb_short, 1, 1)
        layout.addWidget(self.rb_group, 2, 0)
        layout.addWidget(self.sb_group, 2, 1)

        self.rb_broadcast.setChecked(True)
        self.chk_unaddressed.setChecked(False)

        # 信号联动
        for widget in (
            self.rb_broadcast,
            self.chk_unaddressed,
            self.rb_short,
            self.rb_group,
        ):
            widget.toggled.connect(self._emit_changed)

        self.sb_short.valueChanged.connect(self._emit_changed)
        self.sb_group.valueChanged.connect(self._emit_changed)

        self.apply_language()

    # ------------------ 公共 API ------------------
    def mode(self) -> str:
        if self.rb_short.isChecked():
            return "short"
        if self.rb_group.isChecked():
            return "group"
        return "broadcast"

    def addr_value(self) -> int | None:
        m = self.mode()
        if m == "short":
            return int(self.sb_short.value())
        if m == "group":
            return int(self.sb_group.value())
        return None

    def unaddressed(self) -> bool:
        return bool(self.chk_unaddressed.isChecked()) if self.mode() == "broadcast" else False

    def set_mode(self, mode: str, value: int | None = None, unaddr: bool = False) -> None:
        mode = (mode or "broadcast").lower()
        if mode == "short":
            self.rb_short.setChecked(True)
            if value is not None:
                self.sb_short.setValue(int(value))
        elif mode == "group":
            self.rb_group.setChecked(True)
            if value is not None:
                self.sb_group.setValue(int(value))
        else:
            self.rb_broadcast.setChecked(True)
            self.chk_unaddressed.setChecked(bool(unaddr))
        self._emit_changed()

    # ------------------ 语言刷新 ------------------
    def apply_language(self) -> None:
        self.setTitle(tr("地址选择", "Address selection"))
        self.rb_broadcast.setText(tr("广播", "Broadcast"))
        self.chk_unaddressed.setText(tr("仅未寻址", "Not addressed only"))
        self.rb_short.setText(tr("短地址", "Short address"))
        self.rb_group.setText(tr("组地址", "Group address"))

    # ------------------ 内部 ------------------
    def _emit_changed(self, *_args) -> None:
        self.changed.emit()

