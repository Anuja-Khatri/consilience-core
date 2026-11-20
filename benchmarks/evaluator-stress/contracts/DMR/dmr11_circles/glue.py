import numpy as np

def to_scorer(c):
    """The notebook's (num_circles, 3) array of (x, y, radius)."""
    return [np.column_stack([np.asarray(c["centers"], float), np.asarray(c["radii"], float)])]

def compose(out, c):
    """Notebook cell 119: verify_circles raises on failure; otherwise the score is the sum of radii."""
    return float(np.sum(np.asarray(c["radii"], float)))
