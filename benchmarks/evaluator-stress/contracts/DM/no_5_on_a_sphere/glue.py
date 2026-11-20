"""Glue for no_5_on_a_sphere (n = 7: grid {0..6}^3 as in the shipped construction_n_7_7_7). The scorer is
a verifier (bool); score = |S| if verified else 0."""
import itertools
import math

import numpy as np


def to_scorer(c):
    return [[tuple(int(v) for v in row) for row in np.asarray(c['S']).reshape(-1, 3)]]


def compose(out, c):
    return float(len(np.asarray(c['S']).reshape(-1, 3))) if out is True else 0.0


def _det(M):
    """Exact determinant of an integer matrix (fraction-free Gaussian elimination, Bareiss)."""
    M = [row[:] for row in M]
    n, sign, prev = len(M), 1, 1
    for k in range(n - 1):
        if M[k][k] == 0:
            for r in range(k + 1, n):
                if M[r][k] != 0:
                    M[k], M[r] = M[r], M[k]
                    sign = -sign
                    break
            else:
                return 0
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                M[i][j] = (M[i][j] * M[k][k] - M[i][k] * M[k][j]) // prev
        prev = M[k][k]
    return sign * M[n - 1][n - 1]


def _no_five_cospherical(c):
    P = [tuple(int(v) for v in row) for row in np.asarray(c['S']).reshape(-1, 3)]
    for five in itertools.combinations(P, 5):
        M = [[x, y, z, x * x + y * y + z * z, 1] for x, y, z in five]
        if _det(M) == 0:     # 5 points on a common sphere or plane
            return (False, math.inf)
    return (True, 0.0)


predicates = {"no_five_cospherical_or_coplanar": _no_five_cospherical}
