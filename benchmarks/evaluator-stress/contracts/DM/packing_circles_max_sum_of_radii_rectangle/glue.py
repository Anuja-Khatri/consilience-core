"""Glue for packing_circles_max_sum_of_radii, rectangle of perimeter 4, n = 21. Independent of the scorer."""
from fractions import Fraction

import numpy as np

N = 21


def to_scorer(c):
    return [np.array(c['centers'], dtype=float), np.array(c['radii'], dtype=float), N,
            float(c['width']), float(c['height'])]


def _perimeter_4(c):
    w, h = float(c['width']), float(c['height'])
    if not (np.isfinite(w) and np.isfinite(h)):
        return False, float('inf')
    d = abs(2 * (Fraction(w) + Fraction(h)) - 4)
    return d == 0, float(d)


def _inside_rectangle(c):
    """Every disk lies in [0, width] x [0, height] (exact)."""
    w, h = Fraction(float(c['width'])), Fraction(float(c['height']))
    worst = Fraction(0)
    for p, r in zip(np.asarray(c['centers'], dtype=float), np.asarray(c['radii'], dtype=float)):
        x, y, R = Fraction(float(p[0])), Fraction(float(p[1])), Fraction(float(r))
        worst = max(worst, R - x, R - y, x + R - w, y + R - h)
    return worst <= 0, float(max(worst, Fraction(0)))


predicates = {'perimeter_4': _perimeter_4, 'inside_rectangle': _inside_rectangle}
