# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/furstenberg_sarkozy_problem/furstenberg_sarkozy_problem.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import math


def is_square_free(n):
  """Checks if an integer n is square-free.

  Args:
      n (int): The integer to check.

  Returns:
      bool: True if n is square-free, False otherwise.
  """
  if n <= 1:
    return True  # 1 is considered square-free

  # Handle negative numbers (square-freeness is usually defined for positive
  # integers)
  if n < 0:
    n = -n

  # Check divisibility by squares of primes up to sqrt(n)
  d = 2
  while d * d <= n:
    if n % (d * d) == 0:
      return False
    d += 1
  return True


def get_score(best_list, best_m):
  """Returns the score for the best list."""
  # if best_m is not square-free, return 0
  if not is_square_free(best_m):
    return 0
  best_list_set = set(best_list)
  # reduce each element mod best_m
  best_list_set = {x % best_m for x in best_list_set}
  kth_power_residues = set()
  for y in range(1, best_m):
    residue = pow(y, 2, best_m)
    if residue != 0:
      kth_power_residues.add(residue)
  non_zero_residues = sorted(list(kth_power_residues))

  # Verify that no two elements differ by a non-zero k-th power residue
  for i in best_list_set:
    for j in best_list_set:
      if (i - j) % best_m in non_zero_residues:
        return 0

  return 1 - 1.0 / 2.0 + math.log(len(best_list_set)) / (2 * math.log(best_m))
