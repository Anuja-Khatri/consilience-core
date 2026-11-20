"""Glue for finite_field_nikodym_problem (p=5, d=3). Independent of the scorer."""
import itertools
import numpy as np

P, DIM = 5, 3
def to_scorer(c):
    return [np.asarray(c['N']), P, DIM]


def _directions(p, d):
    for v in itertools.product(range(p), repeat=d):
        nz = [x for x in v if x != 0]
        if nz and nz[0] == 1:
            yield np.array(v, dtype=np.int64)


def _nikodym(c):
    """Problem 1: every x in F_p^d lies on a line l with l minus {x} contained in N."""
    N = np.asarray(c['N'], dtype=float)
    if N.ndim != 2 or N.shape[1] != DIM:
        return False, float('inf')
    pts = {tuple(int(t) for t in row) for row in N
           if np.all(np.isfinite(row)) and np.all(row == np.round(row)) and np.all((row >= 0) & (row < P))}
    dirs = list(_directions(P, DIM))
    bad = 0
    for x in itertools.product(range(P), repeat=DIM):
        x = np.array(x, dtype=np.int64)
        if not any(all(tuple(int(t) for t in (x + s * v) % P) in pts for s in range(1, P)) for v in dirs):
            bad += 1
    return bad == 0, float('inf') if bad else 0.0


predicates = {'nikodym': _nikodym}
