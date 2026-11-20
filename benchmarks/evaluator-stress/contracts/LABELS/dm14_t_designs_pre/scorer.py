# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/spherical_t_designs/spherical_t_designs.ipynb, notebook code cell 0 (0-based over code cells; '#@title Verification code', whole cell: get_dim_k, get_gegenbauer_poly, calculate_design_score) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
#@title Verification code

import numpy as np
import numba
from scipy.special import gegenbauer, binom

njit = numba.njit



# Memoization cache for expensive calculations
_gegenbauer_cache = {}
_dim_k_cache = {}


def get_dim_k(k: int, d: int) -> float:
  """Computes the dimension of the space of spherical harmonics of degree k on S^d."""
  if (k, d) in _dim_k_cache:
    return _dim_k_cache[(k, d)]
  # This formula for dimension of harmonic polynomials in d+1 variables is valid for k>=0
  # scipy's binom handles k-2 < 0 correctly (returns 0)
  dim = binom(d + k, k) - binom(d + k - 2, k - 2)
  _dim_k_cache[(k, d)] = dim
  return dim


def get_gegenbauer_poly(k: int, d: int):
  """Returns a memoized Gegenbauer polynomial object."""
  lam = (d - 1) / 2.0
  if (k, lam) in _gegenbauer_cache:
    return _gegenbauer_cache[(k, lam)]
  poly = gegenbauer(k, lam)
  _gegenbauer_cache[(k, lam)] = poly
  return poly


def calculate_design_score(points: np.ndarray, d: int, t: int, N: int) -> float:
  """Calculates the score for a potential spherical design."""
  # --- Safety checks ---
  if not isinstance(points, np.ndarray):
    points = np.array(points, dtype=np.float64)

  if points.ndim != 2 or points.shape != (N, d + 1):
    return -1_000_000.0

  if np.any(np.isnan(points)) or np.any(np.isinf(points)):
    return -1_000_000.0

  # --- Normalization ---
  norms = np.linalg.norm(points, axis=1, keepdims=True)
  # Handle zero-norm vectors
  if np.any(norms < 1e-9):
    return -1_000_000.0
  points_normalized = points / norms

  # --- Score Calculation ---
  if d == 1:
    # Special case for the circle S^1 using Fourier series condition
    # Convert points (x, y) to complex numbers z
    z = points_normalized[:, 0] + 1j * points_normalized[:, 1]
    total_error = 0.0
    # z_powers will be z^k in the k-th iteration (1-based index)
    z_powers = z.copy()
    for k in range(1, t + 1):
      # Sum of z_i^k over all points i
      sum_z_powers = np.sum(z_powers)
      # Add squared magnitude |sum(z_i^k)|^2 to error
      total_error += sum_z_powers.real**2 + sum_z_powers.imag**2
      # Update z_powers for next iteration: z^(k+1) = z^k * z
      if k < t:
        z_powers *= z
    return -total_error

  # General case for d >= 2
  dot_products = np.clip(points_normalized @ points_normalized.T, -1.0, 1.0)

  total_error = 0.0

  for k in range(1, t + 1):
    dim_k = get_dim_k(k, d)
    if abs(dim_k) < 1e-9:
      continue

    gegen_poly = get_gegenbauer_poly(k, d)

    # Denominator C_k(1), which is C_n^(\alpha)(1) = \binom{n+2\alpha-1}{n}
    denom = binom(k + d - 2, k)
    if abs(denom) < 1e-9:
      continue

    # Evaluate polynomial on all dot products
    poly_vals = gegen_poly(dot_products)

    # Sum over all pairs (i, j)
    error_k = np.sum(poly_vals)

    total_error += dim_k * error_k / denom

  return -total_error

