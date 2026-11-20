"""Glue for erdos_discrepancy_problem. The candidate is the list [a_0, a_1, ..., a_N] of +-1 entries;
index i holds a_i, and a_0 is a placeholder the scorer drops (as in the notebook's initial program)."""
import numpy as np


def to_scorer(c):
    return [[int(v) for v in np.asarray(c['a']).ravel()]]
