"""Glue for sidorenko_conjecture. Independent of the scorer."""
import numpy as np


def to_scorer(c):
    return [np.array(c['W'], dtype=np.float64)]


def _symmetric(c):
    """Problem 26: a graphon is symmetric; a step graphon's matrix must be symmetric."""
    W = np.asarray(c['W'], dtype=float)
    if W.ndim != 2 or W.shape[0] != W.shape[1]:
        return False, float('inf')
    d = float(np.max(np.abs(W - W.T))) if W.size else 0.0
    return d == 0.0, d


predicates = {'symmetric': _symmetric}
