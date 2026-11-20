# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/prime_number_theorem/prime_number_theorem.ipynb, notebook code cells 2 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
import numba
from typing import Mapping


@numba.njit(fastmath=True)
def evaluate_partial_function_vectorized_numba(
    partial_function_keys, partial_function_values, num_samples
):
  """Numba-optimized vectorized function."""

  max_key_in_function = np.max(partial_function_keys)
  upper_bound_for_sampling = 10 * max_key_in_function

  for _ in range(num_samples):
    x_sample = np.random.uniform(1, upper_bound_for_sampling)
    x_sum = np.sum(
        partial_function_values * (x_sample // partial_function_keys)
    )

    if x_sum > 1.0001:
      return -np.inf

  a_value = - np.sum(
      partial_function_values
      * np.log(partial_function_keys)
      / partial_function_keys
  )
  return a_value


def evaluate_partial_function(
    partial_function: Mapping[int, float], num_samples
):
  # Create a new dictionary to avoid modifying the original
  clipped_partial_function = {}
  for k, v in partial_function.items():
    clipped_partial_function[k] = np.clip(v, -10, 10)

  total_sum = 0
  for k in clipped_partial_function:  # Use the clipped dictionary here
    total_sum += clipped_partial_function[k] / k
  if 1 in clipped_partial_function:  # Use the clipped dictionary here
    clipped_partial_function[1] -= total_sum  # Use the clipped dictionary here
  else:
    clipped_partial_function[1] = -total_sum  # Use the clipped dictionary here

  keys_np = np.array(
      list(clipped_partial_function.keys())
  )  # Use the clipped dictionary here
  values_np = np.array(
      list(clipped_partial_function.values())
  )  # Use the clipped dictionary here
  return evaluate_partial_function_vectorized_numba(
      keys_np, values_np, num_samples
  )
