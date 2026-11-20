"""Glue for erdos_squares_in_a_square (n = 9). Row i = (x, y, angle_norm, s): centre, rotation angle as a
fraction of a full turn, side length. Valid: every square inside [0,1]^2 and interiors pairwise disjoint.
Axis-parallel squares (angle_norm a multiple of 1/4) are checked in exact rational arithmetic; rotated
squares in floating point (vertex coordinates involve cos/sin)."""
import math
from fractions import Fraction

import numpy as np


def to_scorer(c):
    return [[tuple(float(v) for v in row) for row in np.asarray(c['Q'], dtype=float)], 9]


def _vertices(row):
    x, y, a, s = (float(v) for v in row)
    q = a * 4.0
    if q == int(q):                    # axis-parallel: exact
        X, Y, h = Fraction(x), Fraction(y), Fraction(s) / 2
        return [(X + h, Y + h), (X - h, Y + h), (X - h, Y - h), (X + h, Y - h)], True
    t = a * 2 * math.pi
    c, sn, h = math.cos(t), math.sin(t), s / 2.0
    d1, d2 = (h * c, h * sn), (-h * sn, h * c)
    return [(x + d1[0] + d2[0], y + d1[1] + d2[1]), (x - d1[0] + d2[0], y - d1[1] + d2[1]),
            (x - d1[0] - d2[0], y - d1[1] - d2[1]), (x + d1[0] - d2[0], y + d1[1] - d2[1])], False


def _overlap_depth(V1, V2):
    """Smallest projected overlap over the 4 edge normals (separating axis theorem); <= 0 means disjoint interiors."""
    depth = None
    for V in (V1, V2):
        for i in range(2):
            ex, ey = V[i + 1][0] - V[i][0], V[i + 1][1] - V[i][1]
            ax = (-ey, ex)
            p1 = [v[0] * ax[0] + v[1] * ax[1] for v in V1]
            p2 = [v[0] * ax[0] + v[1] * ax[1] for v in V2]
            ov = min(max(p1), max(p2)) - max(min(p1), min(p2))
            nrm = math.hypot(float(ax[0]), float(ax[1])) or 1.0
            ov = float(ov) / nrm
            depth = ov if depth is None else min(depth, ov)
    return depth


def _packing_valid(c):
    Q = np.asarray(c['Q'], dtype=float)
    worst = 0.0
    polys = []
    for row in Q:
        if float(row[3]) <= 0:
            return (False, math.inf)           # a square needs positive side
        V, _ = _vertices(row)
        polys.append(V)
        for vx, vy in V:
            worst = max(worst, float(-vx), float(vx - 1), float(-vy), float(vy - 1))
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            worst = max(worst, _overlap_depth(polys[i], polys[j]))
    return (worst <= 0.0, max(worst, 0.0))


predicates = {"squares_packed": _packing_valid}
