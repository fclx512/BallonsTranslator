"""Tests for the card-based LLM Profile settings page.

Runs offscreen. Writes are patched out so the real ``config/config.json`` is
never touched — ``setUp`` gives ``pcfg.module.model_profiles`` a controlled
value because ``import``-time config loading otherwise leaks the developer's
own profiles into the singleton (see docs/基础速查/经验教训.md).

Usage:
    ./ballontrans_pylibs_win/python.exe -m pytest tests/test_llm_profile_cards.py -v
    ./ballontrans_pylibs_win/python.exe tests/test_llm_profile_cards.py
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

from qtpy.QtWidgets import QApplication  # noqa: E402

_APP = None


def _ensure_app():
    global _APP
    _APP = QApplication.instance() or QApplication(
        sys.argv[:1] + ["--platform", "offscreen"]
    )
    return _APP


def _sample_profiles() -> list:
    """受控基线：直接用内置样例，避免 load_profiles 补回缺失的 builtin。"""
    from utils.profile_manager import SAMPLE_PROFILES

    return [dict(p) for p in SAMPLE_PROFILES]


class TestLLMProfileCards(unittest.TestCase):
    def setUp(self):
        _ensure_app()
        from utils.config import pcfg

        self._saved_raw = pcfg.module.model_profiles
        pcfg.module.model_profiles = json.dumps(_sample_profiles())
        # Never touch disk from these tests.
        self._save_patcher = mock.patch("ui.llm_profile_cards.save_all_profiles")
        self._save_patcher.start()

        from ui.llm_profile_cards import LLMProfileListWidget

        self.widget = LLMProfileListWidget()
        self.widget.resize(900, 700)
        self.widget.show()

    def tearDown(self):
        from utils.config import pcfg

        self.widget.hide()
        self.widget.deleteLater()
        self._save_patcher.stop()
        pcfg.module.model_profiles = self._saved_raw

    def _card(self, name: str):
        return next(c for c in self.widget._cards if c.profile["name"] == name)

    def test_card_count_matches_profiles(self):
        self.assertEqual(len(self.widget._cards), len(_sample_profiles()))
        self.assertEqual(self.widget._cards[0].profile["name"], "OpenAI")

    def test_cards_start_collapsed(self):
        self.assertTrue(all(not c.is_expanded() for c in self.widget._cards))

    def test_vision_badge_toggles_field_and_section(self):
        card = self._card("OpenAI")
        card.set_expanded(True)
        details = card._details
        self.assertTrue(details.section_widgets["vision"].isVisible())
        card._toggle_vision_support()
        self.assertFalse(card.profile["vision_support"])
        self.assertFalse(details.section_widgets["vision"].isVisible())
        # 文本分节恒显
        self.assertTrue(details.section_widgets["text"].isVisible())

    def test_image_badge_gates_section_and_actions(self):
        card = self._card("OpenAI")
        card.set_expanded(True)
        self.assertFalse(card._details.section_widgets["image"].isVisible())
        self.assertFalse(card._image_actions.isVisible())
        card._toggle_image_support()
        self.assertTrue(card.profile["image_support"])
        self.assertTrue(card._details.section_widgets["image"].isVisible())
        self.assertTrue(card._image_actions.isVisible())

    def test_detail_edit_writes_back_with_converted_type(self):
        card = self._card("OpenAI")
        card._apply_value("temperature", "0.75")
        self.assertIsInstance(card.profile["temperature"], float)
        self.assertAlmostEqual(card.profile["temperature"], 0.75)
        card._apply_value("requests_per_minute", "not-a-number")
        self.assertEqual(card.profile["requests_per_minute"], 20)
        card._apply_value("return_json_schema", True)
        self.assertTrue(card.profile["return_json_schema"])
        card._apply_value("api_host", "  https://trimmed.example/v1  ")
        self.assertEqual(card.profile["api_host"], "https://trimmed.example/v1")

    def test_reasoning_effort_default_maps_to_empty_string(self):
        from ui.llm_profile_cards import _REASONING_DEFAULT

        card = self._card("OpenAI")
        card._apply_value("reasoning_effort", "high")
        self.assertEqual(card.profile["reasoning_effort"], "high")
        card._apply_value("reasoning_effort", _REASONING_DEFAULT)
        self.assertEqual(card.profile["reasoning_effort"], "")

    def test_builtin_delete_disabled(self):
        self.assertFalse(self._card("DeepSeek")._delete_btn.isEnabled())
        self.assertTrue(self._card("OpenAI")._delete_btn.isEnabled())

    def test_hide_event_persists_and_notifies(self):
        received = []
        self.widget.profiles_changed.connect(lambda: received.append(1))
        self.widget.hide()
        self.assertEqual(len(received), 1)

    def test_add_generates_unique_name(self):
        self.widget._on_add()
        names = [c.profile["name"] for c in self.widget._cards]
        self.assertEqual(len(names), len(_sample_profiles()) + 1)
        self.assertEqual(len(set(names)), len(names))
        self.assertIn("New Profile", names)

    # ── 模型清单（摘要行下拉 + 手动增删 + Fetch 多选）──

    def test_model_selector_starts_with_current_model_only(self):
        card = self._card("OpenAI")
        selector = card._model_selectors["model"]
        # 不预置供应商模型表：只有当前值入列
        self.assertEqual(selector.options(), ["gpt-4o"])
        self.assertEqual(selector.current_text(), "gpt-4o")

    def test_model_selector_pick_writes_back_and_persists(self):
        card = self._card("OpenAI")
        received = []
        card.persist_requested.connect(lambda: received.append(1))
        card._on_model_options_changed("model", ["gpt-4o", "gpt-4.1"], "gpt-4.1")
        self.assertEqual(card.profile["model_options"], ["gpt-4o", "gpt-4.1"])
        self.assertEqual(card.profile["model"], "gpt-4.1")
        self.assertEqual(len(received), 1)

    def test_model_selector_manual_add_appends_option(self):
        card = self._card("OpenAI")
        selector = card._model_selectors["model"]
        selector.start_edit()
        selector.combo.setEditText("  gpt-4o-mini  ")
        selector._finish_edit()
        self.assertIn("gpt-4o-mini", card.profile["model_options"])
        self.assertEqual(card.profile["model"], "gpt-4o-mini")

    def test_model_selector_remove_current_selects_neighbour(self):
        card = self._card("OpenAI")
        card._on_model_options_changed(
            "model", ["gpt-4o", "gpt-4.1", "gpt-4o-mini"], "gpt-4.1"
        )
        selector = card._model_selectors["model"]
        selector._remove_current()
        self.assertEqual(card.profile["model_options"], ["gpt-4o", "gpt-4o-mini"])
        self.assertEqual(card.profile["model"], "gpt-4o-mini")

    def test_fetch_models_multi_select_adds_all(self):
        from qtpy.QtWidgets import QDialog

        card = self._card("OpenAI")
        seen = []

        class _FakeDialog:
            DialogCode = QDialog.DialogCode

            def __init__(self, parent, title, items, multi_select=False):
                seen.append((list(items), multi_select))
                self.selected_items = ["gpt-4o-mini", "gpt-4.1"]
                self.selected = self.selected_items[0]

        card._exec_dialog = lambda _dialog: QDialog.DialogCode.Accepted
        with mock.patch("ui.llm_profile_cards.FilterableListDialog", _FakeDialog):
            card._pick_model(["gpt-4o", "gpt-4o-mini", "gpt-4.1"], "model")
        self.assertTrue(seen[0][1], "Fetch 列表必须走多选")
        self.assertEqual(
            card.profile["model_options"],
            ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
        )
        self.assertEqual(card.profile["model"], "gpt-4o-mini")

    def test_image_model_row_follows_image_support(self):
        card = self._card("OpenAI")
        row = card._model_rows["image_model"]
        self.assertFalse(row.isVisible())
        card._toggle_image_support()
        self.assertTrue(row.isVisible())

    def test_model_combo_width_is_content_sized(self):
        from qtpy.QtWidgets import QSizePolicy
        from utils.shared import CONFIG_COMBOBOX_LONG

        card = self._card("OpenAI")
        combo = card._model_selectors["model"].combo
        # 不再横向拉伸撑满整行，宽度由内容（最长选项）决定并受分级上限约束。
        self.assertNotEqual(
            combo.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Expanding
        )
        self.assertLessEqual(combo.maximumWidth(), CONFIG_COMBOBOX_LONG)

    # ── 连接信息块（主机 / API Key / 图像端口）──

    def test_connection_block_holds_host_and_key(self):
        from ui.llm_profile_cards import (
            PROFILE_COMMON_PARAM_DEFS,
            PROFILE_SECTION_PARAM_DEFS,
        )

        common_keys = [key for key, _type in PROFILE_COMMON_PARAM_DEFS]
        image_keys = [key for key, _type in PROFILE_SECTION_PARAM_DEFS["image"]]
        # 三个连接字段不再出现在杂项参数 / 图像分节里。
        self.assertNotIn("api_host", common_keys)
        self.assertNotIn("api_key", common_keys)
        self.assertNotIn("image_base_url", image_keys)

        card = self._card("OpenAI")
        card.set_expanded(True)
        connection = card._details._connection
        self.assertEqual(
            connection.edit_for("api_host").text(), card.profile["api_host"]
        )
        self.assertEqual(
            connection.edit_for("api_key").text(), card.profile["api_key"]
        )

    def test_connection_block_edits_write_back(self):
        card = self._card("OpenAI")
        card.set_expanded(True)
        edit = card._details._connection.edit_for("api_host")
        edit.setText("https://relay.example/v1")
        self.assertEqual(card.profile["api_host"], "https://relay.example/v1")

    def test_image_endpoint_row_follows_image_support(self):
        card = self._card("OpenAI")
        card.set_expanded(True)
        row = card._details._connection._rows["image_base_url"]
        self.assertFalse(row.isVisible())
        card._toggle_image_support()
        self.assertTrue(row.isVisible())

    def test_show_reloads_external_profile_changes(self):
        from utils.profile_manager import (
            get_profiles_raw,
            load_profiles,
            set_profiles_raw,
        )

        self.widget.hide()
        profiles = load_profiles()
        profiles[0]["model"] = "externally-changed"
        # 模拟外部（画布 AI 修图模型栏）写盘后回到本页
        set_profiles_raw(json.dumps(profiles))
        self.assertNotEqual(get_profiles_raw(), self.widget._loaded_raw)
        self.widget.show()
        card = self._card(profiles[0]["name"])
        self.assertEqual(card.profile["model"], "externally-changed")


class TestProfileModelOptions(unittest.TestCase):
    """数据层：清单归一 / 记忆去重 / 多选对话框。"""

    def test_normalize_model_options_keeps_current_value(self):
        from utils.profile_manager import normalize_model_options

        profile = normalize_model_options({"model": " m1 ", "model_options": ["m1", ""]})
        self.assertEqual(profile["model_options"], ["m1"])
        self.assertEqual(profile["image_model_options"], [])

    def test_remember_model_option_dedupes(self):
        from utils.profile_manager import remember_model_option

        profile = {"model_options": ["a"]}
        remember_model_option(profile, "model", "b")
        remember_model_option(profile, "model", "b")
        remember_model_option(profile, "model", "  ")
        self.assertEqual(profile["model_options"], ["a", "b"])

    def test_filterable_dialog_multi_select(self):
        _ensure_app()
        from utils.profile_manager import FilterableListDialog

        dialog = FilterableListDialog(
            None, "t", ["a", "b", "c"], multi_select=True
        )
        dialog.list_widget.item(0).setSelected(True)
        dialog.list_widget.item(2).setSelected(True)
        dialog._accept_selection()
        self.assertEqual(dialog.selected_items, ["a", "c"])
        self.assertEqual(dialog.selected, "a")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestLLMProfileCards))
    suite.addTests(loader.loadTestsFromTestCase(TestProfileModelOptions))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
