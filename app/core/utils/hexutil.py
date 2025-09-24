from __future__ import annotations

def _to_byte(tok: str) -> int:
    tok = tok.strip().lower().replace("0x", "")
    if not tok or len(tok) > 2:
        raise ValueError(f"非法字节: {tok!r}")
    v = int(tok, 16)
    if not (0 <= v <= 255):
        raise ValueError(f"字节越界: {tok!r}")
    return v

def parse_pairs(text: str) -> list[tuple[int,int]]:
    """
    解析字符串为若干个(AA,BB)帧对。
    接受格式示例：
      FF 21
      ff 21; c1 08
      FF,21 | C1,08
    分隔符允许：空格、逗号、分号、竖线、换行
    """
    import re
    # 按分号或换行切分为多帧
    chunks = re.split(r"[;\n]+", text)
    out = []
    for ch in chunks:
        toks = [t for t in re.split(r"[\s,\|]+", ch.strip()) if t]
        if not toks:
            continue
        if len(toks) != 2:
            raise ValueError(f"每帧必须两字节，得到 {toks!r}")
        out.append((_to_byte(toks[0]), _to_byte(toks[1])))
    if not out:
        raise ValueError("未解析到任何帧")
    return out

def fmt_pair(a: int, d: int) -> str:
    return f"{a:02X} {d:02X}"
