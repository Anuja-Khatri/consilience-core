"""Glue for furstenberg_sarkozy_problem (k = 2, subsets of Z/mZ). Independent of the scorer."""
import math

import numpy as np


def to_scorer(c):
    return [[int(t) for t in np.asarray(c['A']).ravel()], int(c['m'])]


def _square_free_modulus(c):
    m = float(c['m'])
    if not (math.isfinite(m) and m == round(m) and m >= 2):
        return False, float('inf')
    m = int(m)
    ok = all(m % (d * d) for d in range(2, math.isqrt(m) + 1))
    return ok, 0.0 if ok else float('inf')


def _distinct_mod_m(c):
    m = int(c['m'])
    A = [int(t) for t in np.asarray(c['A'], dtype=float).ravel()]
    ok = len({a % m for a in A}) == len(A)
    return ok, 0.0 if ok else float('inf')


def _no_square_difference(c):
    """Problem 31 (k = 2): no two elements of A differ by a nonzero square residue modulo m."""
    m = int(c['m'])
    A = sorted({int(t) % m for t in np.asarray(c['A'], dtype=float).ravel()})
    squares = {pow(y, 2, m) for y in range(1, m)} - {0}
    bad = sum(1 for i in A for j in A if i != j and (i - j) % m in squares)
    return bad == 0, 0.0 if bad == 0 else float('inf')


def _score_from_size_mod_205(size):
    return 0.5 + math.log(size) / (2 * math.log(205))


predicates = {'square_free_modulus': _square_free_modulus, 'distinct_mod_m': _distinct_mod_m,
              'no_square_difference': _no_square_difference}
maps = {'score_from_size_mod_205': _score_from_size_mod_205}
