from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from pathlib import Path
import csv, math, statistics

@dataclass
class RunStats:
    name: str
    count: int
    total_ms: float
    mean_ms: float
    std_ms: float
    min_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    approx_ops_per_s: float  # 约等于 1000 / mean_ms

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def load_durations_csv(path: Path) -> List[float]:
    """
    读取 PanelBenchmark 导出的 CSV（列：index,duration_ms）
    返回 duration_ms 列（float 毫秒）。
    """
    vals: List[float] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                vals.append(float(row["duration_ms"]))
            except Exception:
                # 兼容无表头或不同列名的情况
                try:
                    vals.append(float(row.get("duration", row.get("ms", ""))))
                except Exception:
                    continue
    if not vals:
        # 尝试无表头简单两列：index,duration_ms
        f2 = path.read_text(encoding="utf-8").strip().splitlines()
        for line in f2:
            if "," in line:
                try:
                    _idx, ms = line.split(",", 1)
                    if _idx.isdigit():
                        vals.append(float(ms))
                except Exception:
                    pass
    if not vals:
        raise ValueError(f"未能从 CSV 解析到任何 duration_ms：{path}")
    return vals

def _percentile_ms(data: List[float], q: float) -> float:
    """
    百分位（q in [0,100]），线性插值：与 numpy.percentile(method='linear') 近似
    """
    if not data:
        return 0.0
    xs = sorted(data)
    n = len(xs)
    if n == 1:
        return float(xs[0])
    pos = (q / 100.0) * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(xs[lo])
    frac = pos - lo
    return float(xs[lo] * (1 - frac) + xs[hi] * frac)

def compute_stats(name: str, durations_ms: List[float]) -> RunStats:
    if not durations_ms:
        raise ValueError("空数据")
    total_ms = float(sum(durations_ms))
    mean_ms = float(statistics.fmean(durations_ms))
    std_ms = float(statistics.pstdev(durations_ms)) if len(durations_ms) > 1 else 0.0
    return RunStats(
        name=name,
        count=len(durations_ms),
        total_ms=total_ms,
        mean_ms=mean_ms,
        std_ms=std_ms,
        min_ms=float(min(durations_ms)),
        p50_ms=_percentile_ms(durations_ms, 50),
        p95_ms=_percentile_ms(durations_ms, 95),
        p99_ms=_percentile_ms(durations_ms, 99),
        max_ms=float(max(durations_ms)),
        approx_ops_per_s=(1000.0 / mean_ms) if mean_ms > 0 else 0.0,
    )

def ecdf(values: List[float]):
    """经验分布函数：返回 (xs_sorted, ys[0..1])"""
    if not values:
        return [], []
    xs = sorted(values)
    n = len(xs)
    ys = [(i + 1) / n for i in range(n)]
    return xs, ys
