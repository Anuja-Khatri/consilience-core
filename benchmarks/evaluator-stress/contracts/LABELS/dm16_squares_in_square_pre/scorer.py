# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/squares_in_square/squares_in_square.ipynb, notebook code cell 2 (0-based over code cells; function(s) evaluate_squares_in_square) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np

def evaluate_squares_in_square(centers: np.ndarray, sides: np.ndarray) -> float:
    n = len(sides)
    # Boundary check
    for i in range(n):
        x, y = centers[i]
        s = sides[i]
        if x - s/2 < -1e-7 or x + s/2 > 1.0 + 1e-7 or y - s/2 < -1e-7 or y + s/2 > 1.0 + 1e-7:
            return -float('inf')
    # Disjointness check
    for i in range(n):
        for j in range(i+1, n):
            xi, yi = centers[i]
            xj, yj = centers[j]
            si, sj = sides[i], sides[j]
            if abs(xi - xj) < (si + sj)/2 - 1e-7 and abs(yi - yj) < (si + sj)/2 - 1e-7:
                return -float('inf')
    return np.sum(sides)
