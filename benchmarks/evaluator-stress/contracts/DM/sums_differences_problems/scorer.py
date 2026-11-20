# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/sums_differences_problems/sums_differences_problems.ipynb, notebook code cells 0 (0-based, counting code cells only), functions get_score, get_score_numba (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import math
import numpy as np
from numba import njit

def get_score(best_list):
  """Returns the score for the given list using Numba."""
  if len(best_list) < 2:
    return 0

  # if the list contains non-integers, return 0
  if not all(isinstance(x, int) for x in best_list):
    return 0

  return get_score_numba(best_list)


@njit
def get_score_numba(best_list):
  """Returns the score for the given list using Numba."""

  best_list_set = set(best_list)
  n_unique = len(best_list_set)

  a_minus_a = set()
  for i in best_list:
    for j in best_list:
      a_minus_a.add(i - j)

  a_plus_a = set()
  for i in best_list:
    for j in best_list:
      a_plus_a.add(i + j)

  lhs = len(a_minus_a) / n_unique
  rhs = len(a_plus_a) / n_unique

  try:
    return math.log(rhs) / math.log(lhs)
  except Exception:
    return 0
