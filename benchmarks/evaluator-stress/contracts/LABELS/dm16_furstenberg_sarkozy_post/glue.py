import itertools, math
import numpy as np

def sarkozy_free(S, m, k):
    """No two distinct elements whose difference (either order, mod m) is x^k mod m for some x in 1..m-1."""
    A = np.asarray(S, float).ravel()
    if not np.isfinite(A).all() or not np.all(A == np.round(A)):
        return (False, math.inf)
    V = [int(v) for v in A]
    powers = set(pow(x, k, m) for x in range(1, m))
    for i, j in itertools.combinations(range(len(V)), 2):
        if (V[i] - V[j]) % m in powers or (V[j] - V[i]) % m in powers:
            return (False, math.inf)
    return (True, 0.0)

def _num(v):
    f = float(v)
    return int(f) if f.is_integer() else f

def to_scorer(c):
    """check_sarkozy_subset(m, subset, power) with m = 205, power = 2."""
    return [205, [_num(v) for v in np.asarray(c["S"]).ravel()], 2]

def compose(out, c):
    """Score = subset size if the checker returns True."""
    return float(np.asarray(c["S"]).size) if out is True else -1.0

predicates = {"sarkozy": lambda c: sarkozy_free(c["S"], 205, 2)}
