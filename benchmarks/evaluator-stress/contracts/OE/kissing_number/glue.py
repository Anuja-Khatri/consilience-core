"""Kissing configuration in dimension 11 (AlphaEvolve B.11), OpenEvolve formulation (config.yaml,
initial_program docstring): a set S of points in Z^11, 0 not in S, with
max_i |p_i| <= min_{i != j} |p_i - p_j|. Exact integer arithmetic."""
import math

import numpy as np


def kissing_config(c):
    A = np.asarray(c["points"], float)
    if A.ndim != 2 or A.shape[1] != 11 or len(A) == 0 or not np.isfinite(A).all():
        return (False, math.inf)
    # Fractional entries are the 'integral' rule's business (a type violation); the geometric
    # condition is judged on the nearest integer points, so that it does not double-report them.
    P = [tuple(int(v) for v in row) for row in np.round(A)]
    norms = [sum(v * v for v in p) for p in P]
    if min(norms) == 0:
        return (False, math.inf)
    mx = max(norms)
    if len(P) == 1:
        return (True, 0.0)
    M = np.array(P, dtype=object)
    worst = 0
    for i in range(len(P) - 1):
        d2 = ((M[i + 1:] - M[i]) ** 2).sum(axis=1)
        md = int(min(d2))
        if md < mx:
            worst = max(worst, mx - md)
    return (worst == 0, float(math.sqrt(mx) - math.sqrt(mx - worst)) if worst else 0.0)


predicates = {"kissing_config": kissing_config}
