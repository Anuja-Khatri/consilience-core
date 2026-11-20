"""Glue for ring_loading_problem (m = 15, the shipped solution's length). Row i = (u_i, v_i)."""
import math
from fractions import Fraction

import numpy as np


def to_scorer(c):
    return [[(float(u), float(v)) for u, v in np.asarray(c['X'], dtype=float)], 15]


def _sum_at_most_one(c):
    worst = max(Fraction(float(u)) + Fraction(float(v)) - 1 for u, v in np.asarray(c['X'], dtype=float))
    return (worst <= 0, max(0.0, float(worst)))


predicates = {"u_plus_v_at_most_1": _sum_at_most_one}
