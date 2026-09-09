"""画笔粗细：非线性滑块映射 + 精确像素输入框（上游 5acc4f4 / 2ecd5f7 移植）。"""

import math
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qtpy.QtWidgets import QApplication  # noqa: E402

_APP = None


def _ensure_app():
    global _APP
    _APP = QApplication.instance() or QApplication(
        sys.argv[:1] + ["--platform", "offscreen"]
    )
    return _APP


class BrushThicknessTest(unittest.TestCase):
    def setUp(self):
        _ensure_app()

    def test_slider_positions_are_logarithmic_but_values_are_exact(self):
        from ui.drawingpanel import (
            MAX_PEN_SIZE,
            MIN_PEN_SIZE,
            _BrushThicknessSlider,
        )

        slider = _BrushThicknessSlider()
        slider.setRange(MIN_PEN_SIZE, MAX_PEN_SIZE)
        slider.setValue(MIN_PEN_SIZE)
        self.assertAlmostEqual(slider._value_to_position_ratio(), 0.0)
        slider.setValue(MAX_PEN_SIZE)
        self.assertAlmostEqual(slider._value_to_position_ratio(), 1.0)
        # 轨道中点对应几何中点，而不是算术中点——小笔头才有可点区间。
        self.assertEqual(
            slider._position_ratio_to_value(0.5),
            round(MIN_PEN_SIZE * (MAX_PEN_SIZE / MIN_PEN_SIZE) ** 0.5),
        )
        self.assertLess(
            slider._position_ratio_to_value(0.5), MAX_PEN_SIZE / 2
        )
        # 值本身仍是精确像素，不因映射被改写。
        slider.setValue(37)
        self.assertEqual(slider.value(), 37)

    def test_base_slider_stays_linear(self):
        from ui.custom_widget import PaintQSlider

        slider = PaintQSlider()
        slider.setRange(0, 100)
        slider.setValue(25)
        self.assertAlmostEqual(slider._value_to_position_ratio(), 0.25)
        self.assertEqual(slider._position_ratio_to_value(0.25), 25)

    def test_thickness_control_exposes_exact_pixel_spinbox(self):
        from ui.drawingpanel import (
            MAX_PEN_SIZE,
            MIN_PEN_SIZE,
            THICKNESS_SPIN_WIDTH,
            TOOL_LABEL_WIDTH,
            _create_thickness_control,
        )

        slider, spinbox, layout = _create_thickness_control(None, "Thickness")
        self.assertEqual(slider.value(), spinbox.value())
        self.assertEqual(spinbox.minimum(), MIN_PEN_SIZE)
        self.assertEqual(spinbox.maximum(), MAX_PEN_SIZE)
        # 无单位后缀：右栏里 "20 px" 会被裁成 "20 p"。
        self.assertEqual(spinbox.suffix(), "")
        self.assertEqual(spinbox.width(), THICKNESS_SPIN_WIDTH)
        # 数值框落在标签列内，滑条独占其余宽度（不挤占滑条）。
        self.assertEqual(layout.count(), 2)
        label_cell = layout.itemAt(0).widget()
        self.assertEqual(label_cell.width(), TOOL_LABEL_WIDTH)
        self.assertEqual(layout.itemAt(1).widget(), slider)
        self.assertIn(spinbox, label_cell.findChildren(type(spinbox)))


if __name__ == "__main__":
    unittest.main()
