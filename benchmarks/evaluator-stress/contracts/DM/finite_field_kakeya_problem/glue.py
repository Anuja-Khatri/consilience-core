"""Glue for finite_field_kakeya_problem (p=7, d=3). Independent of the scorer."""
import itertools
import numpy as np

P, DIM = 7, 3


def to_scorer(c):
    return [np.asarray(c['K']), P, DIM]


def _directions(p, d):
    # one representative per projective direction: first nonzero coordinate equal to 1
    for v in itertools.product(range(p), repeat=d):
        nz = [x for x in v if x != 0]
        if nz and nz[0] == 1:
            yield np.array(v, dtype=np.int64)


def _kakeya(c):
    """Problem 1: K contains a full line {x + t v : t in F_p} in every direction v."""
    K = np.asarray(c['K'], dtype=float)
    if K.ndim != 2 or K.shape[1] != DIM:
        return False, float('inf')
    pts = {tuple(int(t) for t in row) for row in K
           if np.all(np.isfinite(row)) and np.all(row == np.round(row)) and np.all((row >= 0) & (row < P))}
    missing = 0
    for v in _directions(P, DIM):
        ok = any(all(tuple(int(t) for t in (np.array(x) + s * v) % P) in pts for s in range(P)) for x in pts)
        missing += 0 if ok else 1
    return missing == 0, float('inf') if missing else 0.0


predicates = {'kakeya': _kakeya}
