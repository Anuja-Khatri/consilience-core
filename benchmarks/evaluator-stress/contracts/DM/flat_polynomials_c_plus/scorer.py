# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/flat_polynomials/flat_polynomials.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np


def get_c_plus_score(coefficients: np.ndarray) -> float:
  poly_fn = np.poly1d(coefficients)
  n = len(coefficients)
  int_fn = lambda z: np.abs(poly_fn(z))

  num_points = 1000000
  zs = np.exp(1j * np.linspace(0, 2 * np.pi, num_points))
  int_val = np.max(int_fn(zs))
  return int_val / np.sqrt(n + 1)
