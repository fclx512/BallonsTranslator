"""Filter-effect pipeline smoke tests for the effects-stack renderer.

Locks the filter pipeline now owned by
``ui/text_engine/effects/renderer.TextEffectRenderer``:

- a stack containing an enabled ``FilterEffect`` renders without error and
  the completed surface stays in ``effect_renderer.background_pixmap``
- the filter actually changes the composited pixels (alpha-expanding
  ``gaussian_blur`` produces a different scene than the same stroke alone)
- ``_render_effect_surface`` resolves a Filter chain to a valid pixmap

Pixel comparisons render the scene to a fixed-size image so the filter's
alpha expansion (which grows effect padding and thus the surface rect)
does not break array-shape equality.
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


class TextBlkItemFilterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from qtpy.QtCore import QRectF
        from qtpy.QtGui import QColor, QImage, QPainter
        from qtpy.QtWidgets import QApplication, QGraphicsScene

        from ui.textitem import TextBlkItem
        from utils.text_effects import (
            FilterEffect,
            SolidPaint,
            StrokeEffect,
            TextEffectStack,
        )

        cls.QRectF = QRectF
        cls.QColor, cls.QImage, cls.QPainter = QColor, QImage, QPainter
        cls.QApplication, cls.QGraphicsScene = QApplication, QGraphicsScene
        cls.TextBlkItem = TextBlkItem
        cls.FilterEffect = FilterEffect
        cls.SolidPaint = SolidPaint
        cls.StrokeEffect = StrokeEffect
        cls.TextEffectStack = TextEffectStack
        cls.app = QApplication.instance() or QApplication([])
        cls.scene = QGraphicsScene()

    def setUp(self):
        self.scene.clear()

    def _new_item(self, effects):
        """Build a TextBlkItem whose canonical stack is ``effects``."""
        from utils.textblock import TextBlock

        blk = TextBlock(xyxy=[100, 100, 400, 220], translation="测试文字")
        blk._bounding_rect = [100, 100, 400, 220]
        blk.fontformat.font_size = 60
        blk.fontformat.frgb = [255, 255, 255]
        item = self.TextBlkItem(blk=blk, idx=0)
        self.scene.addItem(item)
        blk.fontformat.text_effects = self.TextEffectStack(
            effects=tuple(effects)
        )
        item.repaint_background()
        return item, blk

    def _scene_bytes(self, item):
        image = self.QImage(
            600, 400, self.QImage.Format.Format_ARGB32_Premultiplied
        )
        image.fill(self.QColor(255, 255, 255))
        painter = self.QPainter(image)
        try:
            self.scene.render(
                painter, target=self.QRectF(0, 0, 600, 400)
            )
        finally:
            painter.end()
        return bytes(image.constBits().asarray(image.sizeInBytes()))

    def test_filter_render_no_error_and_pixels_change(self):
        """A FilterEffect in the stack renders and changes the pixels."""
        stroke = self.StrokeEffect(
            width=0.1, paint=self.SolidPaint((255, 0, 0))
        )
        baseline_item, _ = self._new_item((stroke,))
        baseline = self._scene_bytes(baseline_item)

        blur = self.FilterEffect(
            "builtin:gaussian_blur", params={"radius": 3.0}
        )
        item, _ = self._new_item((stroke, blur))
        pm = item.effect_renderer.background_pixmap
        self.assertIsNotNone(pm, "filtered background_pixmap was not produced")
        self.assertFalse(pm.isNull())
        filtered = self._scene_bytes(item)
        self.assertNotEqual(
            baseline, filtered, "gaussian_blur did not change the pixels"
        )

    def test_in_glyph_filters_replace_native_foreground(self):
        """Noise/grain (in-glyph only) must visibly reach the scene.

        Regression for the completed-foreground contract: noise and grain
        only modify pixels inside the glyphs, so while the un-filtered
        native text pass still painted on top of the filter output they
        were perfectly erased ("滤镜没有效果") while halo filters like
        gaussian_blur stayed visible around the glyphs.  The native pass
        must be replaced whenever an enabled Filter owns the face.
        """
        stroke = self.StrokeEffect(
            width=0.1, paint=self.SolidPaint((255, 0, 0))
        )
        baseline_item, _ = self._new_item((stroke,))
        baseline = self._scene_bytes(baseline_item)

        for filter_id, params in (
            ("builtin:noise", {"amount": 1.0, "mode": "monochrome", "seed": 0}),
            ("builtin:grain", {"amount": 1.0, "size": 2.0, "seed": 0}),
        ):
            item, _ = self._new_item(
                (stroke, self.FilterEffect(filter_id, params=params))
            )
            filtered = self._scene_bytes(item)
            changed = sum(
                1
                for offset in range(0, len(baseline), 4)
                if baseline[offset:offset + 3]
                != filtered[offset:offset + 3]
            )
            self.assertGreater(
                changed,
                1000,
                f"{filter_id} changed only {changed} pixels; "
                "the un-filtered native face still covers its output",
            )

    def test_filter_effect_surface_produces_pixmap(self):
        """`_render_effect_surface` resolves a filter chain to a pixmap."""
        blur = self.FilterEffect(
            "builtin:gaussian_blur", params={"radius": 2.0}
        )
        item, _ = self._new_item((blur,))
        renderer = item.effect_renderer
        surface = renderer._render_effect_surface(
            renderer.boundingRect(), 1.0
        )
        self.assertIsNotNone(surface)
        self.assertFalse(surface.isNull())

    def test_filter_mixed_batch_with_stroke(self):
        """A filter below a generated layer alternates segments cleanly."""
        stroke = self.StrokeEffect(
            width=0.1, paint=self.SolidPaint((255, 0, 0))
        )
        blur = self.FilterEffect(
            "builtin:gaussian_blur", params={"radius": 2.0}
        )
        # Filter first (bottom), then stroke drawn above the filtered alpha.
        item, _ = self._new_item((blur, stroke))
        pm = item.effect_renderer.background_pixmap
        self.assertIsNotNone(pm)
        self.assertFalse(pm.isNull())

    def test_filter_edit_session_with_value_settable(self):
        """Filter card commits reach the stack via ``_with_value``.

        Regression: ``TextEffectEditSession._with_value`` fell through to
        ``raise ValueError('selected text effect type is unsupported')`` for
        ``FilterEffect``, so every filter-card edit and its enabled/visibility
        toggle was swallowed by ``commit_value`` and silently no-op'd (user
        report: filter card "功能项都不可交互/隐藏按钮无效").
        """
        from ui.text_engine.effects.edit_session import (
            TextEffectEditSession,
        )

        blur = self.FilterEffect(
            "builtin:gaussian_blur", params={"radius": 1.0}
        )
        stack = self.TextEffectStack(effects=(blur,))

        # Commit a parameter value (filter card emits 'param:<key>').
        after_param = TextEffectEditSession._with_value(
            stack, 0, "param:radius", 4.0
        )
        self.assertEqual(
            after_param.effects[0].params_dict()["radius"], 4.0
        )
        self.assertEqual(
            TextEffectEditSession._value_at(stack, 0, "param:radius"),
            1.0,
            "value_at must read the current filter param",
        )

        # Commit the enabled/visibility toggle ('enabled').
        after_enabled = TextEffectEditSession._with_value(
            stack, 0, "enabled", False
        )
        self.assertFalse(after_enabled.effects[0].enabled)
        self.assertIs(
            TextEffectEditSession._value_at(stack, 0, "enabled"), True
        )

        # Unknown fields still raise so typos are not silently accepted.
        with self.assertRaises(ValueError):
            TextEffectEditSession._with_value(
                stack, 0, "not_a_filter_field", 1
            )

    def test_filter_renders_completed_foreground(self):
        """A FilterEffect stack owns the face so the native original hides.

        Regression: ``_renders_completed_foreground`` omitted FilterEffect, so
        the renderer composited the filter surface and then painted the
        un-filtered original text on top of it (user report: the filter effect
        "没有将原样式隐藏，样式前面还有一个原样式挡着").
        """
        from utils.text_effects import TextEffectStack

        # Neutral stack → the host native text pass stays.
        neutral_item, _ = self._new_item(())
        self.assertFalse(
            neutral_item.effect_renderer._renders_completed_foreground()
        )

        # Enabled FilterEffect → the filter surface replaces the original face.
        blur = self.FilterEffect(
            "builtin:gaussian_blur", params={"radius": 3.0}
        )
        item, _ = self._new_item((blur,))
        self.assertTrue(item.effect_renderer._renders_completed_foreground())


if __name__ == "__main__":
    unittest.main()
