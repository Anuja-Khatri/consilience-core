"""Glue for kakeya_needle_2d, parallelograms (n = 32). Independent of the scorer.

Builds P_j with vertices (x_j, 0), (x_j + 1/n, 0), (x_j + (j+1)/n, 1), (x_j + j/n, 1) (problem 9),
split into two triangles exactly as the notebook's get_all_parallelogram_vertices does, and passes
the list to get_score_shapely."""
import numpy as np


def to_scorer(c):
    x = [float(t) for t in np.asarray(c['x']).ravel()]
    n = len(x)
    d = 1 / n
    tris = []
    for j in range(1, n + 1):
        xi, a = x[j - 1], j / n
        tris.append([(xi, 0), (xi + d, 0), (xi + a, 1)])
        tris.append([(xi + d, 0), (xi + a + d, 1), (xi + a, 1)])
    return [tris]
