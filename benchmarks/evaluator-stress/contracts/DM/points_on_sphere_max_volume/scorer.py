# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/points_on_sphere_max_volume/points_on_sphere_max_volume.ipynb, notebook code cells 0 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import math
import numpy as np
from scipy.spatial import ConvexHull, QhullError

#@title Verification code

import numpy as np
import math
from scipy.spatial import ConvexHull, QhullError


def calculate_polytope_volume(
    placements_params: np.ndarray, num_points: int, dimension: int
) -> float:
  """Calculates the volume of the convex hull of points on the unit sphere.

  Points are first normalized to lie on the unit sphere, then the volume of
  their convex hull is computed.
  """
  if not isinstance(placements_params, np.ndarray):
    return -np.inf
  if placements_params.shape != (num_points, dimension):
    return -np.inf
  if np.isnan(placements_params).any():
    return -np.inf

  placements_copy = placements_params.copy()
  norms = np.linalg.norm(placements_copy, axis=1)
  if np.any(norms < 1e-9):
    return 0.0
  placements_copy /= norms[:, np.newaxis]

  try:
    hull = ConvexHull(placements_copy, qhull_options='QJ')
  except (QhullError, ValueError):
    return 0.0

  total_volume = 0.0
  try:
    d_factorial = float(math.factorial(dimension))
  except ValueError:
    return 0.0

  for simplex_indices in hull.simplices:
    facet_vertices = placements_copy[simplex_indices]
    sign, logdet = np.linalg.slogdet(facet_vertices)
    if sign != 0:
      volume_of_simplex = np.exp(logdet) / d_factorial
      total_volume += volume_of_simplex

  return total_volume
