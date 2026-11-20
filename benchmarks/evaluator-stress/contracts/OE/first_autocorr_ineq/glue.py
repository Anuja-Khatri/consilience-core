import math
import numpy as np
from fractions import Fraction


def c1_of(c):
    f = np.asarray(c["f"], float); n = len(f); dx = 0.5 / n
    return float(np.max(np.convolve(f, f) * dx) / ((f.sum() * dx) ** 2))


def positive_integral(c):
    """C1 is a ratio with (int f)^2 in the denominator: f must not be identically zero."""
    f = np.asarray(c["f"], float)
    if f.size == 0 or not np.isfinite(f).all():
        return (False, math.inf)
    ok = sum(Fraction(float(v)) for v in f) > 0
    return (ok, 0.0 if ok else math.inf)


quantities = {"c1": c1_of}
predicates = {"positive_integral": positive_integral}


# Record map (spec 6.4): the scorer's combined_score for a construction whose c1 equals v.
maps = {"score_from_c1": lambda v: 1.5052939684401607 / v}
