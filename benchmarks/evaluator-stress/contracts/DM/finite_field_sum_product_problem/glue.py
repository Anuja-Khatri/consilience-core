import numpy as np

P = 1000033  # prime, P = 1 mod 4 (the notebook's prompt fixes p = 1 mod 4); |X| = floor(sqrt(P)) = 1000


def to_scorer(c):
    return [np.ascontiguousarray(np.asarray(c['X']).ravel(), dtype=np.int64), P]
