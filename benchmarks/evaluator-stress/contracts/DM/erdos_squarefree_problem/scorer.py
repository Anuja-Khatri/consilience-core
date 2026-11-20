# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/erdos_squarefree_problem/erdos_squarefree_problem.ipynb, notebook code cells 0 (0-based, counting code cells only), functions gcd_numba, is_squarefree_numba, calculate_score (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import re
from typing import Any, List, Mapping
import numba
import numpy as np
njit = numba.njit

@njit
def gcd_numba(a, b):
  """Computes GCD using Numba.

  Handles non-positive inputs returning abs(gcd).

  Args:
    a: The first integer.
    b: The second integer.

  Returns:
    The greatest common divisor of a and b.
  """
  # Ensure inputs are integers for modulo operation
  a_int = int(a)
  b_int = int(b)
  while b_int:
    a_int, b_int = b_int, a_int % b_int
  # Ensure result is non-negative, consistent with math.gcd
  # Note: gcd(0, 0) typically returns 0. gcd(a, 0) returns abs(a).
  return abs(a_int)


@njit
def is_squarefree_numba(n_signed):
  """Checks if n is squarefree using Numba. Handles n<=0 and n=1."""
  # Definition: An integer is squarefree if no prime squared divides it.
  # Conventionally, 1 is squarefree. 0 is not (divisible by 4, 9, ...).
  # Negative numbers: -n is squarefree iff n is. e.g., -4 is not, -6 is.
  n = abs(int(n_signed))  # Ensure positive integer
  if n == 0:
    return False
  if n == 1:
    return True

  temp_n = n  # Work on a copy

  # Check factor 2 first
  if temp_n % 2 == 0:
    temp_n //= 2
    if temp_n % 2 == 0:  # Divisible by 4
      return False

  # Check odd factors starting from 3
  d = 3
  # Optimization: Only need to check primes d up to sqrt(n)
  # The loop condition d * d <= temp_n handles this.
  while d * d <= temp_n:
    if temp_n % d == 0:  # Found a factor d
      temp_n //= d  # Divide by d
      # Check if divisible by d again (meaning d*d was a factor of original n)
      if temp_n % d == 0:
        return False
    # Move to the next odd number
    d += 2

  # After the loop, temp_n might be a prime > sqrt(original n) or 1.
  # No square factor involving primes up to sqrt(n) was found.
  return True


def calculate_score(set_a: List[int], modulus: int) -> float:
  """Calculates the score for a set A modulo M based on squarefree condition."""
  # --- Basic Validity Checks ---
  if not isinstance(modulus, int) or modulus <= 1:
    return -1_000_000.0
  if not isinstance(set_a, list):
    return -1_000_000.0

  if modulus % 25 == 0:
    modulus = 625

  # Handle empty set A
  if not set_a:
    return 0.0  # Density is 0, penalty is 0
  processed_set_a = sorted(
      list(
          set(
              int(x)
              for x in set_a
              if isinstance(x, (int, np.integer)) and 0 <= int(x) < modulus
          )
      )
  )

  n = len(processed_set_a)
  density = n / modulus

  penalty_count = 0
  # Iterate through all pairs (a, b) using the input list A
  for i in range(n):
    a = processed_set_a[i]
    for j in range(i, n):
      b = processed_set_a[j]
      # Calculate ab + 1. Python handles large integers.
      val = int(a) * int(b) + 1
      # Calculate gcd(ab+1, M). Use numba helper.
      g = gcd_numba(val, int(modulus))

      # Check if gcd is squarefree. Use numba helper.
      # g can be 0 only if val=0 and M=0 (disallowed). g=1 is squarefree.
      if is_squarefree_numba(g):
        penalty_count += 1

  # Penalty term as defined: (count of bad pairs) / M
  penalty = penalty_count / modulus
  score = density - penalty

  # Return score as float
  return float(score)
