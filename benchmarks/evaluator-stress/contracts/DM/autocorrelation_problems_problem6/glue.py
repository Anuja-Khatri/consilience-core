"""Glue for problem_6.ipynb (autocorrelation related to difference bases). Independent of the scorer."""
import numpy as np


def to_scorer(c):
    return [[float(x) for x in np.asarray(c['h']).ravel()]]


def _positive_mass(c):
    h = np.asarray(c['h'], dtype=float)
    s = float(np.sum(h)) if h.size else 0.0
    return (s > 0, 0.0 if s > 0 else float('inf'))


predicates = {'positive_mass': _positive_mass}
