"""Uncertainty inequality (AlphaEvolve B.4), OpenEvolve formulation (README, config.yaml).

Construction: coefficients c_0..c_{m-1} of physicists' Hermite polynomials H_0, H_4, ..., H_{4(m-1)};
a last coefficient on H_{4m} is chosen so that P(0) = 0, and P is negated if its leading coefficient is
negative. f(x) = P(x) exp(-x^2/2) is then even, equal to its own Fourier transform (up to the
convention), with f(0) = 0. A(f) = r_max is the largest positive x where P changes sign (P >= 0
beyond it), and C4 = r_max^2 / (2 pi). Exact rational arithmetic; roots refined by bisection.
"""
import math
from fractions import Fraction

import numpy as np


def _hermite(n):
    """Physicists' Hermite polynomial H_n as integer coefficients, lowest degree first."""
    h0, h1 = [1], [0, 2]
    if n == 0:
        return h0
    for k in range(1, n):
        nxt = [0] * (k + 2)
        for i, a in enumerate(h1):
            nxt[i + 1] += 2 * a
        for i, a in enumerate(h0):
            nxt[i] -= 2 * k * a
        h0, h1 = h1, nxt
    return h1


def _poly(coeffs):
    """P (exact, lowest degree first) for the given input coefficients, or None if degenerate."""
    cs = [Fraction(float(v)) for v in np.asarray(coeffs, float).ravel()]
    m = len(cs)
    if m == 0:
        return None
    P = [Fraction(0)] * (4 * m + 1)
    for i, c in enumerate(cs):
        for d, a in enumerate(_hermite(4 * i)):
            P[d] += c * a
    Hm = _hermite(4 * m)
    c_last = -P[0] / Hm[0]
    for d, a in enumerate(Hm):
        P[d] += c_last * a
    while len(P) > 1 and P[-1] == 0:
        P.pop()
    if all(v == 0 for v in P):
        return None
    if P[-1] < 0:
        P = [-v for v in P]
    return P


def _ev(Q, x):
    v = Fraction(0)
    for a in reversed(Q):
        v = v * x + a
    return v


def r_max_of(c):
    P = _poly(c["coeffs"])
    if P is None or len(P) < 3 or P[0] != 0 or P[1] != 0:
        return math.nan
    Q = P[2:]                                   # P / x^2 (P is even with P(0) = 0)
    if len(Q) == 1:
        return math.nan
    approx = np.roots([float(a) for a in reversed(Q)])
    cands = sorted({float(z.real) for z in approx if z.real > 0 and abs(z.imag) <= 1e-6 * max(1.0, abs(z))},
                   reverse=True)
    for r in cands:
        d = 1e-6 * max(1.0, r)
        lo, hi = Fraction(max(r - d, 0.0)), Fraction(r + d)
        slo, shi = _ev(Q, lo), _ev(Q, hi)
        if slo == 0 or shi == 0 or (slo > 0) == (shi > 0):
            continue                             # no sign change in this bracket
        for _ in range(60):
            mid = (lo + hi) / 2
            sm = _ev(Q, mid)
            if sm == 0:
                lo = hi = mid
                break
            if (sm > 0) == (slo > 0):
                lo = mid
            else:
                hi = mid
        return float((lo + hi) / 2)
    return math.nan


def c4_of(c):
    r = r_max_of(c)
    return r * r / (2.0 * np.pi)


def sign_change(c):
    """A valid construction gives a non-trivial f: P / x^2 changes sign at some x > 0, so that
    A(f) = r_max > 0 is defined."""
    a = np.asarray(c["coeffs"], float)
    if a.size == 0 or not np.isfinite(a).all():
        return (False, math.inf)
    r = r_max_of(c)
    ok = not math.isnan(r) and r > 0
    return (ok, 0.0 if ok else math.inf)


quantities = {"c4": c4_of, "r_max": r_max_of}
predicates = {"sign_change": sign_change}
