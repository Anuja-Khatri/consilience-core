"""Glue for subsets_of_the_grid_with_no_isosceles_triangles (64 x 64 grid, coordinates 0..63 as in the
shipped sol_64). The scorer is a verifier (bool); the score is |S| if it verifies, else 0."""
import math

import numpy as np


def to_scorer(c):
    return [[tuple(int(v) for v in row) for row in np.asarray(c['S']).reshape(-1, 2)]]


def compose(out, c):
    return float(len(np.asarray(c['S']).reshape(-1, 2))) if out is True else 0.0


def _no_isosceles(c):
    P = [tuple(int(v) for v in row) for row in np.asarray(c['S']).reshape(-1, 2)]
    for b in P:   # a, b, c distinct with |a-b| = |b-c|: two other points at the same distance from b
        seen = set()
        for a in P:
            if a == b:
                continue
            d = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
            if d in seen:
                return (False, math.inf)
            seen.add(d)
    return (True, 0.0)


predicates = {"no_isosceles": _no_isosceles}
