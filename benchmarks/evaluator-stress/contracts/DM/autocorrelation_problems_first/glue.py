"""Glue for the first autocorrelation inequality (problem 2). Independent of the scorer."""
import numpy as np


def to_scorer(c):
    # the notebook passes a Python list of floats (the shipped constructions are lists)
    return [[float(x) for x in np.asarray(c['a']).ravel()]]


def _positive_mass(c):
    # a non-negative step function with integral 0 is f = 0, for which the ratio is undefined
    a = np.asarray(c['a'], dtype=float)
    s = float(np.sum(a)) if a.size else 0.0
    return (s > 0, 0.0 if s > 0 else float('inf'))


predicates = {'positive_mass': _positive_mass}
