"""Glue for borcea_conjecture (p = 1). Independent of the scorer."""
import numpy as np


def to_scorer(c):
    return [np.array(c['z'], dtype=complex)]


def _mean_modulus_at_most_one(c):
    """Problem 22 with p = 1: (1/n) sum |z_i| <= 1."""
    z = np.asarray(c['z'], dtype=complex).ravel()
    if z.size == 0:
        return False, float('inf')
    m = float(np.mean(np.abs(z)))
    return (m <= 1.0, max(0.0, m - 1.0))


predicates = {'mean_modulus': _mean_modulus_at_most_one}
