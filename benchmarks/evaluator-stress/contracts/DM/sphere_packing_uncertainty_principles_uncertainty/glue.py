"""Glue for sphere_packing_uncertainty_principles, uncertainty part (problem 11). Independent of the scorer."""
import math

import numpy as np


def to_scorer(c):
    return [[float(t) for t in np.asarray(c['z']).ravel()]]


def _positive(c):
    z = np.asarray(c['z'], dtype=float).ravel()
    worst = float(max(0.0, -z.min())) if z.size else float('inf')
    ok = bool(z.size) and bool(np.all(z > 0))
    return ok, (worst if worst > 0 else (0.0 if ok else float('inf')))


def _score_from_C(C):
    # the notebook reads get_score(z)**2 as the upper bound on the constant C
    return -math.sqrt(C)


predicates = {'positive': _positive}
maps = {'score_from_C': _score_from_C}
