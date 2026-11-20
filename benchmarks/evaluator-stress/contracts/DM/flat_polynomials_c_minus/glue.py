"""Glue for flat_polynomials (n = 50 coefficients). Independent of the scorer."""
import numpy as np


def to_scorer(c):
    return [np.array(c['c'], dtype=float)]
