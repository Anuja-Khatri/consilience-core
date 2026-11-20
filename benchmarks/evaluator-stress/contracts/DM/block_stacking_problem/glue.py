"""Glue for block_stacking_problem (n = 20). Independent of the scorer.

The scorer's positions p_0..p_{n-1} (right endpoints, bottom to top, table edge at 0) are the
problem's x_1..x_n (problem 29 puts the table as block 0 centred at x_0 = 0)."""
from fractions import Fraction

import numpy as np


def to_scorer(c):
    return [[float(t) for t in np.asarray(c['x']).ravel()]]


def _nondecreasing(c):
    """0 = x_0 <= x_1 <= ... <= x_n."""
    x = [Fraction(float(t)) for t in np.asarray(c['x'], dtype=float).ravel()]
    prev, worst = Fraction(0), Fraction(0)
    for t in x:
        worst = max(worst, prev - t)
        prev = t
    return worst == 0, float(worst)


def _stable(c):
    """(x_{i+1} + ... + x_n) / (n - i) < x_i + 1/2 for all 0 <= i < n (strict), exactly."""
    x = [Fraction(0)] + [Fraction(float(t)) for t in np.asarray(c['x'], dtype=float).ravel()]
    n = len(x) - 1
    worst = None
    s = Fraction(0)
    for i in range(n - 1, -1, -1):
        s += x[i + 1]
        gap = s / (n - i) - (x[i] + Fraction(1, 2))     # must be < 0
        worst = gap if worst is None else max(worst, gap)
    if worst is None or worst < 0:
        return True, 0.0
    return False, float(worst)


predicates = {'nondecreasing': _nondecreasing, 'stable': _stable}
