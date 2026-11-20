# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/packing_circles_max_sum_of_radii/packing_circles_max_sum_of_radii.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np


def _circles_overlap(centers, radii):
  """Protected function to compute max radii."""
  n = centers.shape[0]

  for i in range(n):
    for j in range(i + 1, n):
      dist = np.sqrt(np.sum((centers[i] - centers[j]) ** 2))
      if radii[i] + radii[j] > dist:
        return True

  return False


def check_construction(centers, radii, n) -> dict[str, float]:
  """Evaluates circle packing for maximizing sum of radii in unit square."""

  # General checks for the whole array
  if centers.shape != (n, 2) or not np.isfinite(centers).all():
    print(
        "Error: The 'centers' array has an invalid shape or non-finite values."
    )
    return {'sum_of_radii': -np.inf}

  # --- Start of the modified geometric check ---

  # 1. Check each circle individually to see if it's contained
  is_contained = (
      (radii[:, None] <= centers) & (centers <= 1 - radii[:, None])
  ).all(axis=1)

  # 2. If not all of them are contained...
  if not is_contained.all():
    return {'sum_of_radii': -np.inf}

  if (
      radii.shape != (n,)
      or not np.isfinite(radii).all()
      or not (0 <= radii).all()
  ):
    print('radii bad shape')
    return {'sum_of_radii': -np.inf}

  if _circles_overlap(centers, radii):
    print('circles overlap')
    return {'sum_of_radii': -np.inf}

  print("The circles are disjoint and lie inside the unit square.")
  return {'sum_of_radii': float(np.sum(radii))}
