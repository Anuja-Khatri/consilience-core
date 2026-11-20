# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/ring_loading_problem/ring_loading_problem.ipynb, notebook code cells 0 (0-based, counting code cells only), functions validate_input, compute_alpha_exact, get_score (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import itertools
import numpy as np

def validate_input(u: list[float], v: list[float]):
  """Validates the input vectors u and v."""
  if len(u) != len(v):
    raise ValueError('Input vectors u and v must have the same length.')
  if not all(isinstance(x, (float, int)) for x in u) or not all(
      isinstance(x, (float, int)) for x in v
  ):
    raise ValueError('Input vectors must contain only floats or integers.')
  if not all(x >= 0 for x in u) or not all(x >= 0 for x in v):
    raise ValueError('Input vectors must be non-negative.')
  # Use a small tolerance for floating point comparisons
  if not all(ui + vi <= 1.000001 for ui, vi in zip(u, v)):
    raise ValueError('Condition u_i + v_i <= 1 must be met for all i.')
  if any(np.isnan(x) for x in u) or any(np.isnan(x) for x in v):
    raise ValueError('Input vectors cannot contain NaN values.')


def compute_alpha_exact(u: list[float], v: list[float]) -> tuple[float, float]:
  """Computes the smallest possible alpha (the min) for the given input vectors as well as alpha's smooth version."""
  validate_input(u, v)
  m = len(u)
  if m == 0:
    return 0.0, 0.0

  best_alpha = float('inf')

  z_choices = [(vi, -ui) for ui, vi in zip(u, v)]
  for z in itertools.product(*z_choices):
    max_alpha_for_z = 0
    if m > 1:
      max_alpha_for_z = max(abs(sum(z[:k]) - sum(z[k:])) for k in range(1, m))
    best_alpha = min(best_alpha, max_alpha_for_z)

  return best_alpha


def get_score(params: list[tuple[float, float]], m: int) -> float:
  """Calculates the score for a given set of (u, v) vector parameters."""
  assert isinstance(params, list), "params must be a list"
  assert isinstance(m, int), "m must be an integer"
  assert len(params) == m, "Invalid number of parameters"

  u, v = [], []
  for item in params:
    if not isinstance(item, (tuple, list)) or len(item) != 2:
      return -1.0
    if not isinstance(item[0], (float, int)) or not isinstance(
        item[1], (float, int)
    ):
      return -1.0
    if np.isnan(item[0]) or np.isnan(item[1]):
      return -1.0

    ui, vi = abs(item[0]), abs(item[1])
    s = ui + vi
    if s > 1.0:
      ui /= s
      vi /= s
    assert s < 1e9, "Numerical instability"
    u.append(ui)
    v.append(vi)

  try:
    exact_alpha = compute_alpha_exact(u, v)
    return exact_alpha
  except (ValueError, OverflowError):
    return -1.0
