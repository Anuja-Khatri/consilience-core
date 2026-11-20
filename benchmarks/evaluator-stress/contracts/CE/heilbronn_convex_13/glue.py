import itertools, math
from fractions import Fraction as F
import numpy as np

def hull_nondegenerate(P):
    """Positive hull area: not all points collinear (exact)."""
    P = np.asarray(P, float)
    if P.ndim != 2 or P.shape[1] != 2 or not np.isfinite(P).all():
        return (False, math.inf)
    Q = [(F(float(x)), F(float(y))) for x, y in P]
    a = Q[0]
    for b, c in itertools.combinations(Q[1:], 2):
        if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) != 0:
            return (True, 0.0)
    return (False, math.inf)

def ratio(v):
    """benchmark_ratio = min_area_normalized / BENCHMARK (BENCHMARK copied from the README)."""
    return v / 0.030936889034895654

predicates = {"hull_nondegenerate": lambda c: hull_nondegenerate(c["P"])}
maps = {"ratio": ratio}
