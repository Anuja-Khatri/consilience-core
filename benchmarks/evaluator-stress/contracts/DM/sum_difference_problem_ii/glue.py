import numpy as np


def to_scorer(c):
    return [[int(v) for v in np.asarray(c['A']).ravel()]]
