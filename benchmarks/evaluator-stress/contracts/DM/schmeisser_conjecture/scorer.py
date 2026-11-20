# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/schmeisser_conjecture/schmeisser_conjecture.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np


def coefficient_distance_to_x_n_minus_c_family(roots):
  """Calculates a penalty based on how close the polynomial's coefficients are to the form x^n - c (family of polynomials)."""
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


def evaluate_construction_h(roots):
  """Evaluates constrction for a given set of roots (optimized).

  Args:
    roots: A numpy array of complex numbers representing the roots of a
      polynomial.

  Returns:
    The maximum distance from each root to its closest critical point.
  """
  n = len(roots)
  if n < 15:
    return 0

  # Project roots onto the unit circle (if outside)
  for i in range(len(roots)):
    if np.abs(roots[i]) > 1:
      roots[i] = roots[i] / np.abs(roots[i])  # Project to unit circle

  # if all roots have magnitude > 0.7, return 0
  if np.all(np.abs(roots) > 0.7):
    return 0

  critical_points = polynomial_critical_points_h(roots)

  # The points to consider are the midpoints (averages) of all pairs of roots
  points_to_consider = []
  for i in range(len(roots) - 1):
    for j in range(i + 1, len(roots)):
      midpoint = (2 * roots[i] + roots[j]) / 3
      if np.abs(midpoint) > 0.4:
        points_to_consider.append(midpoint)

  points_to_consider = np.array(points_to_consider)

  # Vectorized distance calculation and minimum finding
  distances = np.abs(points_to_consider[:, np.newaxis] - critical_points)
  min_distances = np.min(distances, axis=1)
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
