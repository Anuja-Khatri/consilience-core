"""Glue for kissing_cylinders. X[i] = (p_i, v_i): v_i the unit axis direction of cylinder i and p_i the
point of its axis closest to the origin (p_i . v_i = 0), the input convention of the notebook."""
from fractions import Fraction

import numpy as np


def to_scorer(c):
    X = np.asarray(c['X'], dtype=np.float64)
    return [[(np.ascontiguousarray(p, dtype=np.float64), np.ascontiguousarray(v, dtype=np.float64)) for p, v in X]]


def _F(t):
    return Fraction(float(t))


def _unit_directions(c):
    X = np.asarray(c['X'], dtype=float)
    worst = max(abs(float(sum(_F(t) * _F(t) for t in v)) ** 0.5 - 1.0) for _, v in X)
    return (worst == 0.0, worst)


def _standardized(c):
    X = np.asarray(c['X'], dtype=float)
    worst = max(abs(float(sum(_F(a) * _F(b) for a, b in zip(p, v)))) for p, v in X)
    return (worst == 0.0, worst)


predicates = {"unit_directions": _unit_directions, "standardized_points": _standardized}
