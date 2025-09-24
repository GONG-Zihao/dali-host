from __future__ import annotations

def addr_short(short_addr: int, is_command: bool) -> int:
    """0AAA AAAS：短地址 0..63；S=0 表示ARC亮度，S=1表示命令。"""
    if not (0 <= short_addr < 64):
        raise ValueError("short_addr must be 0..63")
    s = 1 if is_command else 0
    return ((short_addr & 0x3F) << 1) | s

def addr_group(group: int, is_command: bool) -> int:
    """100A AAAS：组地址 0..15。"""
    if not (0 <= group < 16):
        raise ValueError("group must be 0..15")
    s = 1 if is_command else 0
    return 0b1000_0000 | ((group & 0x0F) << 1) | s

def addr_broadcast(is_command: bool, unaddressed: bool = False) -> int:
    """
    广播：1111111S -> 0xFE/0xFF
    未寻址广播：1111110S -> 0xFC/0xFD
    """
    base7 = 0x7E if unaddressed else 0x7F  # 7位高位
    s = 1 if is_command else 0
    return (base7 << 1) | s


def make_forward_frame(addr_byte: int, opcode_or_arc: int) -> bytes:
    """前向帧：地址字节 + 操作码/亮度（8位）。"""
    return bytes([(addr_byte & 0xFF), (opcode_or_arc & 0xFF)])
