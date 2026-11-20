"""Glue for crouzeix_conjecture. Independent of the scorer."""
import numpy as np

THETA = 10000   # evaluate() calls evaluate_construction(..., num_theta_points=10000)


def to_scorer(c):
    return [np.array(c['A'], dtype=np.complex128), list(np.asarray(c['p'], dtype=complex)), THETA]


def _square(c):
    A = np.asarray(c['A'])
    ok = A.ndim == 2 and A.shape[0] == A.shape[1] and A.shape[0] >= 1
    return ok, 0.0 if ok else float('inf')


def _nonzero_polynomial(c):
    p = np.asarray(c['p'], dtype=complex)
    ok = p.size > 0 and bool(np.any(p != 0))
    return ok, 0.0 if ok else float('inf')


predicates = {'square': _square, 'nonzero_polynomial': _nonzero_polynomial}
