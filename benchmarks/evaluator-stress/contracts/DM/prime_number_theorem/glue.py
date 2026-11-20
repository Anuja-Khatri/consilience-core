"""Glue for prime_number_theorem (Chebyshev-type partial functions). Independent of the scorer."""
import math
from functools import reduce

import numpy as np

LCM_CAP = 10_000_000   # the predicate checks one full period exactly; larger periods cannot be judged


def to_scorer(c):
    keys = [int(k) for k in np.asarray(c['k']).ravel()]
    vals = [float(v) for v in np.asarray(c['v']).ravel()]
    return [dict(zip(keys, vals)), 10_000_000]   # evaluate() uses num_samples = 10_000_000 (prompt)


def _same_length(c):
    ok = np.asarray(c['k']).shape == np.asarray(c['v']).shape and np.asarray(c['k']).ndim == 1
    return ok, 0.0 if ok else float('inf')


def _chebyshev_condition(c):
    """With a_1 chosen so that sum a_k / k = 0, F(x) = sum_k a_k floor(x/k) <= 1 for every real x >= 1.
    F is constant on [m, m+1) and periodic with period lcm(keys), so one period of integers decides it."""
    k = np.asarray(c['k'], dtype=float).ravel()
    v = np.asarray(c['v'], dtype=float).ravel()
    if k.shape != v.shape or not np.all(np.isfinite(k)) or not np.all(np.isfinite(v)) \
            or not np.all(k == np.round(k)) or np.any(k < 1) or len(set(k.tolist())) != len(k):
        return False, float('inf')
    a = dict(zip(k.astype(np.int64).tolist(), v.tolist()))
    total = sum(val / key for key, val in a.items())
    a[1] = a.get(1, 0.0) - total
    L = reduce(lambda x, y: x * y // math.gcd(x, y), a.keys(), 1)
    if L > LCM_CAP:
        raise ValueError('period too long to check exactly')
    x = np.arange(1, L + 1, dtype=np.int64)
    F = np.zeros(L)
    for key, val in a.items():
        F += val * (x // key)
    worst = float(np.max(F) - 1.0)
    return worst <= 0.0, max(0.0, worst)


predicates = {'same_length': _same_length, 'chebyshev_condition': _chebyshev_condition}
