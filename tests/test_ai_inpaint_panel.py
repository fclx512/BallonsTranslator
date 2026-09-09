"""AI 修图面板：生图模型栏（可编辑，写回 profile）+ 比例支持表。

Runs offscreen. ``setUp`` gives ``pcfg.module.model_profiles`` a controlled
value and patches ``save_config`` so the developer's real ``config/config.json``
is never written (see docs/基础速查/经验教训.md).

Usage:
    ./ballontrans_pylibs_win/python.exe -m pytest tests/test_ai_inpaint_panel.py -v
    ./ballontrans_pylibs_win/python.exe tests/test_ai_inpaint_panel.py
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qtpy.QtWidgets import QApplication, QLabel  # noqa: E402

_APP = None


def _ensure_app():
    global _APP
    _APP = QApplication.instance() or QApplication(
        sys.argv[:1] + ["--platform", "offscreen"]
    )
    return _APP


IMAGE_PROFILE = {
    "name": "Image Relay",
    "builtin": False,
    "vision_support": False,
    "api_host": "https://relay.example/v1",
    "api_key": "sk-test",
    "model": "",
    "model_options": [],
    "temperature": 0.1,
    "top_p": 1.0,
    "max_tokens": "",
    "proxy": "",
    "requests_per_minute": 20,
    "delay": 0.3,
    "reasoning_effort": "",
    "return_json_schema": False,
    "system_prompt": "",
    "ocr_prompt": "",
    "ocr_system_prompt": "",
    "ocr_detail_level": "auto",
    "ocr_max_response_tokens": 4096,
    "image_support": True,
    "image_base_url": "https://relay.example/v1/images",
    "image_model": "gpt-image-2",
    "image_model_options": ["gpt-image-2", "nano-banana-2"],
    "image_prompt": "",
}


class AIImageModelRowTest(unittest.TestCase):
    def setUp(self):
        app = _ensure_app()
        from ui.misc import parse_stylesheet
        from utils.config import pcfg

        # 生产环境的字号来自 stylesheet；面板最小宽依赖字体度量，这里照实应用。
        self._old_qss = app.styleSheet()
        app.setStyleSheet(parse_stylesheet())

        self._saved_raw = pcfg.module.model_profiles
        pcfg.module.model_profiles = json.dumps([dict(IMAGE_PROFILE)])
        self._save_patcher = mock.patch("utils.profile_manager.save_config")
        self._save_patcher.start()

        from ui.drawingpanel import AIConfigPanel

        self.panel = AIConfigPanel()
        self.panel.refresh_profile_options()

    def tearDown(self):
        from utils.config import pcfg

        self._save_patcher.stop()
        pcfg.module.model_profiles = self._saved_raw
        _ensure_app().setStyleSheet(self._old_qss)

    def test_model_combo_lists_profile_options(self):
        combo = self.panel.image_model_combo
        self.assertEqual(
            [combo.itemText(i) for i in range(combo.count())],
            ["gpt-image-2", "nano-banana-2"],
        )
        self.assertEqual(combo.currentText(), "gpt-image-2")
        self.assertTrue(combo.isEditable(), "中转站需手动输入模型名")

    def test_manual_model_input_persists_to_profile(self):
        from utils.profile_manager import find_profile

        self.panel.image_model_combo.setCurrentText("relay-image-x")
        self.panel._commit_image_model()
        profile = find_profile("Image Relay")
        self.assertEqual(profile["image_model"], "relay-image-x")
        self.assertIn("relay-image-x", profile["image_model_options"])

    def test_picking_from_list_persists_to_profile(self):
        from utils.profile_manager import find_profile

        self.panel.image_model_combo.setCurrentText("nano-banana-2")
        self.panel._commit_image_model()
        self.assertEqual(
            find_profile("Image Relay")["image_model"], "nano-banana-2"
        )

    def test_aspect_table_lists_models_and_ratios(self):
        labels = [
            label.text()
            for label in self.panel.crop_controls.findChildren(QLabel)
            if label.objectName() == "InpaintAspectTableCell"
        ]
        self.assertIn("gpt-image-2", labels)
        self.assertIn("Nano Banana", labels)
        self.assertIn("1:1 · 3:2 · 2:3", labels)
        self.assertIn("1:1 · 16:9 · 9:16 · 4:3 · 3:4", labels)

    def test_ratio_cells_wrap_instead_of_widening_the_panel(self):
        cells = [
            label
            for label in self.panel.crop_controls.findChildren(QLabel)
            if label.objectName() == "InpaintAspectTableCell"
        ]
        ratio_cells = [c for c in cells if "16:9" in c.text()]
        self.assertTrue(ratio_cells)
        for cell in ratio_cells:
            self.assertTrue(cell.wordWrap())

    def test_panel_min_width_fits_right_panel(self):
        # 右栏固定 360px，减去工具窄栏后可用约 326px；面板最小宽必须放得下，
        # 否则会被横向裁掉（比例提示被裁的根因）。
        self.assertLessEqual(self.panel.minimumSizeHint().width(), 326)

    def test_thickness_slider_aligns_with_combo_column(self):
        # 加精确输入框后滑条起点仍须与同栏下拉框同列（右栏对齐约定）。
        from qtpy.QtCore import QPoint
        from qtpy.QtWidgets import QVBoxLayout, QWidget

        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.panel)
        host.resize(326, 600)
        host.show()
        _ensure_app().processEvents()
        combo_x = self.panel.profile_combo.mapTo(self.panel, QPoint(0, 0)).x()
        slider_x = self.panel.thicknessSlider.mapTo(self.panel, QPoint(0, 0)).x()
        self.assertEqual(slider_x, combo_x)

    def test_repair_panel_buttons_get_horizontal_padding(self):
        # 全局 QPushButton 无内边距，中文两字按钮会紧贴边框；内边距来自
        # stylesheet 的 `DrawingPanel QPushButton` 规则。真实 DrawingPanel
        # 构造需要 Canvas，这里用同 class 名的容器承载，并校验类名一致。
        from qtpy.QtWidgets import QVBoxLayout, QWidget

        from ui.drawingpanel import DrawingPanel

        self.assertEqual(
            DrawingPanel.staticMetaObject.className(), "DrawingPanel"
        )
        host = type("DrawingPanel", (QWidget,), {})()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.panel)
        self.panel.crop_controls.set_llm_active(True)
        host.resize(326, 600)
        host.show()
        _ensure_app().processEvents()
        for button in (
            self.panel.crop_controls.inpaint_btn,
            self.panel.crop_controls.clear_mask_btn,
        ):
            slack = (
                button.width()
                - button.fontMetrics().horizontalAdvance(button.text())
            )
            self.assertGreaterEqual(slack, 16, button.text())


if __name__ == "__main__":
    unittest.main()
