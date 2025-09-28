from __future__ import annotations

import math
from typing import Tuple

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPaintEvent
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider, QStylePainter


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp *value* into [minimum, maximum]."""
    return max(minimum, min(maximum, value))


def kelvin_to_rgb(kelvin: float) -> Tuple[int, int, int]:
    """Approximate XYZ-to-RGB conversion for a color temperature in Kelvin."""
    temp = _clamp(kelvin, 1000.0, 40000.0) / 100.0

    if temp <= 66:
        red = 255.0
        green = 99.4708 * math.log(temp) - 161.1196 if temp > 0 else 0.0
        blue = 0.0 if temp <= 19 else 138.5177 * math.log(temp - 10.0) - 305.0448
    else:
        red = 329.6987 * ((temp - 60.0) ** -0.1332047592)
        green = 288.1222 * ((temp - 60.0) ** -0.0755148492)
        blue = 255.0

    return (
        int(round(_clamp(red, 0.0, 255.0))),
        int(round(_clamp(green, 0.0, 255.0))),
        int(round(_clamp(blue, 0.0, 255.0))),
    )


class KelvinGradientSlider(QSlider):
    """Horizontal slider that renders a color-temperature gradient."""

    def __init__(self, kelvin_min: int, kelvin_max: int, parent=None, *, samples: int = 24):
        super().__init__(Qt.Horizontal, parent)
        self._gradient_samples = max(1, samples)
        self._groove_radius = 6
        self._kmin = kelvin_min
        self._kmax = kelvin_max
        super().setRange(kelvin_min, kelvin_max)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumHeight(36)

    # ---- QSlider overrides -------------------------------------------------
    def setRange(self, minimum: int, maximum: int) -> None:  # type: ignore[override]
        self._kmin = minimum
        self._kmax = maximum
        super().setRange(minimum, maximum)
        self.update()

    def setMinimum(self, minimum: int) -> None:  # type: ignore[override]
        self.setRange(minimum, self.maximum())

    def setMaximum(self, maximum: int) -> None:  # type: ignore[override]
        self.setRange(self.minimum(), maximum)

    # ---- painting ----------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: D401 (Qt override)
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        painter = QStylePainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        groove = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)
        groove = self._groove_rect(groove)

        if groove.isValid():
            gradient = QLinearGradient(groove.topLeft(), groove.topRight())
            span = max(1, self._kmax - self._kmin)
            for step in range(self._gradient_samples + 1):
                ratio = step / self._gradient_samples
                kelvin = self._kmin + span * ratio
                gradient.setColorAt(ratio, QColor(*kelvin_to_rgb(kelvin)))

            path = QPainterPath()
            path.addRoundedRect(groove, self._groove_radius, self._groove_radius)
            painter.fillPath(path, gradient)

            painter.setPen(QColor(0, 0, 0, 60))
            painter.drawPath(path)

        sub_controls = QStyle.SC_SliderHandle
        if self.tickPosition() != QSlider.NoTicks:
            sub_controls |= QStyle.SC_SliderTickmarks

        opt.subControls = sub_controls
        painter.drawComplexControl(QStyle.CC_Slider, opt)

    # ---- helpers -----------------------------------------------------------
    def _groove_rect(self, groove: QRect) -> QRect:
        """Shrink the style groove into a compact gradient bar."""
        if not groove.isValid():
            return groove

        groove = QRect(groove)
        groove.adjust(6, 0, -6, 0)
        target_height = min(18, groove.height())
        dy = max(0, (groove.height() - target_height) // 2)
        groove.adjust(0, dy, 0, -dy)
        return groove
