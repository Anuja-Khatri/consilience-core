import numpy as np


def to_scorer(c):
    return [np.array(c['X'], dtype=float), 8, 3]
