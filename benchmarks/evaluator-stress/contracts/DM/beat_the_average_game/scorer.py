# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/beat_the_average_game/beat_the_average_game.ipynb, notebook code cells 0 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numba
import numpy as np
from scipy import optimize

#@title Verification code

import numba
import numpy as np
from scipy import optimize

njit = numba.njit
linprog = optimize.linprog


@njit
def get_score(pmf_x: np.ndarray, sequence_length: int) -> float:
  """Calculates P[X1 + X2 + X3 < 2*X4] using vectorized numpy operations.

  Args:
      pmf_x: The probability mass function for each variable.
      sequence_length: The length of the pmf_x sequence.

  Returns:
      The score representing P[X1 + X2 + X3 < 2*X4].
  """
  if len(pmf_x) != sequence_length:
    return 0.0

  pmf_x = np.maximum(pmf_x, 0)
  current_sum = np.sum(pmf_x)

  if current_sum <= 1e-8:
    return 0.0
  pmf_x /= current_sum

  pmf_x1x2 = np.convolve(pmf_x, pmf_x)
  pmf_y = np.convolve(pmf_x1x2, pmf_x)
  cdf_y = np.cumsum(pmf_y)

  probs_y_less_than_2x4 = np.zeros(len(pmf_x))
  indices = 2 * np.arange(1, len(pmf_x)) - 1
  probs_y_less_than_2x4[1:] = cdf_y[indices]

  total_prob = np.dot(pmf_x, probs_y_less_than_2x4)
  return total_prob
