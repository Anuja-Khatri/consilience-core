"""Heilbronn problem for the triangle (AlphaEvolve B.9), OpenEvolve formulation (config.yaml,
initial_program docstring): 11 points on or inside the equilateral triangle with vertices (0, 0),
(1, 0), (1/2, sqrt(3)/2). Containment is decided exactly: y >= 0, y <= sqrt(3) x, y <= sqrt(3) (1 - x)."""
import math
from fractions import Fraction as F

import numpy as np

S3 = math.sqrt(3.0)


def _le_sqrt3(a, b):
    """Exact test a <= sqrt(3) * b for rationals a, b."""
    if b >= 0:
        return a <= 0 or a * a <= 3 * b * b
    return a < 0 and a * a >= 3 * b * b


def in_triangle(c):
    P = np.asarray(c["points"], float)
    if P.ndim != 2 or P.shape[1] != 2 or not np.isfinite(P).all():
        return (False, math.inf)
    worst = 0.0
    for x, y in P:
        fx, fy = F(float(x)), F(float(y))
        d = 0.0
        if fy < 0:
            d = max(d, -float(y))
        if not _le_sqrt3(fy, fx):                       # left edge
            d = max(d, (float(y) - S3 * float(x)) / 2.0, 1e-300)
        if not _le_sqrt3(fy, 1 - fx):                   # right edge
            d = max(d, (float(y) - S3 * (1.0 - float(x))) / 2.0, 1e-300)
        worst = max(worst, d)
    return (worst == 0.0, worst)


predicates = {"in_triangle": in_triangle}
