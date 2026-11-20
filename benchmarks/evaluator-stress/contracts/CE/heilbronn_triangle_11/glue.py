import itertools, math
from fractions import Fraction as F
import numpy as np

def in_equilateral_triangle(P):
    """Closed triangle (0,0),(1,0),(1/2,sqrt3/2): y>=0, y<=sqrt3*x, y<=sqrt3*(1-x); exact via squares."""
    P = np.asarray(P, float)
    if P.ndim != 2 or P.shape[1] != 2 or not np.isfinite(P).all():
        return (False, math.inf)
    worst = 0.0
    s3 = math.sqrt(3.0)
    for x, y in P:
        X, Y = F(float(x)), F(float(y))
        ok = Y >= 0
        for u in (X, 1 - X):          # need Y <= sqrt3*u  <=>  u >= 0 and (Y <= 0 or Y^2 <= 3u^2)
            ok = ok and u >= 0 and (Y <= 0 or Y * Y <= 3 * u * u)
        if not ok:
            # distance-like magnitude (float): max violation of the three half-planes
            worst = max(worst, -float(y), (float(y) - s3 * float(x)) / 2, (float(y) - s3 * (1 - float(x))) / 2, 1e-18)
    return (worst == 0.0, worst)

def ratio(v):
    """benchmark_ratio = min_area_normalized / BENCHMARK (BENCHMARK copied from the README)."""
    return v / 0.036529889880030156

predicates = {"in_equilateral_triangle": lambda c: in_equilateral_triangle(c["P"])}
maps = {"ratio": ratio}
