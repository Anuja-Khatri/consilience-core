import numpy as np
def to_scorer(c):
    return [np.asarray(c['B'], float), 3, 2, 2]
