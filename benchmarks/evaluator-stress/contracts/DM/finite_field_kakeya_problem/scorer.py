# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/finite_field_kakeya_problem/finite_field_kakeya.ipynb, notebook code cells 3 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
import numba
njit = numba.njit  # as defined at the top of the notebook's construction cells


@njit
def _is_point_in_construction(
    point_to_check: np.ndarray, construction: np.ndarray
) -> bool:
  """Numba-friendly check if a point exists in the construction array."""
  for i in range(construction.shape[0]):
    is_equal = True
    for j in range(construction.shape[1]):
      if construction[i, j] != point_to_check[j]:
        is_equal = False
        break
    if is_equal:
      return True
  return False


@njit
def is_valid_kakeya_numba(construction: np.ndarray, p: int, d: int) -> bool:
  """Checks if a construction is a valid Kakeya set.

  This function is designed to be JIT-compiled with Numba.
  """
  # Manually iterate through all directions, as itertools.product is not available in Numba.
  if d == 3:
    v1 = 0
    for v2 in range(2):
      for v3 in range(p):
        if v1 == 0 and v2 == 0 and v3 == 0:
          continue
        v = np.array([v1, v2, v3], dtype=np.int64)

        found_line_for_v = False
        for i in range(construction.shape[0]):
          x = construction[i]
          line_is_contained = True
          for t in range(1, p):
            point_on_line = (x + t * v) % p
            if not _is_point_in_construction(point_on_line, construction):
              line_is_contained = False
              break
          if line_is_contained:
            found_line_for_v = True
            break
        if not found_line_for_v:
          return False
    v1 = 1
    for v2 in range(p):
      for v3 in range(p):
        if v1 == 0 and v2 == 0 and v3 == 0:
          continue
        v = np.array([v1, v2, v3], dtype=np.int64)

        found_line_for_v = False
        for i in range(construction.shape[0]):
          x = construction[i]
          line_is_contained = True
          for t in range(1, p):
            point_on_line = (x + t * v) % p
            if not _is_point_in_construction(point_on_line, construction):
              line_is_contained = False
              break
          if line_is_contained:
            found_line_for_v = True
            break
        if not found_line_for_v:
          return False
  elif d == 4:
    for v1 in range(2):
      for v2 in range(p):
        for v3 in range(p):
          for v4 in range(p):
            if v1 == 0 and v2 == 0 and v3 == 0 and v4 == 0:
              continue
            v = np.array([v1, v2, v3, v4], dtype=np.int64)

            found_line_for_v = False
            for i in range(construction.shape[0]):
              x = construction[i]
              line_is_contained = True
              for t in range(1, p):
                point_on_line = (x + t * v) % p
                if not _is_point_in_construction(point_on_line, construction):
                  line_is_contained = False
                  break
              if line_is_contained:
                found_line_for_v = True
                break
            if not found_line_for_v:
              return False
  return True


def calculate_score(construction: np.ndarray, p: int, d: int) -> float:
  """Calculates the score for a given construction.

  A higher score is better.
  """
  if (
      not isinstance(construction, np.ndarray)
      or construction.ndim != 2
      or construction.shape[1] != d
  ):
    return np.inf

  if construction.shape[0] == 0:
    return np.inf

  # Remove duplicate points before scoring
  unique_tuples = {tuple(row) for row in construction}
  unique_construction = np.array(list(unique_tuples), dtype=np.int64)
  size = unique_construction.shape[0]

  is_kakeya = is_valid_kakeya_numba(unique_construction, p, d)

  if not is_kakeya:
    return np.inf  # Heavily penalize invalid sets

  return -float(size)
