"""Packing unit regular hexagons in a regular hexagon (AlphaEvolve B.7), OpenEvolve formulation
(README, config.yaml, initial_program docstring): 11 regular hexagons of side 1, each given by
(x, y, angle in degrees), with pairwise disjoint interiors, all inside a regular hexagon given by
(x, y, angle in degrees) and side length s. Vertices are irrational, so the test runs in 60-digit
arithmetic (mpmath); a gap of less than 1e-50 is treated as touching (allowed)."""
import math

import mpmath as mp
import numpy as np

N_HEX = 11
EPS = mp.mpf("1e-50")


def _verts(cx, cy, side, ang_deg):
    a = mp.radians(mp.mpf(float(ang_deg)))
    cx, cy, side = mp.mpf(float(cx)), mp.mpf(float(cy)), mp.mpf(float(side))
    return [(cx + side * mp.cos(a + k * mp.pi / 3), cy + side * mp.sin(a + k * mp.pi / 3)) for k in range(6)]


def _axes(V):
    out = []
    for i in range(6):
        (x1, y1), (x2, y2) = V[i], V[(i + 1) % 6]
        ex, ey = x2 - x1, y2 - y1
        L = mp.sqrt(ex * ex + ey * ey)
        out.append((-ey / L, ex / L))
    return out


def _penetration(V1, V2):
    """Smallest overlap of the projections over all edge normals; <= 0 means disjoint interiors."""
    best = None
    for ax in _axes(V1) + _axes(V2):
        p1 = [x * ax[0] + y * ax[1] for x, y in V1]
        p2 = [x * ax[0] + y * ax[1] for x, y in V2]
        ov = min(max(p1) - min(p2), max(p2) - min(p1))
        best = ov if best is None else min(best, ov)
    return best


def packing(c):
    inner = np.asarray(c["inner"], float)
    outer = np.asarray(c["outer"], float)
    s = np.asarray(c["side"], float)
    if inner.shape != (N_HEX, 3) or outer.shape != (3,) or s.shape != () or \
            not (np.isfinite(inner).all() and np.isfinite(outer).all() and np.isfinite(s)) or float(s) <= 0:
        return (False, math.inf)
    with mp.workdps(60):
        hexes = [_verts(x, y, 1, a) for x, y, a in inner]
        O = _verts(outer[0], outer[1], float(s), outer[2])
        worst = mp.mpf(0)
        for i in range(N_HEX):
            for j in range(i + 1, N_HEX):
                pen = _penetration(hexes[i], hexes[j])
                if pen > EPS:
                    worst = max(worst, pen)
        # containment: every inner vertex on the inner side of every outer edge (outer vertices are CCW)
        for k in range(6):
            (x1, y1), (x2, y2) = O[k], O[(k + 1) % 6]
            ex, ey = x2 - x1, y2 - y1
            L = mp.sqrt(ex * ex + ey * ey)
            for V in hexes:
                for px, py in V:
                    out = -(ex * (py - y1) - ey * (px - x1)) / L
                    if out > EPS:
                        worst = max(worst, out)
        return (worst == 0, float(worst))


predicates = {"packing": packing}
