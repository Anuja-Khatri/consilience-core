# Vendored verbatim from google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8 (Apache-2.0).
"""Vendored verbatim from google-deepmind/alphaevolve_repository_of_problems @ 8f44745 (Apache-2.0),
notebook matrix_multiplication_amgm.ipynb, code cell [0]. Only the scoring functions are copied; imports added."""
import numpy as np, itertools, math
from typing import List, Tuple

def get_score(b_matrices: np.ndarray, n: int, m: int, d: int) -> float:
  """Calculates the score for a given set of matrices to test the AM-GM conjecture.

  The score is defined as RHS - LHS of the inequality. A positive score
  indicates a counterexample has been found.
  """
  if not isinstance(b_matrices, np.ndarray) or b_matrices.shape != (n, d, d):
    return -1_000_000.0

  b_matrices = np.clip(b_matrices, -1000.0, 1000.0)
  if np.isnan(b_matrices).any() or np.isinf(b_matrices).any():
    return -1_000_000.0

  try:
    matrices_A = [b @ b.conj().T for b in b_matrices]
  except ValueError:
    return -1_000_000.0

  # Calculate the Left-Hand Side (LHS) of the inequality
  sum_all_norms = 0.0
  for indices in itertools.product(range(n), repeat=m):
    try:
      prod = np.identity(d, dtype=np.complex128)
      for idx in indices:
        prod = prod @ matrices_A[idx]
      norm = np.linalg.norm(prod, ord='nuc')
      if np.isinf(norm) or np.isnan(norm):
        return -1_000_000.0
      sum_all_norms += norm
    except np.linalg.LinAlgError:
      return -1_000_000.0

  lhs = (1.0 / (n**m)) * sum_all_norms

  # Calculate the Right-Hand Side (RHS) of the inequality
  sum_distinct_norms = 0.0
  if n < m:
    return -lhs

  for indices in itertools.permutations(range(n), m):
    try:
      prod = np.identity(d, dtype=np.float64)
      for idx in indices:
        prod = prod @ matrices_A[idx]
      norm = np.linalg.norm(prod, ord='nuc')
      if np.isinf(norm) or np.isnan(norm):
        return -1_000_000.0
      sum_distinct_norms += norm
    except np.linalg.LinAlgError:
      return -1_000_000.0

  num_permutations = math.factorial(n) / math.factorial(n - m)
  rhs = (1.0 / num_permutations) * sum_distinct_norms

  score = rhs - lhs
  if np.isnan(score) or np.isinf(score):
    return -1_000_000.0

  return score
