# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/autocorrelation_problems/problem_6.ipynb, notebook code cells 2 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np


def evaluate_autocorrelation(heights: list[float]) -> float:
    n = len(heights)
    if n == 0: return -1.0
    h = np.array(heights, dtype=float)
    if np.any(h < 0): return -1.0
    l1 = np.sum(h)
    if l1 == 0: return -1.0
    f = np.repeat(h, 100)
    autocorr = np.correlate(f, f, mode='full')
    valid = autocorr[len(f)-1:] / 100.0
    return -np.max(valid[1:]) / (l1**2) # Minimize peak off-center autocorrelation
