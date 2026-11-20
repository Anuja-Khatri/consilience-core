import numpy as np

def positive_sum(c):
    """f is not identically zero (the constant is defined only for f != 0)."""
    a = np.asarray(c["a"], float)
    if a.size == 0 or not np.isfinite(a).all():
        return (False, float("inf"))
    return (bool(np.sum(np.maximum(a, 0.0)) > 0), float("inf"))

def benchmark_ratio_from_c1(v):
    """benchmark_ratio = BENCHMARK / C1 with BENCHMARK = 1.5031 (copied from the README)."""
    return 1.5031 / v

predicates = {"positive_sum": positive_sum}
maps = {"benchmark_ratio_from_c1": benchmark_ratio_from_c1}
