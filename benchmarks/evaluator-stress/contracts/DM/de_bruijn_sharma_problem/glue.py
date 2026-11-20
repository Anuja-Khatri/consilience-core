"""Glue for de_bruijn_sharma_problem (n = 5). Independent of the scorer."""
import numpy as np

N = 5   # degree; evaluate(params) takes n as a parameter, fixed here


def to_scorer(c):
    P = np.asarray(c['P'], dtype=complex)
    return [[np.array(row, dtype=complex) for row in P.reshape(P.shape[0], -1)], N]


def _degree_n(c):
    P = np.asarray(c['P'])
    ok = P.ndim == 2 and P.shape[1] == N
    return ok, 0.0 if ok else float('inf')


def _roots_sum_to_zero(c):
    """Problem 24: each polynomial's zeros sum to zero."""
    P = np.asarray(c['P'], dtype=complex)
    if P.ndim != 2:
        return False, float('inf')
    worst = float(np.max(np.abs(P.sum(axis=1)))) if P.size else 0.0
    return worst == 0.0, worst


predicates = {'degree_n': _degree_n, 'roots_sum_to_zero': _roots_sum_to_zero}
