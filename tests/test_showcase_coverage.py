"""展示台覆盖校验：ui/custom_widget 的每个导出都必须登记到 style_showcase.py。

防止「新增封装控件但忘了展示/登记」的静默漂移（裸符号名 check_docs 查不到）。
逻辑在 scripts/check_showcase.py，verify.py 每次也会跑同一个脚本。
"""

import importlib.util
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_checker():
    path = os.path.join(REPO_ROOT, "scripts", "check_showcase.py")
    spec = importlib.util.spec_from_file_location("check_showcase", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestShowcaseCoverage(unittest.TestCase):
    def test_every_export_is_registered(self):
        problems = _load_checker().find_problems()
        self.assertEqual(
            problems,
            [],
            "展示台登记与 ui/custom_widget 导出不一致：\n" + "\n".join(problems),
        )


if __name__ == "__main__":
    unittest.main()
