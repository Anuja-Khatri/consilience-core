"""Glue: roots of a complex polynomial. Independent of the scorer."""
import numpy as np


def to_scorer(c):
    # a fresh complex array (the scorer projects roots in place)
    return [np.array(c['z'], dtype=complex)]
