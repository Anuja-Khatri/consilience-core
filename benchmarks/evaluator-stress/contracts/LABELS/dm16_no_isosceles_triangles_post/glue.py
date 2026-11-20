import itertools, math
from fractions import Fraction as F
import numpy as np

def no_isosceles(P):
    """No three distinct points a, b, c with |ab| = |bc| (includes flat/degenerate cases) (exact)."""
    A = np.asarray(P, float)
    if A.ndim != 2 or A.shape[1] != 2 or not np.isfinite(A).all():
        return (False, math.inf)
    Q = [(F(float(x)), F(float(y))) for x, y in A]
    for b in range(len(Q)):
        seen = set()
        for a in range(len(Q)):
            if a == b:
                continue
            d = (Q[a][0] - Q[b][0]) ** 2 + (Q[a][1] - Q[b][1]) ** 2
            if d in seen:
                return (False, math.inf)
            seen.add(d)
    return (True, 0.0)

def _num(v):
    f = float(v)
    return int(f) if f.is_integer() else f

def to_scorer(c):
    """A list of (x, y) tuples, as in the notebook's data cell (Python ints where integral)."""
    return [[tuple(_num(v) for v in p) for p in np.asarray(c["P"]).reshape(-1, 2)]]

def compose(out, c):
    """Score = number of points if the verifier returns True."""
    return float(len(np.asarray(c["P"]).reshape(-1, 2))) if out is True else -1.0

def iso(c):
    A = np.asarray(c["P"])
    if A.ndim != 2 or A.shape[1] != 2:
        return (False, math.inf)
    return no_isosceles(A)

predicates = {"iso": iso}
