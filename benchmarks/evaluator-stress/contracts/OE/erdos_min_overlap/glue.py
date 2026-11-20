import math
import numpy as np
from fractions import Fraction
def c5_of(c):
    h = np.asarray(c["h"], float); n = len(h); dx = 2.0 / n
    return float(np.max(np.correlate(h, 1 - h, mode="full") * dx))
def integral_one(c):
    h = np.asarray(c["h"], float)
    if len(h) == 0 or not np.isfinite(h).all():
        return (False, math.inf)
    d = abs(Fraction(float(np.sum(h))) * Fraction(2, len(h)) - 1)
    return (d <= Fraction(1, 10**12), float(d))
def project(c):
    h = np.clip(np.asarray(c["h"], float), 0, 1)
    for _ in range(20):
        tot = h.sum() * 2.0 / len(h)
        if tot == 0:
            break
        h = np.clip(h / tot, 0, 1)
    return dict(c, h=h)
quantities = {"c5": c5_of}
predicates = {"integral_one": integral_one}


# Record map (spec 6.4): the scorer's combined_score for a construction whose c5 equals v.
maps = {"score_from_c5": lambda v: 0.38092303510845016 / v}
