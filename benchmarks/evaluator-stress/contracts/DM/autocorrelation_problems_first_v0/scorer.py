# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/autocorrelation_problems/autocorrelation_problems.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np


def evaluate_sequence(sequence: list[float]) -> float:
  """Evaluates a sequence of coefficients."""
  n = len(sequence)
  b_sequence = np.convolve(sequence, sequence)
  max_b = max(b_sequence)
  sum_a = np.sum(sequence)
  return float(2 * n * max_b / (sum_a**2))
