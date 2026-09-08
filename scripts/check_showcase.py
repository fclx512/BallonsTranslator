#!/usr/bin/env python3
"""展示台覆盖校验：ui/custom_widget 导出清单 vs 展示台登记名单。

防止「新增了封装控件但忘了在 scripts/style_showcase.py 里展示/登记」的
静默漂移（裸符号名 check_docs 查不到）。纯 AST 解析，不导入 Qt，
任意解释器可跑；verify.py 每次都会执行。

用法：
    python scripts/check_showcase.py
退出码：0 一致，1 存在漏登记 / 重复登记 / 陈旧登记。
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOWCASE = ROOT / "scripts" / "style_showcase.py"
INIT = ROOT / "ui" / "custom_widget" / "__init__.py"

# 展示行里的符号引用形如 ui/custom_widget/spinbox.py::NoArrowsSpinBox
SYMBOL_RE = re.compile(r"^ui/[\w/]+\.py::(\w+)$")


def _exports():
    """ui/custom_widget/__init__.py 里所有对外导出（相对导入 + 本文件定义）。"""
    tree = ast.parse(INIT.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            names.update(alias.name for alias in node.names)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _registered():
    """展示台里出现的符号名 + EXCLUDED 字典的键。"""
    tree = ast.parse(SHOWCASE.read_text(encoding="utf-8"))
    covered, excluded = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            match = SYMBOL_RE.match(node.value)
            if match:
                covered.add(match.group(1))
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "EXCLUDED":
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            excluded.add(key.value)
    return covered, excluded


def find_problems():
    exported = _exports()
    covered, excluded = _registered()
    problems = []
    for name in sorted(exported - covered - excluded):
        problems.append(
            f"未登记：{name} —— 既没有展示行，也不在 EXCLUDED 字典里"
        )
    for name in sorted(excluded & covered):
        problems.append(f"重复登记：{name} 同时在展示行和 EXCLUDED 里")
    for name in sorted(excluded - exported):
        problems.append(
            f"陈旧登记：EXCLUDED 里的 {name} 已不是 ui/custom_widget 的导出，请删除"
        )
    return problems


def main():
    problems = find_problems()
    if not problems:
        print("✅ showcase: 展示台覆盖与 ui/custom_widget 导出一致")
        return 0
    print("❌ showcase: 展示台登记与导出不一致")
    for problem in problems:
        print(f"  - {problem}")
    print("\n修复：在 scripts/style_showcase.py 的 _sections() 加展示行，"
          "或在 EXCLUDED 字典登记原因。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
