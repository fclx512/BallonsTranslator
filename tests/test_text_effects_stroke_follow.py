"""Stroke auto-inverse behavior (2026-09-08 second feedback batch).

User decision: the old live following (font color change → stroke color
inverse) is replaced by a one-shot detection when a stroke is added.
``TextEffectEditSession.add_effect('stroke')`` seeds the paint from the
current text color; afterwards the stroke color is a manual value and
``TextBlkItem.setFontColor`` no longer rewrites it.

Run from the repo root:
    ./ballontrans_pylibs_win/python.exe -m pytest tests/test_text_effects_stroke_follow.py
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


class StrokeAutoInverseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from qtpy.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from utils.config import pcfg

        self._previous = pcfg.stroke_auto_follow
        pcfg.stroke_auto_follow = True

    def tearDown(self):
        from utils.config import pcfg

        pcfg.stroke_auto_follow = self._previous

    def _session(self, foreground):
        from ui.text_engine.effects.edit_session import TextEffectEditSession
        from utils.fontformat import FontFormat

        host = type('EffectHost', (), {})()
        host.global_format = FontFormat()
        host.global_format.frgb = list(foreground)
        host.update_text_style_label = lambda: None
        return host, TextEffectEditSession(host)

    def test_add_stroke_seeds_inverse_of_text_color(self):
        from utils.text_effects import primary_stroke

        host, session = self._session((255, 255, 255))
        self.assertTrue(session.add_effect('stroke'))
        stroke = primary_stroke(host.global_format.text_effects)
        self.assertEqual(tuple(stroke.paint.color), (0, 0, 0))
        self.assertTrue(host.global_format.stroke_color_custom)

    def test_add_stroke_seeds_inverse_for_dark_text(self):
        from utils.text_effects import primary_stroke

        host, session = self._session((10, 20, 30))
        session.add_effect('stroke')
        stroke = primary_stroke(host.global_format.text_effects)
        self.assertEqual(tuple(stroke.paint.color), (245, 235, 225))

    def test_add_stroke_keeps_default_when_switch_off(self):
        from utils.config import pcfg
        from utils.text_effects import primary_stroke

        pcfg.stroke_auto_follow = False
        host, session = self._session((255, 255, 255))
        session.add_effect('stroke')
        stroke = primary_stroke(host.global_format.text_effects)
        self.assertEqual(tuple(stroke.paint.color), (0, 0, 0))

    def test_font_color_change_keeps_manual_stroke_color(self):
        """改字色不再实时反色：已有描边保持手动值。"""
        from ui.textitem import TextBlkItem
        from utils.text_effects import (
            SolidPaint,
            StrokeEffect,
            TextEffectStack,
            primary_stroke,
        )
        from utils.textblock import TextBlock

        blk = TextBlock(xyxy=[100, 100, 400, 220], translation="测试文字")
        blk._bounding_rect = [100, 100, 400, 220]
        blk.fontformat.font_size = 60
        blk.fontformat.frgb = [255, 255, 255]
        blk.fontformat.text_effects = TextEffectStack(
            effects=(
                StrokeEffect(width=0.2, paint=SolidPaint((10, 20, 30))),
            )
        )
        item = TextBlkItem(blk=blk, idx=0)
        item.setFontColor((255, 255, 255))
        stroke = primary_stroke(blk.fontformat.text_effects)
        self.assertEqual(tuple(stroke.paint.color), (10, 20, 30))


if __name__ == '__main__':
    unittest.main()
