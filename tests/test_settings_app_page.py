"""Offscreen tests for the General → App page carrying the two ex-Misc options.

The App page absorbed what used to be a separate "Misc" staging page: the
Photoshop executable path (was Settings → Inpainter) and the workbench
confirmation toggle (was Settings → Translator).

Run from the repo root:
    ./ballontrans_pylibs_win/python.exe tests/test_settings_app_page.py
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

from qtpy.QtWidgets import QApplication  # noqa: E402

from utils.config import pcfg  # noqa: E402


class SettingsAppPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ui.configpanel import ConfigPanel

        cls.app = QApplication.instance() or QApplication([])
        cls.panel = ConfigPanel()

    def setUp(self):
        cfg = pcfg
        snapshot = (cfg.drawpanel.photoshop_path, cfg.workbench_confirm_costly)
        self.addCleanup(
            lambda: (
                setattr(pcfg.drawpanel, "photoshop_path", snapshot[0]),
                setattr(pcfg, "workbench_confirm_costly", snapshot[1]),
            )
        )

    def test_misc_page_is_gone(self):
        self.assertNotIn("misc", self.panel._nav_section_to_widget)
        self.assertFalse(hasattr(self.panel, "misc_block"))
        self.assertFalse(hasattr(self.panel, "label_misc"))

    def test_page_count_is_nine(self):
        # Modules (Models / Pipeline / LLM Profile) + General (Project /
        # Typesetting / Interface / Shortcuts / Quick Menus / App).
        self.assertEqual(self.panel.pageStack.count(), 9)
        self.assertEqual(len(self.panel._nav_section_to_widget), 9)

    def test_app_page_carries_both_options(self):
        self.assertTrue(hasattr(self.panel, "ps_path_edit"))
        self.assertTrue(hasattr(self.panel, "confirm_costly_checker"))

    def test_photoshop_path_writes_config(self):
        self.panel.ps_path_edit.setText(r"D:\Adobe\Photoshop.exe")
        self.panel.on_ps_path_changed()
        self.assertEqual(
            pcfg.drawpanel.photoshop_path, r"D:\Adobe\Photoshop.exe"
        )

    def test_workbench_toggle_writes_config(self):
        self.panel.confirm_costly_checker.setChecked(False)
        self.assertFalse(pcfg.workbench_confirm_costly)
        self.panel.confirm_costly_checker.setChecked(True)
        self.assertTrue(pcfg.workbench_confirm_costly)

    def test_pipeline_panels_no_longer_carry_them(self):
        self.assertFalse(hasattr(self.panel.inpaint_config_panel, "ps_path_edit"))
        self.assertFalse(
            hasattr(self.panel.trans_config_panel, "_confirm_costly_checker")
        )


if __name__ == "__main__":
    unittest.main()
