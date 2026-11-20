# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/sums_differences_problems/sums_differences_problems.ipynb, notebook code cells 6 (0-based, counting code cells only), functions compute_lower_bound (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import itertools
import numpy as np

def compute_lower_bound(u: list[int]) -> float:
  """Returns the lower bound obtained from the input set u, which must satisfy min(u) == 0."""
  if min(u) != 0:
    raise AssertionError("Set U must be nonnegative and must contain 0; got minimum value ", min(u))

  max_u = max(u)
  u_minus_u = np.zeros(2 * max_u + 1, dtype=bool)  # Store the set u - u as an array of booleans.
  u_plus_u = np.zeros(2 * max_u + 1, dtype=bool)  # Store the set u + u as an array of booleans.
  u_np = np.array(u)

  for i in u:
    u_minus_u[i - u_np + max_u] = True
    u_plus_u[i + u_np] = True

  u_minus_u_size = np.sum(u_minus_u)
  u_plus_u_size = np.sum(u_plus_u)

  if u_minus_u_size > 2 * max_u + 1:
    raise AssertionError(
        "The constraint |U - U| <= 2 max (U) + 1 is not satisfied. Got: "
        f"lhs={u_minus_u_size} but rhs={2 * max_u + 1}."
    )

  return np.log(u_minus_u_size / u_plus_u_size) / np.log(2 * max_u + 1) + 1.0
