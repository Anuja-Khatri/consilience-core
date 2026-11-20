"""Heilbronn problem for convex regions (AlphaEvolve B.10), OpenEvolve formulation (config.yaml,
initial_program docstring): n points; the region is their convex hull, scaled to unit area. A valid
answer needs a hull of positive area (the points are not all on one line); exact test."""
import math
from fractions import Fraction as F

import numpy as np


def not_all_collinear(c):
    P = np.asarray(c["points"], float)
    if P.ndim != 2 or P.shape[1] != 2 or len(P) < 3 or not np.isfinite(P).all():
        return (False, math.inf)
    Q = [(F(float(x)), F(float(y))) for x, y in P]
    a = Q[0]
    b = next((q for q in Q if q != a), None)
    if b is None:
        return (False, math.inf)
    ok = any((b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0]) != 0 for q in Q)
    return (ok, 0.0 if ok else math.inf)


predicates = {"not_all_collinear": not_all_collinear}


# Record map (spec 6.4): the scorer's combined_score for a construction whose min_area_normalized equals v.
maps = {"score_from_area": lambda v: v / 0.027835571458482138}
