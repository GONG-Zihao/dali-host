from app.core.dali.frames import (
    addr_broadcast,
    addr_group,
    addr_short,
    make_forward_frame,
)


def test_addr_short_valid():
    assert addr_short(0, False) == 0
    assert addr_short(5, True) == (5 << 1) | 1


def test_addr_short_invalid():
    try:
        addr_short(64, False)
    except ValueError:
        pass
    else:  # pragma: no cover - 确保异常抛出
        raise AssertionError("expected ValueError for short=64")


def test_addr_group_encoding():
    value = addr_group(3, True)
    assert value == 0b1000_0111


def test_addr_broadcast():
    assert addr_broadcast(is_command=False) == 0xFE
    assert addr_broadcast(is_command=True, unaddressed=True) == 0xFD


def test_make_forward_frame():
    frame = make_forward_frame(0x12, 0x34)
    assert frame == b"\x12\x34"

