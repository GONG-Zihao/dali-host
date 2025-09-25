from app.core.controller import Controller


def make_controller():
    cfg = {
        "gateway": {"type": "mock"},
        "ops": {},
        "tc": {"kelvin_min": 1700, "kelvin_max": 8000},
    }
    ctrl = Controller(cfg)
    ctrl.connect()
    return ctrl


def test_dt8_tc_kelvin_conversion():
    ctrl = make_controller()
    result = ctrl.dt8_set_tc_kelvin("short", 4000, addr_val=1)
    assert result["kelvin"] == 4000
    assert 240 <= result["mirek"] <= 260


def test_dt8_tc_clamp():
    ctrl = make_controller()
    res_low = ctrl.dt8_set_tc_kelvin("short", 1000, addr_val=1)
    assert res_low["kelvin"] == 1700
    res_high = ctrl.dt8_set_tc_kelvin("short", 9000, addr_val=1)
    assert res_high["kelvin"] == 8000

