# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/de_bruijn_sharma_problem/de_bruijn_sharma_problem.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
from typing import List, Tuple
from scipy.spatial import HalfspaceIntersection, ConvexHull


def _get_halfspace_from_poly(
    roots: np.ndarray, n: int
) -> Tuple[float, float, float] | None:
  """Calculates the C4, C2_sq, and LHS terms for a given polynomial."""
  if roots.shape[0] != n or np.any(np.isnan(roots)):
    return None
  if np.abs(np.sum(roots)) > 1e-9:
    return None
  try:
    p_coeffs = np.poly(roots)
    if np.any(np.isnan(p_coeffs)):
      return None
    p_prime_coeffs = np.polyder(p_coeffs)
    if p_prime_coeffs.size == 0:
      return None
    critical_points = np.roots(p_prime_coeffs)

    # --- CRUCIAL CHANGE: Use sum of FOURTH powers as per the paper ---
    lhs = np.sum(np.abs(critical_points) ** 4)

    c4 = np.sum(np.abs(roots) ** 4)
    c2_sq = (np.sum(np.abs(roots) ** 2)) ** 2
    if np.isnan(lhs) or np.isnan(c4) or np.isnan(c2_sq):
      return None
    if c4 < 1e-9 and c2_sq < 1e-9:
      return None
    return (c4, c2_sq, lhs)
  except np.linalg.LinAlgError:
    return None


def calculate_area_score(polynomials: List[np.ndarray], n: int) -> float:
  """Calculates the score, which is the negative area of the feasible region."""
  if not isinstance(polynomials, list) or not polynomials:
    return -4.0

  interior_point = np.array([0.75, 0.75])
  halfspaces = [
      [-1.0, 0.0, 0.0],
      [-0.0, -1.0, 0.0],
      [1.0, 0.0, -1.0],
      [0.0, 1.0, -1.0],
  ]

  for poly_roots in polynomials:
    params = _get_halfspace_from_poly(poly_roots, n)
    if params:
      c4, c2_sq, lhs = params
      halfspaces.append([-c4, -c2_sq, lhs])

  # if len(halfspaces) <= 4: return -4.0

  try:
    # With the correct formula, the interior point should be stable
    vertices = HalfspaceIntersection(
        np.array(halfspaces), interior_point
    ).intersections
    if vertices.shape[0] < 3:
      return 0.0
    return -ConvexHull(vertices).volume - len(polynomials) / 10000.0
  except Exception as e:
    print(f'Warning: Qhull error encountered, returning poor score. {e}')
    return -1_000_000.0
