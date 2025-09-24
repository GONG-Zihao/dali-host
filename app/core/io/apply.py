from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path

from .state_io import GroupEntry, SceneEntry

def apply_groups(controller, entries: List[GroupEntry], clear_others: bool = False):
    """
    将组成员关系应用到设备。
    - 若 clear_others=True，会对每个 short 发送“从所有未列出的组移除”，总最多16条。
    - 否则只发送“加入列表中的组”（不做移除）。
    """
    for e in entries:
        want = set(int(g) for g in e.groups)
        if clear_others:
            for g in range(16):
                if g in want:
                    controller.group_add("short", g, addr_val=int(e.short))
                else:
                    controller.group_remove("short", g, addr_val=int(e.short))
        else:
            for g in sorted(want):
                controller.group_add("short", g, addr_val=int(e.short))

def apply_scenes(controller, entries: List[SceneEntry], recall_after_store: bool = False):
    """
    将亮度表写入场景。entries[i].levels 形如 {"2":128, "5":254}
    """
    for e in entries:
        for s_str, level in e.levels.items():
            scene = int(s_str)
            controller.scene_store_level("short", scene, int(level), addr_val=int(e.short))
            if recall_after_store:
                controller.scene_recall("short", scene, addr_val=int(e.short))

def merge_presets(cfg_presets: List[Dict[str, Any]], user_presets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按 name 去重合并（user 覆盖同名项）"""
    out = {p.get("name", f"preset-{i}"): p for i, p in enumerate(cfg_presets or [])}
    for p in (user_presets or []):
        name = p.get("name")
        if not name:
            name = f"user-{len(out)}"
            p = dict(p); p["name"] = name
        out[name] = p
    return list(out.values())
