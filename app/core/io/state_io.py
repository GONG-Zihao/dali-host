from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from pathlib import Path
import json

SCHEMA_VERSION = 1

@dataclass
class GroupEntry:
    short: int                # 0..63
    groups: List[int]         # 成员组 0..15

@dataclass
class SceneEntry:
    short: int                # 0..63
    levels: Dict[str, int]    # {"0":0..254, "1":..}

@dataclass
class StateFile:
    version: int
    groups: List[GroupEntry]
    scenes: List[SceneEntry]
    dt8_presets: List[Dict[str, Any]]  # 直接沿用我们面板使用的预设结构

def _ensure_range(v: int, lo: int, hi: int, name="value"):
    if not (lo <= v <= hi):
        raise ValueError(f"{name} 超出范围 [{lo},{hi}]: {v}")

def load_state(path: Path) -> StateFile:
    data = json.load(open(path, "r", encoding="utf-8"))
    if not isinstance(data, dict): raise ValueError("顶层必须是对象")
    ver = int(data.get("version", SCHEMA_VERSION))

    # groups
    groups: List[GroupEntry] = []
    for it in (data.get("groups") or []):
        short = int(it["short"]); _ensure_range(short, 0, 63, "short")
        gl = [int(x) for x in it.get("groups", [])]
        for g in gl: _ensure_range(g, 0, 15, "group")
        groups.append(GroupEntry(short=short, groups=gl))

    # scenes
    scenes: List[SceneEntry] = []
    for it in (data.get("scenes") or []):
        short = int(it["short"]); _ensure_range(short, 0, 63, "short")
        lv = {str(k): int(v) for k, v in (it.get("levels") or {}).items()}
        for s, val in lv.items():
            _ensure_range(int(s), 0, 15, "scene")
            _ensure_range(val, 0, 254, "level")
        scenes.append(SceneEntry(short=short, levels=lv))

    presets = list(data.get("dt8_presets") or [])
    # 预设结构保持原样（name/mode/...）

    return StateFile(version=ver, groups=groups, scenes=scenes, dt8_presets=presets)

def save_state(path: Path, state: StateFile) -> None:
    out = {
        "version": state.version,
        "groups": [asdict(x) for x in state.groups],
        "scenes": [asdict(x) for x in state.scenes],
        "dt8_presets": state.dt8_presets,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

def empty_template() -> StateFile:
    return StateFile(version=SCHEMA_VERSION, groups=[], scenes=[], dt8_presets=[])
