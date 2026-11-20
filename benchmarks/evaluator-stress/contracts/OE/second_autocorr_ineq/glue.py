import math
import numpy as np
from fractions import Fraction


def c2_of(c):
    """C2(f) = ||f*f||_2^2 / (||f*f||_1 ||f*f||_inf) for the step function f with n equal steps on
    [-1/4, 1/4]. f*f is piecewise linear with knots every h = 1/(2n) (values h * discrete
    autoconvolution, zero at both ends); the L2 norm of each linear piece is integrated exactly."""
    f = np.asarray(c["f"], float); n = len(f); h = 1.0 / (2 * n)
    g = np.concatenate(([0.0], np.convolve(f, f) * h, [0.0]))
    l2sq = float(np.sum(h / 3.0 * (g[:-1] ** 2 + g[:-1] * g[1:] + g[1:] ** 2)))
    l1 = float(np.sum(h / 2.0 * (np.abs(g[:-1]) + np.abs(g[1:]))))   # exact for non-negative f (no sign change)
    linf = float(np.max(np.abs(g)))
    return l2sq / (l1 * linf)


def positive_integral(c):
    """C2 divides by norms of f*f: f must not be identically zero."""
    f = np.asarray(c["f"], float)
    if f.size == 0 or not np.isfinite(f).all():
        return (False, math.inf)
    ok = sum(Fraction(float(v)) for v in f) > 0
    return (ok, 0.0 if ok else math.inf)


quantities = {"c2": c2_of}
predicates = {"positive_integral": positive_integral}


# Record map (spec 6.4): the scorer's combined_score for a construction whose c2 equals v.
maps = {"score_from_c2": lambda v: v / 0.8962799441554086}
