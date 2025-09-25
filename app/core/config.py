from __future__ import annotations
from pathlib import Path
import logging

try:
    import yaml  # pip install pyyaml
except Exception:
    yaml = None

_DEFAULT = {
    "gateway": {
        "type": "mock",   # "tcp" | "serial" | "hid" | "mock"
        "host": "127.0.0.1",
        "port": 5588,
        "timeout_sec": 0.8,
    }
}

def load_yaml(path: Path) -> dict:
    log = logging.getLogger("Config")
    if path.exists() and yaml is not None:
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            log.warning("YAML 解析失败，使用默认配置: %s", e)
    elif yaml is None:
        log.warning("未安装 pyyaml，使用默认配置")
    return {}

def get_app_config(root_dir: Path) -> dict:
    cfg_dir = root_dir / "配置"
    if not cfg_dir.exists():
        alt = root_dir / "config"
        if alt.exists():
            cfg_dir = alt
    app_cfg  = load_yaml(cfg_dir / "应用.yaml")
    conn_cfg = load_yaml(cfg_dir / "连接.yaml")
    dali_cfg = load_yaml(cfg_dir / "dali.yaml")

    cfg = {}
    cfg.update(app_cfg); cfg.update(conn_cfg); cfg.update(dali_cfg)

    # 默认
    for k, v in _DEFAULT.items():
        cfg.setdefault(k, v)
        if isinstance(v, dict):
            for kk, vv in v.items():
                cfg[k].setdefault(kk, vv)

    # ops 兜底
    ops = cfg.setdefault("ops", {})
    ops.setdefault("recall_scene_base", 64)
    ops.setdefault("store_dtr_as_scene_base", 80)
    ops.setdefault("remove_from_scene_base", 144)
    ops.setdefault("add_to_group_base", 96)
    ops.setdefault("remove_from_group_base", 112)
    ops.setdefault("write_dtr", 163)
    ops.setdefault("query_status", 144)
    ops.setdefault("query_groups_0_7", 192)
    ops.setdefault("query_groups_8_15", 193)
    ops.setdefault("query_scene_level_base", 176)
    # DT8 默认
    ops.setdefault("dt8_enable_addr", 193)
    ops.setdefault("dt8_set_tc_opcode", 231)
    ops.setdefault("write_dtr0_addr", 163)
    ops.setdefault("write_dtr1_addr", 195)

    # Tc 范围
    tc = cfg.setdefault("tc", {})
    tc.setdefault("kelvin_min", 1700)
    tc.setdefault("kelvin_max", 8000)
    # xy
    ops.setdefault("dt8_set_x_opcode", 224)
    ops.setdefault("dt8_set_y_opcode", 225)
    # primary 映射
    prim = ops.setdefault("dt8_set_primary", {})
    prim.setdefault("r", 226);
    prim.setdefault("g", 227)
    prim.setdefault("b", 228);
    prim.setdefault("w", 229)
    cfg.setdefault("presets", [
        {"name": "红", "mode": "rgbw", "values": {"r": 254, "g": 0, "b": 0, "w": 0}},
        {"name": "绿", "mode": "rgbw", "values": {"r": 0, "g": 254, "b": 0, "w": 0}},
        {"name": "蓝", "mode": "rgbw", "values": {"r": 0, "g": 0, "b": 254, "w": 0}},
        {"name": "暖白(2700K)", "mode": "tc", "kelvin": 2700},
        {"name": "中性白(4000K)", "mode": "tc", "kelvin": 4000},
        {"name": "冷白(6500K)", "mode": "tc", "kelvin": 6500},
        {"name": "D65", "mode": "xy", "values": {"x": 0.3127, "y": 0.3290}},
    ])
    return cfg

