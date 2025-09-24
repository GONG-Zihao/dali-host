from __future__ import annotations
from pathlib import Path
import json
from typing import List, Dict, Any
from .io.apply import merge_presets

def load_user_presets(path: Path) -> list[dict]:
    if path.exists():
        try:
            data = json.load(open(path, "r", encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            return []
    return []

def save_user_presets(path: Path, presets: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)

def combined_presets(root_dir: Path, cfg: dict) -> list[dict]:
    cfg_presets = cfg.get("presets", [])
    user_path = root_dir / "数据" / "presets.json"
    user_presets = load_user_presets(user_path)
    return merge_presets(cfg_presets, user_presets)
