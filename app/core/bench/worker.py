from __future__ import annotations
import time, threading, statistics
from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, List

from PySide6.QtCore import QObject, Signal

@dataclass
class BenchPlan:
    # 地址
    mode: str                # 'broadcast' | 'short' | 'group'
    addr_val: Optional[int]  # None/0..63/0..15
    unaddr: bool             # 仅未寻址（仅广播有用）

    # 任务类型与参数
    task: str                # 'arc_fixed'|'arc_sweep'|'scene_recall'|'dt8_tc_fixed'|'dt8_xy_fixed'|'dt8_rgbw_fixed'
    params: Dict[str, Any]   # 各任务所需参数

    # 节奏
    total: int               # 发送总次数
    interval_ms: int         # 两次发送的目标间隔（毫秒）
    recv_timeout_ms: int     # 可选接收等待（目前大多数命令不强制）

class BenchWorker(QObject):
    progress = Signal(dict)   # {sent, ok, err, last_ms, avg_ms, min_ms, max_ms}
    finished = Signal(dict)   # {sent, ok, err, avg_ms, min_ms, max_ms, durations}
    log = Signal(str)

    def __init__(self, controller, plan: BenchPlan):
        super().__init__()
        self.ctrl = controller
        self.plan = plan
        self._stop = threading.Event()
        self._durations: List[float] = []
        self._ok = 0
        self._err = 0
        self._sent = 0

    def stop(self):
        self._stop.set()

    # --- 任务映射 ---
    def _send_once(self, i: int):
        p = self.plan
        t0 = time.perf_counter()

        try:
            if p.task == "arc_fixed":
                v = int(p.params.get("arc", 128))
                self.ctrl.send_arc(p.mode, v, p.addr_val, p.unaddr)

            elif p.task == "arc_sweep":
                lo = int(p.params.get("lo", 0))
                hi = int(p.params.get("hi", 254))
                step = max(1, int(p.params.get("step", 5)))
                # 循环扫描：i 决定当前值
                rng = hi - lo + 1
                v = lo + ((i * step) % rng)
                v = max(lo, min(hi, v))
                self.ctrl.send_arc(p.mode, v, p.addr_val, p.unaddr)

            elif p.task == "scene_recall":
                sc = int(p.params.get("scene", 0))
                self.ctrl.scene_recall(p.mode, sc, p.addr_val, p.unaddr)

            elif p.task == "dt8_tc_fixed":
                k = int(p.params.get("kelvin", 4000))
                self.ctrl.dt8_set_tc_kelvin(p.mode, k, p.addr_val, p.unaddr)

            elif p.task == "dt8_xy_fixed":
                x = float(p.params.get("x", 0.313))
                y = float(p.params.get("y", 0.329))
                self.ctrl.dt8_set_xy(p.mode, x, y, p.addr_val, p.unaddr)

            elif p.task == "dt8_rgbw_fixed":
                r = int(p.params.get("r", 0))
                g = int(p.params.get("g", 0))
                b = int(p.params.get("b", 0))
                w = int(p.params.get("w", 0))
                self.ctrl.dt8_set_rgbw(p.mode, r, g, b, w, p.addr_val, p.unaddr)

            else:
                raise ValueError(f"未知任务：{p.task}")

            ok = True
        except Exception as e:
            ok = False
            self.log.emit(f"ERR: {e!r}")

        t1 = time.perf_counter()
        dt_ms = (t1 - t0) * 1000.0
        self._sent += 1
        if ok:
            self._ok += 1
        else:
            self._err += 1

        self._durations.append(dt_ms)
        avg = statistics.fmean(self._durations) if self._durations else 0.0
        self.progress.emit({
            "sent": self._sent, "ok": self._ok, "err": self._err,
            "last_ms": dt_ms, "avg_ms": avg,
            "min_ms": min(self._durations) if self._durations else 0.0,
            "max_ms": max(self._durations) if self._durations else 0.0,
        })

    def run(self):
        p = self.plan
        interval = max(0.0, float(p.interval_ms) / 1000.0)
        for i in range(p.total):
            if self._stop.is_set():
                break
            start = time.perf_counter()
            self._send_once(i)
            # 节流到指定间隔
            used = time.perf_counter() - start
            remain = interval - used
            if remain > 0:
                time.sleep(remain)

        avg = statistics.fmean(self._durations) if self._durations else 0.0
        self.finished.emit({
            "sent": self._sent, "ok": self._ok, "err": self._err,
            "avg_ms": avg,
            "min_ms": min(self._durations) if self._durations else 0.0,
            "max_ms": max(self._durations) if self._durations else 0.0,
            "durations": self._durations,
        })
