from app.core.analysis.stats import compute_stats, ecdf


def test_compute_stats_basic():
    durations = [10.0, 20.0, 30.0, 40.0]
    stats = compute_stats("sample", durations)
    assert stats.count == 4
    assert stats.min_ms == 10.0
    assert stats.max_ms == 40.0
    assert stats.p50_ms == 25.0
    assert stats.p95_ms >= stats.p50_ms
    assert stats.approx_ops_per_s > 0


def test_ecdf_sorted_output():
    xs, ys = ecdf([3, 1, 2])
    assert xs == [1, 2, 3]
    assert ys == [1 / 3, 2 / 3, 1.0]

