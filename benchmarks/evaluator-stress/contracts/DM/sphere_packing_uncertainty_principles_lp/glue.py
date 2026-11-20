"""Glue for sphere_packing_uncertainty_principles, LP sphere-packing part (m = 6, n = 25). Independent of the scorer."""
import numpy as np

M, N_DIM = 6, 25


def to_scorer(c):
    return [M, N_DIM, [float(t) for t in np.asarray(c['z']).ravel()]]


def _positive(c):
    z = np.asarray(c['z'], dtype=float).ravel()
    ok = bool(z.size) and bool(np.all(z > 0))
    worst = float(max(0.0, -z.min())) if z.size else float('inf')
    return ok, (worst if worst > 0 else (0.0 if ok else float('inf')))


predicates = {'positive': _positive}
