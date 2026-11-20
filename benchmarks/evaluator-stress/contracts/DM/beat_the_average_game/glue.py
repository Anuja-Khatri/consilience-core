"""Glue for beat_the_average_game. The candidate is a vector of non-negative weights of a
probability measure on {0, 1, ..., L-1} (L = 20000); the measure is the normalised weight vector."""
import math
from fractions import Fraction

import numpy as np

L = 20000


def to_scorer(c):
    return [np.array(c['w'], dtype=np.float64, copy=True), L]


def _positive_mass(c):
    # a probability measure needs positive total mass (exact sum of the weights)
    s = sum(Fraction(float(v)) for v in np.asarray(c['w'], dtype=float).ravel())
    return (s > 0, 0.0 if s > 0 else math.inf)


predicates = {"positive_mass": _positive_mass}
