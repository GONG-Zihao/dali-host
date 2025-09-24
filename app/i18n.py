# app/i18n.py
from __future__ import annotations
import json
import os
import re
from string import Formatter
from typing import Dict, List, Tuple


def _load_json(path: str) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _compile_pattern(template: str) -> Tuple[re.Pattern[str], List[str]]:
    formatter = Formatter()
    pattern = "^"
    field_names: List[str] = []
    for literal, field_name, _format, _conv in formatter.parse(template):
        if literal:
            pattern += re.escape(literal)
        if field_name is not None:
            slot_name = f"__slot{len(field_names)}__"
            field_names.append(field_name)
            pattern += f"(?P<{slot_name}>.+?)"
    pattern += "$"
    return re.compile(pattern), field_names


def _render_template(template: str, values: Dict[str, str]) -> str:
    formatter = Formatter()
    parts: List[str] = []
    for literal, field_name, _format, _conv in formatter.parse(template):
        if literal:
            parts.append(literal)
        if field_name is not None:
            parts.append(values.get(field_name, values.get(field_name.split(".")[0], "")))
    return "".join(parts)


class I18N:
    def __init__(self, lang: str = "zh", base_dir: str | None = None):
        self.lang = lang
        self.base_dir = base_dir or os.path.join(os.path.dirname(__file__), "..", "i18n")
        self._dicts: Dict[str, Dict[str, str]] = {}
        self._direct_raw: Dict[str, str] = {}
        self._direct_maps: Dict[str, Dict[str, str]] = {"zh": {}, "en": {}}
        self._pattern_cache: Dict[str, List[Tuple[re.Pattern[str], str, List[str]]]] = {"zh": [], "en": []}
        self._load_direct_map()
        self.load(lang)

    def load(self, lang: str):
        self.lang = lang
        path = os.path.join(self.base_dir, f"strings.{lang}.json")
        try:
            self._dicts[lang] = _load_json(path)
        except FileNotFoundError:
            self._dicts[lang] = {}
        self._rebuild_direct_maps()

    def t(self, key: str, fallback: str | None = None) -> str:
        return self._dicts.get(self.lang, {}).get(key, fallback if fallback is not None else key)

    def translate_text(self, text: str) -> str:
        return self._translate_text_for_lang(text, self.lang)

    def translate_text_to(self, text: str, lang: str) -> str:
        return self._translate_text_for_lang(text, lang)

    def _translate_text_for_lang(self, text: str, lang: str) -> str:
        if not text:
            return text
        lang_map = self._direct_maps.get(lang)
        if lang_map and text in lang_map:
            return lang_map[text]
        for pattern, target_template, field_names in self._pattern_cache.get(lang, []):
            match = pattern.match(text)
            if not match:
                continue
            values = {}
            for idx, field in enumerate(field_names):
                slot = f"__slot{idx}__"
                values[field] = match.group(slot)
            try:
                return _render_template(target_template, values)
            except Exception:
                return target_template
        return text

    # ---------- Internal ----------
    def _load_direct_map(self):
        path = os.path.join(self.base_dir, "direct.map.json")
        if os.path.exists(path):
            try:
                self._direct_raw = _load_json(path)
            except Exception:
                self._direct_raw = {}
        else:
            self._direct_raw = {}
        self._rebuild_direct_maps()

    def _rebuild_direct_maps(self):
        en_map: Dict[str, str] = {}
        zh_map: Dict[str, str] = {}
        en_patterns: List[Tuple[re.Pattern[str], str, List[str]]] = []
        zh_patterns: List[Tuple[re.Pattern[str], str, List[str]]] = []
        for zh_text, en_text in self._direct_raw.items():
            if not isinstance(zh_text, str) or not zh_text:
                continue
            if not isinstance(en_text, str) or not en_text:
                continue
            en_map[zh_text] = en_text
            zh_map[en_text] = zh_text
            if "{" in zh_text and "}" in zh_text:
                try:
                    pat, fields = _compile_pattern(zh_text)
                    en_patterns.append((pat, en_text, fields))
                except Exception:
                    pass
            if "{" in en_text and "}" in en_text:
                try:
                    pat, fields = _compile_pattern(en_text)
                    zh_patterns.append((pat, zh_text, fields))
                except Exception:
                    pass
        self._direct_maps["en"] = en_map
        self._direct_maps["zh"] = zh_map
        self._pattern_cache["en"] = en_patterns
        self._pattern_cache["zh"] = zh_patterns


# singleton
i18n = I18N()


def tr(zh: str, en: str) -> str:
    """简易双语选择，避免英文界面残留中文。"""
    return en if getattr(i18n, "lang", "zh") == "en" else zh


def trf(zh: str, en: str, **kwargs) -> str:
    """带格式化的双语选择。"""
    return tr(zh, en).format(**kwargs)
