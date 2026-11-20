import numpy as np

def positive_sum(c):
    """f is not identically zero (the constant is defined only for f != 0)."""
    a = np.asarray(c["f"], float)
    if a.size == 0 or not np.isfinite(a).all():
        return (False, float("inf"))
    return (bool(np.sum(np.maximum(a, 0.0)) > 0), float("inf"))

def benchmark_ratio_from_c2(v):
    """benchmark_ratio = C2 / BENCHMARK with BENCHMARK = 0.962 (copied from the README)."""
    return v / 0.962

predicates = {"positive_sum": positive_sum}
maps = {"benchmark_ratio_from_c2": benchmark_ratio_from_c2}
