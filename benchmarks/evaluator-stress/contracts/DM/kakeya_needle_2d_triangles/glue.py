"""Glue for kakeya_needle_2d, triangles (n = 32). Independent of the scorer.

Builds T_j with vertices (x_j, 0), (x_j + 1/n, 0), (x_j + j/n, 1) (problem 9), the same list the
notebook's get_all_triangle_vertices builds, and passes it to get_score_shapely."""
import numpy as np


def to_scorer(c):
    x = [float(t) for t in np.asarray(c['x']).ravel()]
    n = len(x)
    return [[[(x[j - 1], 0), (x[j - 1] + 1 / n, 0), (x[j - 1] + j / n, 1)] for j in range(1, n + 1)]]
