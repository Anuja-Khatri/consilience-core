import itertools, math
from fractions import Fraction as F
import numpy as np

def circles_in_rect_perimeter4(C):
    C = np.asarray(C, float)
    if C.ndim != 2 or C.shape[1] != 3 or not np.isfinite(C).all():
        return (False, math.inf)
    R = [[F(float(v)) for v in row] for row in C]
    worst = F(0)
    for _, _, r in R:
        worst = max(worst, -r)
    for a, b in itertools.combinations(R, 2):
        s = a[2] + b[2]
        d2 = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
        if s > 0 and d2 < s * s:
            worst = max(worst, s - F(math.sqrt(float(d2))))
    w = max(f[0] + f[2] for f in R) - min(f[0] - f[2] for f in R)
    h = max(f[1] + f[2] for f in R) - min(f[1] - f[2] for f in R)
    worst = max(worst, (w + h) - 2)
    return (worst <= 0, float(worst))

def ratio(v):
    """benchmark_ratio = radii_sum / BENCHMARK (BENCHMARK copied from the README)."""
    return v / 2.3658321334167627

predicates = {"packing": lambda c: circles_in_rect_perimeter4(c["circles"])}
maps = {"ratio": ratio}
