# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 7b6a34b7b5b13d615dd55800e851080df5c3f92d, experiments/squares_in_square/squares_in_square.ipynb, notebook code cell 2 (0-based over code cells; function(s) evaluate_squares_in_square) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np

def evaluate_squares_in_square(centers: np.ndarray, sides: np.ndarray) -> float:
    if (not np.isfinite(np.asarray(centers, dtype=float)).all()
        or not np.isfinite(np.asarray(sides, dtype=float)).all()
        or np.any(sides <= 0)):
        return -float('inf')
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
