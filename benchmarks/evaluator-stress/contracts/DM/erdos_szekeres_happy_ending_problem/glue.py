import numpy as np


def to_scorer(c):
    return [np.asarray(c['P'], dtype=np.float64), 7]
