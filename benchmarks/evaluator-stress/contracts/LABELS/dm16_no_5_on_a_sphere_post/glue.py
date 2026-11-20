import itertools, math
from fractions import Fraction as F
import numpy as np

def _det(M):
    """Exact determinant (Bareiss fraction-free elimination; exact for ints and Fractions)."""
    M = [list(row) for row in M]
    n, sign, prev = len(M), 1, 1
    for k in range(n - 1):
        if M[k][k] == 0:
            p = next((r for r in range(k + 1, n) if M[r][k] != 0), None)
            if p is None:
                return 0
            M[k], M[p] = M[p], M[k]
            sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                v = M[i][j] * M[k][k] - M[i][k] * M[k][j]
                M[i][j] = v // prev if isinstance(v, int) and isinstance(prev, int) else v / prev
        prev = M[k][k]
    return sign * M[n - 1][n - 1]

def no_five_cospherical(P):
    """No 5 of the points on a common sphere or plane: every 5x5 lifted determinant is nonzero (exact)."""
    A = np.asarray(P, float)
    if A.ndim != 2 or A.shape[1] != 3 or not np.isfinite(A).all():
        return (False, math.inf)
    if np.all(A == np.round(A)):
        Q = [tuple(int(v) for v in p) for p in A]          # integers: exact and fast
    else:
        Q = [tuple(F(float(v)) for v in p) for p in A]
    for five in itertools.combinations(Q, 5):
        if _det([[x, y, z, x * x + y * y + z * z, 1] for x, y, z in five]) == 0:
            return (False, math.inf)
    return (True, 0.0)

def _num(v):
    f = float(v)
    return int(f) if f.is_integer() else f

def to_scorer(c):
    """A list of (x, y, z) tuples, as in the notebook's data cell (Python ints where integral)."""
    return [[tuple(_num(v) for v in p) for p in np.asarray(c["P"]).reshape(-1, 3)]]

def compose(out, c):
    """Score = number of points if the verifier returns True."""
    return float(len(np.asarray(c["P"]).reshape(-1, 3))) if out is True else -1.0

def no5(c):
    A = np.asarray(c["P"])
    if A.ndim != 2 or A.shape[1] != 3:
        return (False, math.inf)
    return no_five_cospherical(A)

predicates = {"no5": no5}
