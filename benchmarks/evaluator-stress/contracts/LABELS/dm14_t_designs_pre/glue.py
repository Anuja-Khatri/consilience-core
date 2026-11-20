import numpy as np

def to_scorer(c):
    """calculate_design_score(points, d, t, N) for the (d, t, N) = (2, 15, 120) design."""
    return [np.asarray(c["X"], float), 2, 15, 120]
