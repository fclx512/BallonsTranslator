"""Offscreen tests for the merged pipeline settings page.

The four stage pages (Text Detection / OCR / Inpaint / Translator) were
merged into one nav entry with an in-page tab switch; each tab shows a
read-only engine label instead of the module selector, because the engine is
picked in the bottom bar.

Run from the repo root:
    ./ballontrans_pylibs_win/python.exe tests/test_pipeline_page_merge.py
"""

import os
import os.path as osp
import sys
import unittest

APP_ROOT = osp.dirname(osp.dirname(osp.abspath(__file__)))
sys.path.insert(0, APP_ROOT)
os.chdir(APP_ROOT)
os.environ["QT_API"] = "pyqt6"
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from qtpy.QtWidgets import QApplication, QPushButton  # noqa: E402


class PipelinePageMergeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ui.configpanel import ConfigPanel

        cls.app = QApplication.instance() or QApplication([])
        cls.panel = ConfigPanel()

    def _stage_panels(self):
        return (
            self.panel.detect_config_panel,
            self.panel.ocr_config_panel,
            self.panel.inpaint_config_panel,
            self.panel.trans_config_panel,
        )

    def test_nav_collapses_pipeline_stages(self):
        keys = self.panel._nav_section_to_widget
        self.assertIn("pipeline", keys)
        self.assertIs(keys["pipeline"], self.panel.pipeline_page)
        for gone in ("detect", "ocr", "inpaint", "trans"):
            self.assertNotIn(gone, keys)

    def test_four_stage_tabs(self):
        bar = self.panel.pipeline_tab_bar
        self.assertEqual(bar.count(), 4)
        self.assertEqual(
            [bar.tabText(i) for i in range(bar.count())],
            ["Text Detection", "OCR", "Inpaint", "Translator"],
        )
        self.assertEqual(self.panel.pipeline_stack.count(), 4)

    def test_engine_label_replaces_module_selector(self):
        for panel in self._stage_panels():
            self.assertTrue(panel.module_label.isHidden())
            self.assertTrue(panel.module_combobox.isHidden())
            self.assertFalse(panel.engine_label.isHidden())
            self.assertEqual(panel.p_layout.indexOf(panel.engine_label), 0)

    def test_engine_label_follows_module_combobox(self):
        panel = self.panel.detect_config_panel
        panel.module_combobox.addItem("ysgyolo")
        panel.module_combobox.setCurrentText("ysgyolo")
        self.assertEqual(panel.engine_label.text(), "Engine: ysgyolo")

    def test_module_combobox_stays_alive_for_the_bottom_bar(self):
        """The merged page must not drop the combobox: the bottom bar, the
        module manager and the canvas inpaint tool panel all drive it."""
        for panel in self._stage_panels():
            self.assertIsNotNone(panel.module_combobox)
            self.assertTrue(hasattr(panel, "paramwidget_edited"))

    def test_focus_switches_stage_tab(self):
        cases = (
            (self.panel.focusOnDetect, self.panel.PIPELINE_STAGE_DETECT),
            (self.panel.focusOnOCR, self.panel.PIPELINE_STAGE_OCR),
            (self.panel.focusOnInpaint, self.panel.PIPELINE_STAGE_INPAINT),
            (self.panel.focusOnTranslator, self.panel.PIPELINE_STAGE_TRANSLATOR),
        )
        for focus, expected in cases:
            focus()
            self.assertEqual(self.panel.pipeline_tab_bar.currentIndex(), expected)
            self.assertEqual(self.panel.pipeline_stack.currentIndex(), expected)

    def test_each_tab_has_a_note_button(self):
        for panel in self._stage_panels():
            texts = [
                panel.p_layout.itemAt(i).widget().text()
                for i in range(panel.p_layout.count())
                if isinstance(panel.p_layout.itemAt(i).widget(), QPushButton)
            ]
            self.assertIn("?", texts)

    def test_inpaint_panel_no_longer_shuttles_its_combobox(self):
        """The old show/hide hack moved the selector in and out of p_layout;
        the canvas tool panel now owns that widget, so it must stay gone."""
        from ui.module_parse_widgets import InpaintConfigPanel

        self.assertNotIn("showEvent", InpaintConfigPanel.__dict__)
        self.assertNotIn("hideEvent", InpaintConfigPanel.__dict__)


if __name__ == "__main__":
    unittest.main()
