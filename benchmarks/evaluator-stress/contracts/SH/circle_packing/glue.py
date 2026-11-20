import numpy as np

def sum_radii(c):
    """The claimed sum, recomputed from the construction."""
    return float(np.sum(np.asarray(c["radii"], float)))

quantities = {"sum_radii": sum_radii}
