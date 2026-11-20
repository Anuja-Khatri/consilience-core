# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/finite_field_sum_product_problem/finite_field_sum_product_problem.ipynb, notebook code cells 2 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import logging
import math
import numba
import numpy as np
njit = numba.njit

#@title Evaluation code

@njit
def _calculate_sum_prod_numba(
    construction: np.ndarray, p: int
) -> tuple[int, int]:
  """A Numba-jitted function to rapidly calculate sum and product set sizes."""
  n = construction.shape[0]

  # Calculate sum set X+X
  sum_set = {np.int64(0)}  # Initialize with a dummy value
  sum_set.clear()  # Numba needs the type to be inferred
  for i in range(n):
    for j in range(n):
      sum_val = (construction[i] + construction[j]) % p
      sum_set.add(sum_val)

  # Calculate product set X*X
  prod_set = {np.int64(0)}
  prod_set.clear()
  for i in range(n):
    for j in range(n):
      prod_val = (construction[i] * construction[j]) % p
      prod_set.add(prod_val)

  return len(sum_set), len(prod_set)


def calculate_score(construction: np.ndarray, p: int) -> float:
  """Calculates the score for a given sum-product construction."""
  target_size = int(math.sqrt(p))

  # --- Basic Validity Checks (remain in pure Python) ---
  if not isinstance(construction, np.ndarray) or construction.ndim != 1:
    logging.warning('Invalid construction: not a 1D numpy array.')
    return np.inf

  # Ensure all elements are within the field F_p.
  if np.any(construction < 0) or np.any(construction >= p):
    logging.warning('Invalid construction: elements are out of F_p bounds.')
    return np.inf

  # Remove duplicates to get the actual set.
  # Note: Numba doesn't have np.unique, so we do it here.
  if np.unique(construction).shape[0] != construction.shape[0]:
    logging.warning('Invalid construction: contains duplicate elements.')
    return np.inf

  # Check if the construction has the correct size.
  if construction.shape[0] != target_size:
    logging.warning(
        f'Invalid construction: size is {construction.shape[0]},'
        f' expected {target_size}.'
    )
    return np.inf

  # --- Call the fast Numba function for the core calculation ---
  # The first call will have a slight compilation overhead. Subsequent calls are free.
  sum_set_size, prod_set_size = _calculate_sum_prod_numba(construction, p)

  # The score is the maximum of the two sizes. Lower is better.
  score = float(max(sum_set_size, prod_set_size))

  return score
