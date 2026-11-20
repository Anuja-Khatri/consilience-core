"""Glue for spherical_t_designs (d = 2, t = 15, N = 120). Independent of the scorer."""
import numpy as np

D_SPHERE, T, N = 2, 15, 120


def to_scorer(c):
    return [np.array(c['X'], dtype=np.float64), D_SPHERE, T, N]
