"""Glue for packing_unit_cubes (n = 11). Independent of the scorer.

A row is (x, y, z, x_angle, y_angle, z_angle), angles in degrees, rotation R = Rz Ry Rx (the
convention stated in the notebook's data cell)."""
import itertools

import numpy as np

N = 11


def to_scorer(c):
    return [[tuple(float(t) for t in row) for row in np.asarray(c['P'], dtype=float)], N]


def _rot(ax, ay, az):
    x, y, z = np.deg2rad([ax, ay, az])
    rx = np.array([[1, 0, 0], [0, np.cos(x), -np.sin(x)], [0, np.sin(x), np.cos(x)]])
    ry = np.array([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    rz = np.array([[np.cos(z), -np.sin(z), 0], [np.sin(z), np.cos(z), 0], [0, 0, 1]])
    return rz @ ry @ rx


_LOCAL = np.array(list(itertools.product([-0.5, 0.5], repeat=3)))


def _penetration(R1, c1, R2, c2):
    """Separating-axis test for two unit cubes; returns the smallest overlap over the 15 axes
    (<= 0 means the interiors are disjoint)."""
    v1, v2 = _LOCAL @ R1.T + c1, _LOCAL @ R2.T + c2
    axes = [R1[:, i] for i in range(3)] + [R2[:, i] for i in range(3)]
    for i in range(3):
        for j in range(3):
            cr = np.cross(R1[:, i], R2[:, j])
            nr = np.linalg.norm(cr)
            if nr > 1e-12:
                axes.append(cr / nr)
    depth = np.inf
    for a in axes:
        p1, p2 = v1 @ a, v2 @ a
        depth = min(depth, min(p1.max(), p2.max()) - max(p1.min(), p2.min()))
    return depth


def _disjoint_interiors(c):
    """Problem 35: the n unit cubes have pairwise disjoint interiors."""
    P = np.asarray(c['P'], dtype=float)
    if P.ndim != 2 or P.shape[1] != 6:
        return False, float('inf')
    Rs = [_rot(*p[3:]) for p in P]
    worst = 0.0
    for i, j in itertools.combinations(range(len(P)), 2):
        worst = max(worst, _penetration(Rs[i], P[i, :3], Rs[j], P[j, :3]))
    return worst <= 0.0, worst


predicates = {'disjoint_interiors': _disjoint_interiors}
