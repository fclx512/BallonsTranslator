"""效果光栅策略：瓦片取整余量 + 随缩放分层的瓦片 tier。

对应上游 9b34135（满瓦片正好卡面积上限，任一轴 ceil() 就整块失败）与
e88c655 的收尾形态（raster 侧只保留余量 + tier 分层）。
"""

import math
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ui.text_engine.rendering.raster import (  # noqa: E402
    EFFECT_CACHE_MAX_DIMENSION,
    EFFECT_CACHE_MAX_PIXELS,
    EFFECT_TILE_MAX_EDGE,
    plan_effect_raster,
)


class EffectRasterPolicyTest(unittest.TestCase):
    def test_tile_edge_leaves_rounding_headroom(self):
        plan = plan_effect_raster(10000, 10000, 1.0)
        self.assertEqual(plan.mode, "tiles")
        expected = min(
            EFFECT_TILE_MAX_EDGE,
            EFFECT_CACHE_MAX_DIMENSION,
            int(math.sqrt(EFFECT_CACHE_MAX_PIXELS)) - 1,
        )
        self.assertEqual(plan.tile_edge, expected)

    def test_tile_tier_follows_requested_scale(self):
        self.assertEqual(plan_effect_raster(10000, 10000, 1.0).tier, 1.0)
        self.assertEqual(plan_effect_raster(10000, 10000, 0.5).tier, 0.5)
        self.assertEqual(plan_effect_raster(10000, 10000, 0.25).tier, 0.25)

    def test_small_surface_stays_full(self):
        plan = plan_effect_raster(100, 80, 2.0)
        self.assertEqual(plan.mode, "full")
        self.assertEqual(plan.tier, 2.0)


if __name__ == "__main__":
    unittest.main()
