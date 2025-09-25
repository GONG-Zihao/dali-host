from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, List
from .transport.base import Transport, MockTransport
from .transport.tcp_gateway import TcpGateway
from .transport.serial_port import SerialGateway
from .transport.hid_gateway import HidGateway
from .dali.frames import addr_broadcast, addr_short, addr_group, make_forward_frame

class Controller:
    """上位机核心：把GUI动作翻译为传输层帧。"""
    def __init__(self, cfg: dict):
        self._cfg = cfg
        self._log = logging.getLogger("Controller")
        gw_cfg = cfg.get("gateway", {})
        gtype = gw_cfg.get("type", "mock").lower()
        if gtype == "tcp":
            self._transport: Transport = TcpGateway(
                host=gw_cfg.get("host", "127.0.0.1"),
                port=int(gw_cfg.get("port", 5588)),
                timeout=float(gw_cfg.get("timeout_sec", 0.8)),
            )
        elif gtype == "serial":
            self._transport = SerialGateway(
                port=gw_cfg.get("port", "COM1"),
                baudrate=int(gw_cfg.get("baudrate", 19200)),
                timeout=float(gw_cfg.get("timeout_sec", 0.8)),
            )
        elif gtype == "hid":
            vid = gw_cfg.get("vid")
            pid = gw_cfg.get("pid")
            self._transport = HidGateway(
                vendor_id=int(vid, 0) if isinstance(vid, str) else vid,
                product_id=int(pid, 0) if isinstance(pid, str) else pid,
                timeout=float(gw_cfg.get("timeout_sec", 0.8)),
            )
        else:
            self._transport = MockTransport()
        self._log.info("Transport: %s", self._transport.__class__.__name__)

    # 连接管理
    def connect(self) -> bool:
        try:
            self._transport.connect()
            return True
        except Exception as e:
            self._log.error("连接失败: %s", e, exc_info=True)
            return False

    def disconnect(self) -> None:
        try:
            self._transport.disconnect()
        except Exception:
            pass

    def is_connected(self) -> bool:
        return self._transport.is_connected()

    # 调光：发送 ARC 0..254（is_command=False）
    def send_arc(self, mode: str, value: int, addr_val: int | None = None, unaddr: bool = False) -> None:
        """mode: 'broadcast' | 'short' | 'group'"""
        value = max(0, min(254, int(value)))
        if mode == "broadcast":
            a = addr_broadcast(is_command=False, unaddressed=unaddr)
        elif mode == "short":
            if addr_val is None:
                raise ValueError("短地址缺失")
            a = addr_short(int(addr_val), is_command=False)
        elif mode == "group":
            if addr_val is None:
                raise ValueError("组地址缺失")
            a = addr_group(int(addr_val), is_command=False)
        else:
            raise ValueError("未知地址模式")

        frame = make_forward_frame(a, value)
        self._transport.send(frame)
    # 发送命令，并尝试读取一个响应包（通常是1字节）
    def send_command(self, mode: str, opcode: int,
                     addr_val: int | None = None, unaddr: bool = False,
                     timeout: float = 0.3) -> bytes | None:
        from .dali.frames import addr_broadcast, addr_short, addr_group, make_forward_frame
        opcode = int(opcode) & 0xFF

        if mode == "broadcast":
            a = addr_broadcast(is_command=True, unaddressed=unaddr)
        elif mode == "short":
            if addr_val is None: raise ValueError("短地址缺失")
            a = addr_short(int(addr_val), is_command=True)
        elif mode == "group":
            if addr_val is None: raise ValueError("组地址缺失")
            a = addr_group(int(addr_val), is_command=True)
        else:
            raise ValueError("未知地址模式")

        frame = make_forward_frame(a, opcode)
        self._transport.send(frame)
        return self._transport.recv(timeout=timeout)

    # ========== 设备查询 ==========
    def query_status(self, short_addr: int, timeout: float = 0.3) -> bytes | None:
        opcode = int(self._cfg_ops().get("query_status", 144))
        return self.send_command("short", opcode, addr_val=int(short_addr), timeout=timeout)

    def query_groups(self, short_addr: int, timeout: float = 0.3) -> Dict[int, int]:
        ops = self._cfg_ops()
        groups: Dict[int, int] = {i: 0 for i in range(16)}

        lo_opcode = int(ops.get("query_groups_0_7", 192))
        hi_opcode = int(ops.get("query_groups_8_15", 193))

        lo_resp = self.send_command("short", lo_opcode, addr_val=int(short_addr), timeout=timeout)
        hi_resp = self.send_command("short", hi_opcode, addr_val=int(short_addr), timeout=timeout)

        if lo_resp:
            mask = lo_resp[0]
            for bit in range(8):
                groups[bit] = 1 if (mask >> bit) & 1 else 0
        if hi_resp:
            mask = hi_resp[0]
            for bit in range(8):
                groups[8 + bit] = 1 if (mask >> bit) & 1 else 0
        return groups

    def query_scene_levels(self, short_addr: int, timeout: float = 0.3) -> Dict[int, int | None]:
        ops = self._cfg_ops()
        base = int(ops.get("query_scene_level_base", 176))
        levels: Dict[int, int | None] = {}
        for scene in range(16):
            opcode = (base + scene) & 0xFF
            resp = self.send_command("short", opcode, addr_val=int(short_addr), timeout=timeout)
            if resp and len(resp) > 0:
                levels[scene] = int(resp[0])
            else:
                levels[scene] = None
        return levels

    def scan_devices(self, short_range: range | List[int] = range(64), timeout: float = 0.3) -> List[int]:
        found: List[int] = []
        for short in short_range:
            try:
                resp = self.query_status(int(short), timeout=timeout)
                if resp is not None:
                    found.append(int(short))
            except Exception as exc:  # pragma: no cover - transport failures only logged
                self._log.debug("query_status failed for %s: %s", short, exc)
        return found

    # ========== 组管理 ==========
    def group_add(self, target_mode: str, group: int, addr_val: int | None = None, unaddr: bool = False):
        """
        将目标（短地址 / 广播）加入 group(0..15)。
        注：组成员关系写入设备，通常应对短地址或广播操作，不对“组地址”本身操作。
        """
        ops = self._cfg_ops()
        opcode = int(ops["add_to_group_base"] + int(group))
        self._send_command_to_target(target_mode, opcode, addr_val, unaddr)

    def group_remove(self, target_mode: str, group: int, addr_val: int | None = None, unaddr: bool = False):
        """从 group(0..15) 中移除目标。"""
        ops = self._cfg_ops()
        opcode = int(ops["remove_from_group_base"] + int(group))
        self._send_command_to_target(target_mode, opcode, addr_val, unaddr)

    # ========== 场景管理 ==========
    def scene_recall(self, target_mode: str, scene: int, addr_val: int | None = None, unaddr: bool = False):
        """回放场景 scene(0..15)。"""
        ops = self._cfg_ops()
        opcode = int(ops["recall_scene_base"] + int(scene))
        self._send_command_to_target(target_mode, opcode, addr_val, unaddr)

    def scene_store_level(self, target_mode: str, scene: int, level: int,
                          addr_val: int | None = None, unaddr: bool = False):
        """
        把 level(0..254) 写入为场景 scene(0..15) 的亮度：
        先写 DTR，再发送“将 DTR 保存为场景 scene”的命令。
        """
        ops = self._cfg_ops()
        write_dtr = int(ops["write_dtr"])
        store_base = int(ops["store_dtr_as_scene_base"])
        scene = int(scene) & 0x0F
        level = max(0, min(254, int(level)))

        # Step1: 写DTR（命令发给目标）
        self._send_command_to_target(target_mode, write_dtr, addr_val, unaddr)
        # Step2: 再发一次写DTR值？——有的网关把“写DTR值”实现为“先ARC=level，再WRITE_DTR”
        # 为了兼容性，先把ARC调到目标值（不影响最终存档），再写入DTR命令一次：
        from .dali.frames import make_forward_frame, addr_broadcast, addr_short, addr_group
        # 设ARC（S=0）
        a = self._address_byte(target_mode, addr_val, unaddr, is_command=False)
        self._transport.send(make_forward_frame(a, level))
        # 写DTR（S=1）
        a_cmd = self._address_byte(target_mode, addr_val, unaddr, is_command=True)
        self._transport.send(make_forward_frame(a_cmd, write_dtr))

        # Step3: 将DTR保存为场景
        self._send_command_to_target(target_mode, store_base + scene, addr_val, unaddr)

    def scene_remove(self, target_mode: str, scene: int, addr_val: int | None = None, unaddr: bool = False):
        """将目标从场景 scene(0..15) 中移除。"""
        ops = self._cfg_ops()
        opcode = int(ops["remove_from_scene_base"] + int(scene))
        self._send_command_to_target(target_mode, opcode, addr_val, unaddr)

    # ========== 工具函数 ==========
    def _cfg_ops(self) -> dict:
        # 从 MainWindow 传入的 config 获取 ops；若没挂入，回退默认
        try:
            return getattr(self, "_ops_cache")
        except AttributeError:
            pass
        ops = getattr(self, "_cfg", {}).get("ops", {}) if hasattr(self, "_cfg") else {}
        if not ops:
            ops = {
                "recall_scene_base": 64, "store_dtr_as_scene_base": 80, "remove_from_scene_base": 144,
                "add_to_group_base": 96, "remove_from_group_base": 112, "write_dtr": 163
            }
        self._ops_cache = ops
        return ops

    def _address_byte(self, mode: str, addr_val: int | None, unaddr: bool, is_command: bool) -> int:
        from .dali.frames import addr_broadcast, addr_short, addr_group
        if mode == "broadcast":
            return addr_broadcast(is_command=is_command, unaddressed=unaddr)
        elif mode == "short":
            if addr_val is None: raise ValueError("短地址缺失")
            return addr_short(int(addr_val), is_command=is_command)
        elif mode == "group":
            if addr_val is None: raise ValueError("组地址缺失")
            return addr_group(int(addr_val), is_command=is_command)
        else:
            raise ValueError("未知目标模式")

    def _send_command_to_target(self, mode: str, opcode: int, addr_val: int | None, unaddr: bool):
        from .dali.frames import make_forward_frame
        a = self._address_byte(mode, addr_val, unaddr, is_command=True)
        frame = make_forward_frame(a, int(opcode) & 0xFF)
        self._transport.send(frame)

    # ====== DT8 / Tc ======
    def dt8_set_tc_kelvin(self, mode: str, kelvin: int,
                          addr_val: int | None = None, unaddr: bool = False):
        """以 K 设置色温（DT8 / Tc）。内部自动换算 Mirek 并写 DTR0/1，再启用DT8后发送 Set-Tc。"""
        ops = self._cfg.get("ops", {})
        tc_cfg = self._cfg.get("tc", {})
        kmin = int(tc_cfg.get("kelvin_min", 1700))
        kmax = int(tc_cfg.get("kelvin_max", 8000))

        k = max(kmin, min(kmax, int(kelvin)))
        # Mirek = 1e6 / K ；范围 1..65534（0保留），四舍五入
        mirek = max(1, min(65534, int(round(1_000_000 / float(k)))))
        lsb = mirek & 0xFF
        msb = (mirek >> 8) & 0xFF

        from .dali.frames import make_forward_frame

        # 写 DTR0 / DTR1 （特殊地址字节）
        self._transport.send(make_forward_frame(int(ops["write_dtr0_addr"]) & 0xFF, lsb))
        self._transport.send(make_forward_frame(int(ops["write_dtr1_addr"]) & 0xFF, msb))

        # 启用 Device Type = 8（特殊地址字节 0xC1, data=8）
        self._transport.send(make_forward_frame(int(ops["dt8_enable_addr"]) & 0xFF, 8))

        # 发送“Set Temporary Colour Temperature Tc”（寻址命令）
        a = self._address_byte(mode, addr_val, unaddr, is_command=True)
        self._transport.send(make_forward_frame(a, int(ops["dt8_set_tc_opcode"]) & 0xFF))

        return {"kelvin": k, "mirek": mirek}

    # 可选：直接以 Mirek 设置（给自动化/脚本用）
    def dt8_set_tc_mirek(self, mode: str, mirek: int,
                         addr_val: int | None = None, unaddr: bool = False):
        mirek = max(1, min(65534, int(mirek)))
        lsb = mirek & 0xFF
        msb = (mirek >> 8) & 0xFF
        ops = self._cfg.get("ops", {})
        from .dali.frames import make_forward_frame
        self._transport.send(make_forward_frame(int(ops["write_dtr0_addr"]) & 0xFF, lsb))
        self._transport.send(make_forward_frame(int(ops["write_dtr1_addr"]) & 0xFF, msb))
        self._transport.send(make_forward_frame(int(ops["dt8_enable_addr"]) & 0xFF, 8))
        a = self._address_byte(mode, addr_val, unaddr, is_command=True)
        self._transport.send(make_forward_frame(a, int(ops["dt8_set_tc_opcode"]) & 0xFF))
        return {"mirek": mirek, "kelvin": int(round(1_000_000 / mirek))}

    # ====== DT8 / xy ======
    def dt8_set_xy(self, mode: str, x: float, y: float,
                   addr_val: int | None = None, unaddr: bool = False):
        """
        设置 CIE xy（0..1）。内部：xy*65535 → 16位；依次写 X、写 Y。
        每次：写 DTR0/1 -> Enable DT8 -> 发送对应 opcode（寻址）。
        """
        ops = self._cfg.get("ops", {})
        set_x = int(ops.get("dt8_set_x_opcode", 224))
        set_y = int(ops.get("dt8_set_y_opcode", 225))
        w_dtr0 = int(ops.get("write_dtr0_addr", 163))  # 0xA3
        w_dtr1 = int(ops.get("write_dtr1_addr", 195))  # 0xC3
        ena    = int(ops.get("dt8_enable_addr", 193))  # 0xC1

        def _u16(v: float) -> tuple[int, int]:
            n = max(0, min(65535, int(round(float(v) * 65535.0))))
            return n & 0xFF, (n >> 8) & 0xFF

        from .dali.frames import make_forward_frame
        # X
        lsb, msb = _u16(x)
        self._transport.send(make_forward_frame(w_dtr0, lsb))
        self._transport.send(make_forward_frame(w_dtr1, msb))
        self._transport.send(make_forward_frame(ena, 8))
        a = self._address_byte(mode, addr_val, unaddr, is_command=True)
        self._transport.send(make_forward_frame(a, set_x & 0xFF))

        # Y
        lsb, msb = _u16(y)
        self._transport.send(make_forward_frame(w_dtr0, lsb))
        self._transport.send(make_forward_frame(w_dtr1, msb))
        self._transport.send(make_forward_frame(ena, 8))
        self._transport.send(make_forward_frame(a, set_y & 0xFF))

        return {
            "x_u16": int(round(x*65535)), "y_u16": int(round(y*65535)),
            "x": float(x), "y": float(y)
        }

    # ====== DT8 / RGBW(A/F) 单通道 ======
    def dt8_set_primary(self, mode: str, channel: str, level: int,
                        addr_val: int | None = None, unaddr: bool = False):
        """
        设置单个主色通道（RGBW/可扩展 A,F）。
        level 0..254（常见做法：写入 DTR0 然后发 'Set Primary X'）
        """
        ops = self._cfg.get("ops", {})
        prim_map: dict = ops.get("dt8_set_primary", {})
        opcode = prim_map.get(channel.lower())
        if opcode is None:
            raise ValueError(f"配置中未定义主色通道 '{channel}' 的 opcode")
        w_dtr0 = int(ops.get("write_dtr0_addr", 163))
        ena    = int(ops.get("dt8_enable_addr", 193))

        level = max(0, min(254, int(level)))
        from .dali.frames import make_forward_frame

        self._transport.send(make_forward_frame(w_dtr0, level & 0xFF))
        self._transport.send(make_forward_frame(ena, 8))
        a = self._address_byte(mode, addr_val, unaddr, is_command=True)
        self._transport.send(make_forward_frame(a, int(opcode) & 0xFF))
        return {"channel": channel.lower(), "level": level}

    # ====== DT8 / RGBW 批量 ======
    def dt8_set_rgbw(self, mode: str, r: int, g: int, b: int, w: int = 0,
                     addr_val: int | None = None, unaddr: bool = False):
        out = []
        for ch, val in (("r", r), ("g", g), ("b", b), ("w", w)):
            out.append(self.dt8_set_primary(mode, ch, val, addr_val=addr_val, unaddr=unaddr))
        return out

    # 原始两字节前向帧（addr, data）
    def send_raw(self, addr_byte: int, data_byte: int):
        from .dali.frames import make_forward_frame
        a = int(addr_byte) & 0xFF
        d = int(data_byte) & 0xFF
        self._transport.send(make_forward_frame(a, d))

    # 批量发送多帧
    def send_sequence(self, frames: list[tuple[int, int]]):
        for a, d in frames:
            self.send_raw(a, d)
