"""
Shared profile data layer for LLM API configurations.

Profiles are stored as a JSON string in pcfg.module.model_profiles.
The translator, LLM OCR and online inpainter modules all read from this
shared pool.

This module holds the model / persistence / network-probe helpers only; the
settings-page UI lives in ``ui/llm_profile_cards.py``.
"""

import json
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse

import httpx
from qtpy.QtCore import QThread, Signal
from qtpy.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from ui.custom_widget import ConfigLineEdit

from .config import pcfg, save_config
from .logger import logger as LOGGER

# ── Default values ──────────────────────────────────────────────────

DEFAULT_OCR_PROMPT = (
    "Perform OCR on the provided manga image snippet. The language is **{language}**.\n"
    "Recognize all text, including handwritten sound effects (SFX).\n"
    "**CRITICAL INSTRUCTION:** If you see jumbled characters, it is likely vertical text "
    "that was read horizontally. First, mentally reconstruct the correct vertical text.\n"
    "**OUTPUT FORMATTING:** All recognized text from the image must be consolidated "
    "into a **single, continuous horizontal line**. Do not use newlines.\n"
    "Your final output must be ONLY the recognized text. No explanations."
)
DEFAULT_OCR_SYSTEM_PROMPT = (
    "You are a specialized OCR engine for manga and comics. "
    "Your primary function is to accurately extract and consolidate all recognized text "
    "from an image into a **single, continuous horizontal line**. "
    "You must return only the raw, recognized text. "
    "You do not interpret, translate, or explain the content. "
    "You are designed to intelligently handle common OCR errors, such as "
    "reconstructing jumbled characters that result from misreading vertical text."
)
DEFAULT_INPAINT_PROMPT = (
    "Clean up this comic or manga image for further scanlation. Remove all visible text "
    "elements, including speech bubble lettering, captions, sound effects, signs, labels "
    "and text-like watermarks. When text is removed, reconstruct the artwork that was "
    "hidden behind it by sampling the surrounding pixels and extending them into the gap "
    "so it looks as if nothing was ever there: continue the screentone, hatching, "
    "gradients, shading, panel borders and structural lines (speed lines, scan lines, "
    "cross-hatching) with consistent spacing, angle, density, colour and brightness. Do "
    "not leave a flat solid colour, a blank white gap, or a coloured smear where the text "
    "was. Keep all other non-text artwork intact: characters, faces, line art, "
    "backgrounds, speech bubbles, panel borders, lighting, colours, texture and "
    "composition. Do not translate, redraw with new text, add captions, or explain the "
    "edit. Return only the cleaned image."
)

SAMPLE_PROFILES = [
    {
        "name": "OpenAI",
        "builtin": False,
        "vision_support": True,
        "api_host": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o",
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
        "ocr_prompt": DEFAULT_OCR_PROMPT,
        "ocr_system_prompt": DEFAULT_OCR_SYSTEM_PROMPT,
        "ocr_detail_level": "auto",
        "ocr_max_response_tokens": 4096,
        "image_support": False,
        "image_base_url": "",
        "image_model": "",
        "image_model_options": [],
        "image_prompt": DEFAULT_INPAINT_PROMPT,
    },
    {
        "name": "OpenRouter",
        "builtin": False,
        "vision_support": True,
        "api_host": "https://openrouter.ai/api/v1",
        "api_key": "",
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
        "ocr_prompt": DEFAULT_OCR_PROMPT,
        "ocr_system_prompt": DEFAULT_OCR_SYSTEM_PROMPT,
        "ocr_detail_level": "auto",
        "ocr_max_response_tokens": 4096,
        "image_support": False,
        "image_base_url": "",
        "image_model": "",
        "image_model_options": [],
        "image_prompt": DEFAULT_INPAINT_PROMPT,
    },
    {
        "name": "DeepSeek",
        "builtin": True,
        "vision_support": False,
        "api_host": "https://api.deepseek.com/v1",
        "api_key": "",
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
        "ocr_prompt": DEFAULT_OCR_PROMPT,
        "ocr_system_prompt": DEFAULT_OCR_SYSTEM_PROMPT,
        "ocr_detail_level": "auto",
        "ocr_max_response_tokens": 4096,
        "image_support": False,
        "image_base_url": "",
        "image_model": "",
        "image_model_options": [],
        "image_prompt": DEFAULT_INPAINT_PROMPT,
    },
    {
        "name": "LM Studio",
        "builtin": True,
        "vision_support": True,
        "api_host": "http://localhost:1234/v1",
        "api_key": "dummy-key",
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
        "ocr_prompt": DEFAULT_OCR_PROMPT,
        "ocr_system_prompt": DEFAULT_OCR_SYSTEM_PROMPT,
        "ocr_detail_level": "auto",
        "ocr_max_response_tokens": 4096,
        "image_support": False,
        "image_base_url": "",
        "image_model": "",
        "image_model_options": [],
        "image_prompt": DEFAULT_INPAINT_PROMPT,
    },
    {
        "name": "Ollama",
        "builtin": True,
        "vision_support": True,
        "api_host": "http://localhost:11434/v1",
        "api_key": "dummy-key",
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
        "ocr_prompt": DEFAULT_OCR_PROMPT,
        "ocr_system_prompt": DEFAULT_OCR_SYSTEM_PROMPT,
        "ocr_detail_level": "auto",
        "ocr_max_response_tokens": 4096,
        "image_support": False,
        "image_base_url": "",
        "image_model": "",
        "image_model_options": [],
        "image_prompt": DEFAULT_INPAINT_PROMPT,
    },
]


# ── Profile Manager ─────────────────────────────────────────────────

PROFILE_FIELDS = [
    "name",
    "builtin",
    "vision_support",
    "api_host",
    "api_key",
    "model",
    "model_options",
    "temperature",
    "top_p",
    "max_tokens",
    "proxy",
    "requests_per_minute",
    "delay",
    "reasoning_effort",
    "return_json_schema",
    "system_prompt",
    "ocr_prompt",
    "ocr_system_prompt",
    "ocr_detail_level",
    "ocr_max_response_tokens",
    "image_support",
    "image_base_url",
    "image_model",
    "image_model_options",
    "image_prompt",
]


def migrate_old_profiles():
    """Migrate profiles from translator's _profiles_storage to model_profiles."""
    if pcfg.module.model_profiles:
        return  # Already have profiles in the new location
    old_storage = pcfg.module.translator_params.get("LLM_API_Translator", {})
    raw = old_storage.get("_profiles_storage", "")
    if isinstance(raw, dict):
        raw = raw.get("value", "")
    if not raw:
        return
    try:
        old_profiles = json.loads(raw)
        if not isinstance(old_profiles, list):
            return
        # Convert old format to new: add missing fields
        migrated = []
        for p in old_profiles:
            entry = dict(SAMPLE_PROFILES[0])  # start with defaults
            entry.update(p)  # overlay saved values
            # Default vision_support to False for migrated profiles — user must opt in
            entry["vision_support"] = p.get("vision_support", False)
            # Ensure OCR fields exist with defaults
            entry.setdefault("ocr_prompt", DEFAULT_OCR_PROMPT)
            entry.setdefault("ocr_system_prompt", DEFAULT_OCR_SYSTEM_PROMPT)
            entry.setdefault("ocr_detail_level", "auto")
            entry.setdefault("ocr_max_response_tokens", 4096)
            entry.setdefault("proxy", "")
            entry.setdefault("requests_per_minute", 20)
            entry.setdefault("delay", 0.3)
            migrated.append(entry)
        pcfg.module.model_profiles = json.dumps(migrated, ensure_ascii=False)
        # Clean up old storage
        old_storage.pop("_profiles_storage", None)
        LOGGER.info(
            f"Migrated {len(migrated)} profiles from translator storage to model_profiles."
        )
    except (json.JSONDecodeError, TypeError, Exception) as e:
        LOGGER.warning(f"Failed to migrate old profiles: {e}")


def get_profiles_raw() -> str:
    return pcfg.module.model_profiles or ""


def set_profiles_raw(raw: str):
    pcfg.module.model_profiles = raw


def load_profiles() -> List[Dict]:
    """Deserialize profiles from config. Falls back to SAMPLE_PROFILES if empty."""
    raw = get_profiles_raw()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                _merge_builtin_defaults(data)
                return [
                    normalize_model_options(p)
                    for p in data
                    if isinstance(p, dict)
                ]
        except (json.JSONDecodeError, TypeError):
            pass
    profiles = [normalize_model_options(dict(p)) for p in SAMPLE_PROFILES]
    _save_profiles(profiles)
    return profiles


# (清单字段, 当前选中值字段)
_MODEL_OPTION_FIELDS = (
    ("model_options", "model"),
    ("image_model_options", "image_model"),
)


def normalize_model_options(profile: Dict) -> Dict:
    """规整单个 profile 的模型清单，并保证当前选中的模型一定在清单里。

    清单**不预置任何供应商模型名**：只由 Fetch Models 或手动添加产生。
    但当前值永远入列，否则摘要行下拉框会显示为空。
    """
    for options_key, value_key in _MODEL_OPTION_FIELDS:
        raw = profile.get(options_key)
        options: List[str] = []
        if isinstance(raw, list):
            for option in raw:
                text = str(option or "").strip()
                if text and text not in options:
                    options.append(text)
        current = str(profile.get(value_key, "") or "").strip()
        if current and current not in options:
            options.append(current)
        profile[options_key] = options
    return profile


def remember_model_option(profile: Dict, key: str, name: str) -> None:
    """把 ``name`` 记进 ``key``（``model`` / ``image_model``）对应的清单。"""
    text = str(name or "").strip()
    if not text:
        return
    options_key = {
        value_key: options_key for options_key, value_key in _MODEL_OPTION_FIELDS
    }.get(key)
    if options_key is None:
        return
    options = profile.get(options_key)
    if not isinstance(options, list):
        options = []
    if text not in options:
        options.append(text)
    profile[options_key] = options


def _merge_builtin_defaults(profiles: List[Dict]):
    """Ensure all SAMPLE_PROFILES builtins exist with current default fields."""
    default_map = {p["name"]: p for p in SAMPLE_PROFILES if p.get("builtin")}
    existing_names = {p.get("name") for p in profiles}
    for name, defaults in default_map.items():
        if name not in existing_names:
            profiles.append(dict(defaults))
    for profile in profiles:
        if profile.get("builtin") and profile["name"] in default_map:
            defaults = default_map[profile["name"]]
            for key, val in defaults.items():
                if key not in profile:
                    profile[key] = val


def _save_profiles(profiles: List[Dict]):
    set_profiles_raw(json.dumps(profiles, ensure_ascii=False))


def get_profile_names() -> List[str]:
    return [p.get("name", "") for p in load_profiles() if p.get("name")]


def find_profile(name: str) -> Optional[Dict]:
    for p in load_profiles():
        if p.get("name") == name:
            return p
    return None


def get_vision_profiles() -> List[Dict]:
    """Return profiles that have vision_support enabled."""
    return [p for p in load_profiles() if p.get("vision_support", False)]


def get_vision_profile_names() -> List[str]:
    return [p.get("name", "") for p in get_vision_profiles() if p.get("name")]


def get_image_profiles() -> List[Dict]:
    """Return profiles that have image inpainting enabled.

    Inpainting is gated by the image_support flag on each profile (managed in
    Model Management), so a profile that only does text/OCR does not appear in
    the online inpainter's profile selector.
    """
    return [p for p in load_profiles() if p.get("image_support", False)]


def get_image_profile_names() -> List[str]:
    return [p.get("name", "") for p in get_image_profiles() if p.get("name")]


# ── Image endpoint helpers (Test / Fetch Models for image inpainting) ──

def _is_gemini_host(base_url: str) -> bool:
    return urlparse(base_url).netloc.lower() == "generativelanguage.googleapis.com"


def _is_openrouter_host(base_url: str) -> bool:
    host = urlparse(base_url).netloc.lower()
    return host == "openrouter.ai" or host.endswith(".openrouter.ai")


def _join_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    endpoint = "/" + path.strip("/")
    return f"{base}{endpoint}"


def _image_models_url(image_base_url: str) -> str:
    """Derive the provider's model-list endpoint from an image endpoint.

    Gemini exposes ``/models`` under its versioned root; a pasted
    ``:generateContent`` or ``/models/<model>`` tail is stripped back to it.
    OpenAI-compatible / OpenRouter image endpoints usually sit at
    ``<api_root>/images/<action>``, so the list lives at ``<api_root>/models``.
    """
    base = image_base_url.rstrip("/")
    if _is_gemini_host(base):
        parsed = urlparse(base)
        path = parsed.path.rstrip("/")
        if ":generateContent" in path:
            path = path.split(":generateContent")[0].rstrip("/")
        if "/models" in path:
            path = path.split("/models")[0].rstrip("/")
        root = urlunparse(
            parsed._replace(path=path, params="", query="", fragment="")
        ).rstrip("/")
        return _join_url(root, "/models")
    fallback = base
    path = urlparse(base).path.rstrip("/")
    for action in ("/images/edits", "/images"):
        if path.endswith(action):
            fallback = base[: len(base) - len(action)]
            break
    return _join_url(fallback, "/models")


def _image_headers(base_url: str, api_key: str) -> dict:
    if _is_gemini_host(base_url):
        return {"x-goog-api-key": api_key or "", "Content-Type": "application/json"}
    return {"Authorization": f"Bearer {api_key or ''}"}


def _parse_image_models(payload, base_url: str) -> List[str]:
    if _is_gemini_host(base_url):
        models = payload.get("models", []) or []
        names = [m.get("name", "") if isinstance(m, dict) else "" for m in models]
        return [n.rsplit("/", 1)[-1] for n in names if n]
    data = payload.get("data", []) or []
    return [m.get("id", "") for m in data if isinstance(m, dict) and m.get("id")]


def fetch_image_models(
    image_base_url: str, api_key: str = "", proxy: str = "", timeout: float = 10
) -> List[str]:
    """Fetch the provider's model list for the given image endpoint.

    Raises the underlying ``httpx`` errors on failure, so callers can mirror the
    existing text-profile Test / Fetch Models UX.
    """
    if not image_base_url:
        raise ValueError("Image endpoint is required.")
    url = _image_models_url(image_base_url)
    client_kwargs = {
        "timeout": timeout,
        "headers": _image_headers(image_base_url, api_key),
    }
    if proxy:
        client_kwargs["proxy"] = proxy
    with httpx.Client(**client_kwargs) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return _parse_image_models(resp.json(), image_base_url)


def probe_connection(host: str, api_key: str, proxy: str = "") -> None:
    """GET ``<host>/models`` and raise on any failure (used by the Test button).

    Runs on a background thread; raises raw ``httpx`` exceptions so callers map
    them to a friendly message without freezing the GUI.
    """
    client_kwargs = {"timeout": 10}
    if proxy:
        client_kwargs["proxy"] = proxy
    with httpx.Client(**client_kwargs) as client:
        resp = client.get(
            f"{host.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()


def probe_model_list(host: str, api_key: str, proxy: str = "") -> List[str]:
    """GET ``<host>/models`` and return the sorted model ids (Fetch Models)."""
    client_kwargs = {"timeout": 10}
    if proxy:
        client_kwargs["proxy"] = proxy
    with httpx.Client(**client_kwargs) as client:
        resp = client.get(
            f"{host.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        models = resp.json().get("data", [])
        return sorted(m["id"] for m in models)


class NetWorker(QThread):
    """Run a blocking network call off the GUI thread.

    The predecessor ran the request synchronously on the GUI thread, so a slow
    or unreachable host froze the whole window (Windows reports "Not
    Responding"). ``finished_ok`` / ``finished_err`` are delivered back on the
    GUI thread via a queued connection, keeping the UI responsive.
    """
    finished_ok = Signal(object)
    finished_err = Signal(object)

    def __init__(self, parent, callback):
        super().__init__(parent)
        self._callback = callback

    def run(self):
        try:
            result = self._callback()
        except Exception as e:  # noqa: BLE001 — deliberate: forward to GUI
            self.finished_err.emit(e)
        else:
            self.finished_ok.emit(result)


def save_all_profiles(profiles: List[Dict]):
    """Replace all profiles and persist to disk immediately."""
    _save_profiles(profiles)
    save_config()


# ── Filterable List Dialog ──


class FilterableListDialog(QDialog):
    """Dialog with search bar + scrollable list. Returns selected item text.

    ``multi_select=True`` 时列表支持多选，结果同时放进 ``selected_items``
    （``selected`` 仍为首项，保持旧调用方兼容）。
    """

    def __init__(
        self,
        parent,
        title: str,
        items: List[str],
        multi_select: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(420, 500)
        self.selected = ""
        self.selected_items: List[str] = []
        self.multi_select = bool(multi_select)
        self._all_items = list(items)

        layout = QVBoxLayout(self)

        self.search_edit = ConfigLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Search..."))
        self.search_edit.textChanged.connect(self._filter)
        layout.addWidget(self.search_edit)

        self.list_widget = QListWidget()
        self.list_widget.addItems(self._all_items)
        if self.multi_select:
            self.list_widget.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection
            )
        self.list_widget.itemDoubleClicked.connect(self._accept_selection)
        layout.addWidget(self.list_widget, 1)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton(self.tr("OK"))
        ok_btn.clicked.connect(self._accept_selection)
        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        # Focus search bar so user can type immediately
        self.search_edit.setFocus()

    def _filter(self, text: str):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not text:
                item.setHidden(False)
            else:
                item.setHidden(text.lower() not in item.text().lower())

    def _accept_selection(self):
        selected = self.list_widget.selectedItems()
        if selected:
            self.selected = selected[0].text()
            self.selected_items = [item.text() for item in selected]
        self.accept()

