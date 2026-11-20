"""Glue for packing_circles_max_sum_of_radii, unit square, n = 26. Independent of the scorer."""
import numpy as np

N = 26


def to_scorer(c):
    return [np.array(c['centers'], dtype=float), np.array(c['radii'], dtype=float), N]
