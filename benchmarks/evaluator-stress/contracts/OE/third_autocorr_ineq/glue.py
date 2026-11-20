import math
import numpy as np
from fractions import Fraction


def c3_of(c):
    f = np.asarray(c["f"], float); n = len(f); dx = 0.5 / n
    return float(np.max(np.abs(np.convolve(f, f) * dx)) / ((f.sum() * dx) ** 2))


def nonzero_integral(c):
    """C3 is a ratio with (int f)^2 in the denominator: int f must not be zero."""
    f = np.asarray(c["f"], float)
    if f.size == 0 or not np.isfinite(f).all():
        return (False, math.inf)
    ok = sum(Fraction(float(v)) for v in f) != 0
    return (ok, 0.0 if ok else math.inf)


quantities = {"c3": c3_of}
predicates = {"nonzero_integral": nonzero_integral}
