"""Glue for szemeredi_trotter_constructions (n = 100 points, n = 100 lines). Points: the scorer's grid
{0..W-1} x {0..H-1}, W = n // H, plus n - H*W points (0..r-1, H). Lines: integer triples (a, b, c) for
a x + b y = c."""
import math

import numpy as np

N = 100


def to_scorer(c):
    L = [tuple(int(v) for v in row) for row in np.asarray(c['L']).reshape(-1, 3)]
    return [(int(np.asarray(c['H'])), L), N]


def _distinct_lines(c):
    seen = set()
    for row in np.asarray(c['L']).reshape(-1, 3):
        a, b, cc = (int(v) for v in row)
        if a == 0 and b == 0:
            return (False, math.inf)          # not a line
        g = math.gcd(math.gcd(a, b), cc)
        a, b, cc = a // g, b // g, cc // g
        if a < 0 or (a == 0 and b < 0):
            a, b, cc = -a, -b, -cc
        if (a, b, cc) in seen:
            return (False, math.inf)          # the same line twice: fewer than n lines
        seen.add((a, b, cc))
    return (True, 0.0)


predicates = {"n_distinct_lines": _distinct_lines}
