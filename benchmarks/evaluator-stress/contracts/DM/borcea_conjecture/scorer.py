# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/borcea_conjecture/borcea_conjecture.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np


def coefficient_distance_to_x_n_minus_c_family(roots):
  """Calculates a penalty based on how close the polynomial's coefficients are to the form x^n - c (family of polynomials).

  Args:
    roots: A numpy array of complex numbers representing the roots of a
      polynomial.

  Returns:
    A float representing the penalty.
  """
  coeffs = polynomial_roots_to_coeffs(roots)
  degree = len(coeffs) - 1

  # Initialize penalty (we'll sum squared magnitudes of intermediate
  # coefficients)
  penalty_distance = 0

  # Iterate through intermediate coefficients (from x^(n-1) down to x^1)
  for i in range(1, degree):  # Indices 1 to n-1 correspond to x^(n-1) to x^1
    coeff_index = i  # Index in the coefficient array (coeffs)
    coeff_magnitude_squared = np.abs(coeffs[coeff_index]) ** 2
    penalty_distance += coeff_magnitude_squared

  # We could also penalize deviation of the leading coefficient from 1
  # (optional):
  leading_coeff_penalty = np.abs(coeffs[0] - 1) ** 2
  penalty_distance += leading_coeff_penalty

  return penalty_distance


def polynomial_roots_to_coeffs(roots):
  """Converts roots of a polynomial to its coefficients."""
  return np.poly(roots)


def calculate_extremal_family_penalty(
    roots, critical_points, max_min_distance, tolerance=0.75
):
  """Calculates penalty if construction resembles the extremal family."""
  penalty = 0.0
  special_zero_found = False

  for i in range(len(roots)):
    special_zero = roots[i]

    # Calculate distances from the special zero to all critical points
    distances_to_special_zero = np.abs(critical_points - special_zero)

    # Check if all critical points are approximately at max_min_distance from
    # the special zero
    if np.all(np.abs(distances_to_special_zero - max_min_distance) < tolerance):
      special_zero_found = True
      break  # No need to check other roots if one special zero is found

  if special_zero_found:
    penalty = 1.0  # Increased penalty for closer resemblance to extremal family

  return penalty


def polynomial_roots_to_coeffs_h(roots):
  """Converts roots of a polynomial to its coefficients."""
  return np.poly(roots)


def polynomial_coeffs_to_derivative_coeffs_h(coeffs):
  """Calculates coefficients of the derivative of a polynomial."""
  derivative_coeffs = np.polyder(coeffs)
  return derivative_coeffs


def polynomial_critical_points_h(roots):
  """Calculates critical points of a polynomial given its roots."""
  coeffs = polynomial_roots_to_coeffs_h(roots)
  derivative_coeffs = polynomial_coeffs_to_derivative_coeffs_h(coeffs)
  critical_points = np.roots(derivative_coeffs)
  return critical_points


def evaluate_sendov_conjecture_h(roots):
  """Evaluates Sendov's conjecture for a given set of roots (optimized).

  Args:
    roots: A numpy array of complex numbers representing the roots of a
      polynomial.

  Returns:
    The score for the given set of roots.
  """
  n = len(roots)
  if n < 15 or n > 30:
    return 0  # Conjecture is for degree n >= 2

  # Check that the max magnitude is not too large
  if np.max(np.abs(roots)) > 20:
    return 0
  # Scale roots so their average modulus is less than 1
  # Check first if dividing by zero
  if np.mean(np.abs(roots)) < 0.01:
    return 0
  roots = roots / np.mean(np.abs(roots))

  # Check that at most half of the roots are near the origin
  close_to_origin = np.sum(np.abs(roots) < 0.3)
  if close_to_origin > n / 5:
    return 0

  critical_points = polynomial_critical_points_h(roots)

  # Vectorized distance calculation and minimum finding
  distances = np.abs(roots[:, np.newaxis] - critical_points)  # shape (n, n-1)
  min_distances = np.min(distances, axis=1)  # shape (n,)
  max_min_distance = np.max(min_distances)

  penalty = calculate_extremal_family_penalty(
      roots, critical_points, max_min_distance
  )
  coeff_unity_distance = coefficient_distance_to_x_n_minus_c_family(roots)
  if coeff_unity_distance < n:
    penalty += 1.0
  else:
    penalty += 0

  return max_min_distance - penalty
