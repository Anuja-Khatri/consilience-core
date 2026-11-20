# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/smale_problem/smale_problem.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np


def polynomial_roots_to_coeffs(roots):
  """Converts roots of a polynomial to its coefficients."""
  return np.poly(roots)


def polynomial_coeffs_to_derivative_coeffs(coeffs):
  """Calculates coefficients of the derivative of a polynomial."""
  return np.polyder(coeffs)


def polynomial_critical_points(roots):
  """Calculates critical points of a polynomial given its roots."""
  coeffs = polynomial_roots_to_coeffs(roots)
  derivative_coeffs = polynomial_coeffs_to_derivative_coeffs(coeffs)
  critical_points = np.roots(derivative_coeffs)
  return critical_points


def evaluate_smale_conjecture_h(roots: np.ndarray, grid_size):
  """Evaluates Smale's conjecture using a grid of test points.

  Args:
    roots: Roots of the polynomial.
    grid_size: Number of points along each axis for the grid in [-2, 2] x [-2,
      2].

  Returns:
    Maximum Smale ratio found on the grid.
  """
  n = len(roots)
  if n < 10:
    return 0  # Conjecture is for degree n >= 2

  coeffs = polynomial_roots_to_coeffs(roots)
  derivative_coeffs = polynomial_coeffs_to_derivative_coeffs(coeffs)
  critical_points = polynomial_critical_points(roots)

  max_ratio = 0.0

  # Create grid of test points in [-2, 2] x [-2, 2]
  x_vals = np.linspace(-2, 2, grid_size)
  y_vals = np.linspace(-2, 2, grid_size)
  z_grid = np.array([x + 1j * y for x in x_vals for y in y_vals])  # pylint: disable=g-complex-comprehension

  for z in z_grid:
    # Ensure f'(z) is not zero
    f_prime_z = np.polyval(derivative_coeffs, z)
    if np.abs(f_prime_z) < 0.01:
      continue
    if np.abs(f_prime_z) > 10_000_000.0:
      return 0

    min_smale_ratio_for_z = float('inf')

    for xi in critical_points:
      numerator = np.abs(np.polyval(coeffs, z) - np.polyval(coeffs, xi))
      denominator = np.abs(z - xi) * np.abs(f_prime_z)

      if np.isclose(denominator, 0):
        continue
      smale_ratio = numerator / denominator
      min_smale_ratio_for_z = min(min_smale_ratio_for_z, smale_ratio)

    max_ratio = max(max_ratio, min_smale_ratio_for_z)

  return max_ratio
