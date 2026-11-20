# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/block_stacking_problem/block_stacking_problem.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
import sys


FLOAT_TOLERANCE = sys.float_info.epsilon * 100


def get_positions_score(positions: list[float]) -> float:
  """Calculates the score of given positions (block right endpoints).

  Each block has width 1. The position value represents the right endpoint
  of each block. The blocks are stacked from bottom to top, and the
  constraint is that the center of mass of all blocks above block i must
  lie within the support of block i (between positions[i]-1 and positions[i]).

  The score is the rightmost endpoint (positions[-1]), representing
  the maximum overhang achieved.
  """
  n = len(positions)
  if n == 0:
    return 0.0

  if n == 1:
    if positions[0] - 0.5 >= 0.0 - FLOAT_TOLERANCE:
      return -1.0
    return positions[0]

  sum_all = 0.0
  for k in range(n):
    sum_all += (positions[k] - 0.5)
  sum_all_avg = sum_all / n
  if sum_all_avg >= 0.0 - FLOAT_TOLERANCE:
    return -1.0

  upper_sum = 0.0
  upper_count = 0.0

  if n > 1:
    upper_sum = positions[n-1] - 0.5
    upper_count = 1.0

  for i in range(n - 2, -1, -1):
    upper_sum_avg = upper_sum / upper_count
    lb = positions[i] - 1.0
    ub = positions[i]
    if not (lb - FLOAT_TOLERANCE <= upper_sum_avg <= ub + FLOAT_TOLERANCE):
      return -1.0
    upper_sum += (positions[i] - 0.5)
    upper_count += 1.0
  return positions[-1]
