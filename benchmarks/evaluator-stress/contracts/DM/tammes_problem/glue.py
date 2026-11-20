"""Glue for tammes_problem (N = 12). Independent of the scorer."""
import numpy as np


def to_scorer(c):
    return [np.array(c['X'], dtype=np.float64)]
