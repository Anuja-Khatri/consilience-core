# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/imo_2025_p6/imo_2025_p6.ipynb, notebook code cells 0 (0-based, counting code cells only), functions _calculate_score_numba, calculate_score (Apache-2.0).
# Scoring cells copied verbatim; only imports added
from typing import List, Tuple
import numba
import numpy as np
njit = numba.njit

@njit
def _calculate_score_numba(tiles_array: np.ndarray, n: int) -> float:
  """Core scoring logic, JIT-compiled with Numba for performance."""
  grid = np.zeros((n, n), dtype=np.int32)

  # Check for out-of-bounds tiles and overlaps.
  for i in range(tiles_array.shape[0]):
    r, c, h, w = tiles_array[i, :]
    if r < 0 or c < 0 or r + h > n or c + w > n:
      return -np.inf  # Out of bounds.
    if np.any(grid[r : r + h, c : c + w]):
      return -1_000_000_000.0  # Overlap.
    grid[r : r + h, c : c + w] = 1

  # Calculate penalty for deviating from the 'one-uncovered-square' rule.
  uncovered_per_row = n - np.sum(grid, axis=1)
  uncovered_per_col = n - np.sum(grid, axis=0)

  row_penalty = np.sum(np.abs(uncovered_per_row - 1))
  col_penalty = np.sum(np.abs(uncovered_per_col - 1))
  total_penalty = row_penalty + col_penalty

  # The score is primarily driven by the penalty. For valid solutions (penalty=0),
  # the score is the negative number of tiles, encouraging fewer tiles.
  score = -tiles_array.shape[0] - 100 * total_penalty
  return float(score)


def calculate_score(tiles: List[Tuple[int, int, int, int]], n: int) -> float:
  """Calculates the score for a given tiling configuration.

  A higher score is better.
  """
  # Perform initial validation in Python before passing to Numba.
  if not isinstance(tiles, list):
    return -np.inf
  if not tiles:
    # Calculate penalty for an empty grid.
    penalty = 2 * n * (n - 1)
    return float(-1000 * penalty)

  for t in tiles:
    if not isinstance(t, (list, tuple)) or len(t) != 4:
      return -np.inf
    if not all(isinstance(x, int) for x in t):
      return -np.inf
    if t[2] <= 0 or t[3] <= 0:
      return -np.inf  # Non-positive dimensions.

  tiles_array = np.array(tiles, dtype=np.int32)
  return _calculate_score_numba(tiles_array, n)
