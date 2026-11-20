import itertools, math
import numpy as np

def kissing(c):
    """README conditions 1-2 in dimension 11, exact on integers."""
    A = np.asarray(c["C"])
    if A.ndim != 2 or A.shape[1] != 11:
        return (False, math.inf)
    return kissing_config(A)

def kissing_config(C):
    """Integer vectors, none zero, min pairwise squared distance >= max squared norm (exact)."""
    A = np.asarray(C)
    if A.ndim != 2 or A.shape[0] < 1:
        return (False, math.inf)
    Af = A.astype(float)
    if not np.isfinite(Af).all() or not np.all(Af == np.round(Af)):
        return (False, math.inf)
    V = [[int(v) for v in row] for row in A.astype(object).tolist()] if A.dtype.kind in "iu" else \
        [[int(round(float(v))) for v in row] for row in Af.tolist()]
    norms = [sum(v * v for v in row) for row in V]
    if min(norms) == 0:
        return (False, math.inf)
    mx = max(norms)
    worst = 0
    for a, b in itertools.combinations(V, 2):
        d = sum((x - y) * (x - y) for x, y in zip(a, b))
        if d < mx:
            worst = max(worst, mx - d)
    return (worst == 0, float(worst) / float(mx))

def ratio(v):
    """benchmark_ratio = num_points / 593 (BENCHMARK copied from the README)."""
    return v / 593

predicates = {"kissing": kissing}
maps = {"ratio": ratio}
