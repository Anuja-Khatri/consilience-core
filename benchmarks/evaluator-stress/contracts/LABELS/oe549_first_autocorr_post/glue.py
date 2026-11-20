import numpy as np
def c1_of(c):
    f = np.asarray(c["f"], float); n = len(f); dx = 0.5 / n
    return float(np.max(np.convolve(f, f) * dx) / ((f.sum() * dx) ** 2))
def c3_of(c):
    f = np.asarray(c["f"], float); n = len(f); dx = 0.5 / n
    return float(np.max(np.abs(np.convolve(f, f) * dx)) / ((f.sum() * dx) ** 2))
quantities = {"c1": c1_of, "c3": c3_of}
