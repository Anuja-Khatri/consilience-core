# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/szemeredi_trotter_constructions/szemeredi_trotter_constructions.ipynb, notebook code cells 0 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import math
from typing import List, Tuple
import numpy as np
from numba import njit

#@title Verification code

import numpy as np
import math
from numba import njit
from typing import Tuple, List


@njit
def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
  """Extended Euclidean Algorithm: returns g, x, y such that ax + by = g."""
  if a == 0:
    return b, 0, 1
  g, x1, y1 = extended_gcd(b % a, a)
  x = y1 - (b // a) * x1
  y = x1
  return g, x, y


@njit
def count_solutions_in_box(a: int, b: int, c: int, W: int, H: int) -> int:
  """Counts integer solutions to ax + by = c with 0 <= x < W and 0 <= y < H."""
  if W <= 0 or H <= 0:
    return 0
  if a == 0 and b == 0:
    return W * H if c == 0 else 0

  if a == 0:
    if b != 0 and c % b == 0:
      py = c // b
      return W if 0 <= py < H else 0
    return 0
  if b == 0:
    if a != 0 and c % a == 0:
      px = c // a
      return H if 0 <= px < W else 0
    return 0

  g, x0_base, y0_base = extended_gcd(a, b)
  if c % g != 0:
    return 0

  x0 = x0_base * (c // g)
  y0 = y0_base * (c // g)
  b_g = b // g
  a_g = a // g

  k_min = -np.inf
  k_max = np.inf

  if b_g > 0:
    k_min = max(k_min, np.ceil(-x0 / b_g))
    k_max = min(k_max, np.floor((W - 1 - x0) / b_g))
  else:
    k_min = max(k_min, np.ceil((W - 1 - x0) / b_g))
    k_max = min(k_max, np.floor(-x0 / b_g))

  if a_g > 0:
    k_min = max(k_min, np.ceil((y0 - (H - 1)) / a_g))
    k_max = min(k_max, np.floor(y0 / a_g))
  else:
    k_min = max(k_min, np.ceil(y0 / a_g))
    k_max = min(k_max, np.floor((y0 - (H - 1)) / a_g))

  if k_max < k_min:
    return 0
  return int(k_max - k_min) + 1


@njit
def calculate_score_numba(lines: np.ndarray, H: int, n: int) -> float:
  """Calculates raw incidences using O(log n) formula per line."""
  if H <= 0:
    return 0.0
  W = n // H
  incidence_count = 0

  for i in range(lines.shape[0]):
    a, b, c = lines[i, 0], lines[i, 1], lines[i, 2]
    incidence_count += count_solutions_in_box(a, b, c, W, H)

    remaining_points = n - H * W
    if remaining_points > 0:
      c_new = c - b * H
      incidence_count += count_solutions_in_box(a, 0, c_new, remaining_points, 1)

  return float(incidence_count)


def calculate_score(construction, n):
  """Calculates the number of incidences for a given construction."""
  if not (isinstance(construction, tuple) and len(construction) == 2):
    return -np.inf

  H, lines = construction
  if H <= 0 or len(lines) != n:
    return -np.inf

  unique_lines_set = set()
  for a, b, c in lines:
    if a == 0 and b == 0:
      continue
    common_divisor = math.gcd(math.gcd(a, b), c)
    if common_divisor != 0:
      a //= common_divisor
      b //= common_divisor
      c //= common_divisor
    if a < 0 or (a == 0 and b < 0):
      a, b, c = -a, -b, -c
    unique_lines_set.add((a, b, c))

  unique_lines_list = list(unique_lines_set)
  if not unique_lines_list:
    lines_arr = np.array([], dtype=np.int64).reshape(0, 3)
  else:
    lines_arr = np.array(unique_lines_list, dtype=np.int64)

  return calculate_score_numba(lines_arr, H, n)
