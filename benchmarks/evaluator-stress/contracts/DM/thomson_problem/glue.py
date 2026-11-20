"""Glue for thomson_problem (N = 282). Independent of the scorer."""
import numpy as np


def to_scorer(c):
    return [np.array(c['X'], dtype=np.float64)]
