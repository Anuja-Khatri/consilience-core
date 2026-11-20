# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/finite_field_nikodym_problem/finite_field_nikodym.ipynb, notebook code cells 9 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
import numba
njit = numba.njit  # as defined at the top of the notebook's construction cells


@njit
def is_valid_nikodym_numba(construction: np.ndarray, p: int, d: int) -> bool:
  """Checks if a construction is a valid Nikodym set in F_p^d.

  A Nikodym set N must satisfy the following: for every point x in F_p^d,
  there exists a line l passing through x such that l \ {x} is a subset of N.

  NOTE: This implementation is hardcoded for d=3 to comply with Numba's
  limitation on converting lists to tuples for dynamic tuple creation.
  """
  if d != 3:
    # This function is only valid for d=3.
    return False

  # Create a set from the construction for efficient lookups.
  dummy_tuple = (np.int64(0), np.int64(0), np.int64(0))
  construction_set = {dummy_tuple}
  construction_set.clear()
  for i in range(construction.shape[0]):
    construction_set.add(
        (construction[i, 0], construction[i, 1], construction[i, 2])
    )

  # Helper to check if a "punctured" line is fully contained in the set.
  def check_punctured_line_is_contained(point_x, direction_v, const_set):
    for t in range(1, p):  # We check for t=1, 2, ..., p-1.
      p_arr = (point_x + t * direction_v) % p
      point_on_line = (p_arr[0], p_arr[1], p_arr[2])
      if point_on_line not in const_set:
        return False
    return True

  # --- Main Loop: Iterate through EVERY point x in F_p^3 ---
  for x1 in range(p):
    for x2 in range(p):
      for x3 in range(p):
        x = np.array([x1, x2, x3], dtype=np.int64)
        found_line_for_x = False

        # Search for a direction v for the current point x.
        # Case 1: Directions v = (1, *, *)
        for v2 in range(p):
          if found_line_for_x:
            break
          for v3 in range(p):
            v = np.array([1, v2, v3], dtype=np.int64)
            if check_punctured_line_is_contained(x, v, construction_set):
              found_line_for_x = True
              break
        if found_line_for_x:
          continue

        # Case 2: Directions v = (0, 1, *)
        for v3 in range(p):
          v = np.array([0, 1, v3], dtype=np.int64)
          if check_punctured_line_is_contained(x, v, construction_set):
            found_line_for_x = True
            break
        if found_line_for_x:
          continue

        # Case 3: Direction v = (0, 0, 1)
        v = np.array([0, 0, 1], dtype=np.int64)
        if check_punctured_line_is_contained(x, v, construction_set):
          found_line_for_x = True

        # If after checking all directions, no suitable line was found for x:
        if not found_line_for_x:
          return False  # Not a valid Nikodym set.

  # If we get here, a line was found for every point x.
  return True


def calculate_score(construction: np.ndarray, p: int, d: int) -> float:
  """Calculates the score for a given construction."""
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

  is_nikodym = is_valid_nikodym_numba(unique_construction, p, d)

  if not is_nikodym:
    return np.inf  # Heavily penalize invalid sets

  return -float(size)
