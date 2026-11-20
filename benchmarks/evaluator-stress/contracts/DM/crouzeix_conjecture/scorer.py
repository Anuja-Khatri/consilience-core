# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/crouzeix_conjecture/crouzeix_conjecture.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
import numba
import scipy.linalg as la
njit = numba.njit  # as in the notebook's initial-program cell


@njit
def evaluate_poly_at_point_njit(z, coeffs):
  """Evaluates a polynomial at a complex point z using Horner's method.

  `coeffs` must be a NumPy array.
  """
  # Start with the coefficient of the highest power
  res = coeffs[-1]
  # Iterate from the second to last coefficient down to the first
  for i in range(len(coeffs) - 2, -1, -1):
    res = res * z + coeffs[i]
  return res


@njit
def evaluate_polynomial_matrix_njit(matrix_A, poly_coeffs):
  """Evaluates a polynomial at a matrix. `poly_coeffs` must be a NumPy array."""
  result = np.zeros_like(matrix_A, dtype=matrix_A.dtype)
  power_A = np.eye(matrix_A.shape[0], dtype=matrix_A.dtype)
  for coeff in poly_coeffs:
    result += coeff * power_A
    power_A = power_A @ matrix_A
  return result


@njit
def maximize_polynomial_field_of_values_njit(
    poly_coeffs, A, num_theta_points=1000
):
  """Maximizes |p(<Ax,x>)|. `poly_coeffs` must be a NumPy array."""
  max_p_value = -np.inf
  theta_vals = np.linspace(0, 2 * np.pi, num_theta_points)

  for theta in theta_vals:
    H_theta = 0.5 * (np.exp(1j * theta) * A + np.exp(-1j * theta) * A.conj().T)
    eigenvalues, eigenvectors = np.linalg.eig(H_theta)

    largest_eigenvalue_index = np.argmax(eigenvalues.real)

    v_theta = eigenvectors[:, largest_eigenvalue_index]
    v_theta = v_theta / np.linalg.norm(v_theta)
    z_theta = v_theta.conj().T @ A @ v_theta

    # Call the jitted polynomial evaluator with the complex point and NumPy array of coeffs
    current_p_value = np.abs(evaluate_poly_at_point_njit(z_theta, poly_coeffs))

    if current_p_value > max_p_value:
      max_p_value = current_p_value

  return max_p_value


def evaluate_construction(A, p_coeffs, num_theta_points=1000):
  """Wrapper function that calls the high-performance Numba-jitted core."""
  # **FIX**: Convert the list of coefficients to a NumPy array here.
  # This array (not a Polynomial object) is then passed to the jitted functions.
  p_coeffs_arr = np.array(p_coeffs, dtype=np.complex128)

  # if the matrix is 2x2 or smaller, return -np.inf
  if A.shape[0] <= 9:
    return -np.inf

  # --- Call the Numba-jitted functions with the correct array type ---
  try:
    p_A = evaluate_polynomial_matrix_njit(A, p_coeffs_arr)
  except Exception as e:
    print(f'Error in evaluate_polynomial_matrix_njit: {e}')
    return -np.inf
  max_val_fov = maximize_polynomial_field_of_values_njit(
      p_coeffs_arr, A, num_theta_points
  )

  norm_p_A_2 = la.norm(p_A, ord=2)

  final_score = norm_p_A_2 / max_val_fov
  return final_score
