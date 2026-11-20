import itertools, math
from fractions import Fraction as F
import numpy as np

def squares_in_unit_square(centers, sides):
    """Axis-parallel squares, positive sides, inside [0,1]^2, pairwise disjoint interiors (exact)."""
    Cn = np.asarray(centers, float); Sd = np.asarray(sides, float).ravel()
    if Cn.ndim != 2 or Cn.shape[1] != 2 or len(Cn) != len(Sd) or not (np.isfinite(Cn).all() and np.isfinite(Sd).all()):
        return (False, math.inf)
    Q = [(F(float(x)), F(float(y)), F(float(s))) for (x, y), s in zip(Cn, Sd)]
    worst = F(0)
    zero_side = False
    for x, y, s in Q:
        if s <= 0:
            zero_side = True
            worst = max(worst, -s)
        h = s / 2
        worst = max(worst, h - x, x + h - 1, h - y, y + h - 1)
    for a, b in itertools.combinations(Q, 2):
        need = (a[2] + b[2]) / 2
        gx, gy = need - abs(a[0] - b[0]), need - abs(a[1] - b[1])
        if gx > 0 and gy > 0:
            worst = max(worst, min(gx, gy))
    if zero_side and worst == 0:
        return (False, math.inf)
    return (worst <= 0, float(worst))

def to_scorer(c):
    return [np.asarray(c["centers"], float), np.asarray(c["sides"], float)]

predicates = {"squares": lambda c: squares_in_unit_square(c["centers"], c["sides"])}
