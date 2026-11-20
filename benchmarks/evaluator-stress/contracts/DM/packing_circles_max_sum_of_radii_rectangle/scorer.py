# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/packing_circles_max_sum_of_radii/packing_circles_max_sum_of_radii.ipynb, notebook code cells 10 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
import itertools


def _circles_overlap(centers, radii):
  """Protected function to compute max radii."""
  n = centers.shape[0]

  for i in range(n):
    for j in range(i + 1, n):
      dist = np.sqrt(np.sum((centers[i] - centers[j]) ** 2))
      if radii[i] + radii[j] > dist:
        return True

  return False


def check_construction_rectangle(centers: np.ndarray, radii: np.ndarray, n: int, width: float, height: float) -> dict[str, float]:
  """
  Evaluates a circle packing in a rectangle.

  Checks if all circles are contained within the rectangle and do not overlap.
  Provides detailed diagnostics for any violations, distinguishing between
  genuine errors and potential floating-point precision issues.

  Args:
    centers: A numpy array of shape (n, 2) with the (x, y) coordinates of the circle centers.
    radii: A numpy array of shape (n,) with the radii of the circles.
    n: The number of circles.
    width: The width of the rectangle.
    height: The height of the rectangle.

  Returns:
    A dictionary containing the sum of radii if the packing is valid,
    or -np.inf if it is invalid.
  """

  TOLERANCE = 1e-9 # Tolerance for floating-point comparisons

  # --- Start of checks for rectangle geometry ---
  # 1. Check if width and height are finite, real numbers.
  if not np.all(np.isfinite([width, height])) or not np.isrealobj(
      np.array([width, height])
  ):
    print(f'Error: Invalid width or height. Must be finite real numbers.')
    return {'sum_of_radii': -np.inf}

  # 2. Check if the rectangle's perimeter is 4.
  if not np.isclose(2 * (width + height), 4.0):
    print(f'Error: Perimeter is not 4. Got {2 * (width + height)}')
    return {'sum_of_radii': -np.inf}

  # 3. Check for valid, non-degenerate rectangle dimensions.
  if width <= 0 or height <= 0:
    print(
        f'Error: Invalid rectangle dimensions. width={width}, height={height}'
    )
    return {'sum_of_radii': -np.inf}
  # --- End of rectangle checks ---

  # General checks for the input arrays
  if (
      centers.shape != (n, 2)
      or not np.isfinite(centers).all()
      or not np.isrealobj(centers)
  ):
    print(
        "Error: The 'centers' array has an invalid shape, non-finite, or"
        ' complex values.'
    )
    return {'sum_of_radii': -np.inf}

  # --- Geometric check for circle containment ---
  # 1. Check each circle individually to see if it's contained
  is_contained = (
      (radii[:, None] <= centers)
      & (centers <= np.array([width, height]) - radii[:, None])
  ).all(axis=1)

  # 2. If not all of them are contained, print diagnostics
  if not is_contained.all():
    print('Error: Circles are not contained within the rectangle.')
    for i, contained in enumerate(is_contained):
      if not contained:
        print(f'-> Diagnostics for Circle {i}:')
        c_i = centers[i]
        r_i = radii[i]
        # Check violation for each of the four boundaries
        violations = {
            'left': r_i - c_i[0],
            'right': c_i[0] - (width - r_i),
            'bottom': r_i - c_i[1],
            'top': c_i[1] - (height - r_i),
        }
        for boundary, violation_amount in violations.items():
          if violation_amount > TOLERANCE:
            print(f'  - Genuinely violates {boundary} boundary by {violation_amount:.4g}')
          elif violation_amount > 0:
            print(f'  - Potential precision error at {boundary} boundary. Violation: {violation_amount:.4g}')

    return {'sum_of_radii': -np.inf}

  # --- Geometric check for circle overlaps ---
  if n > 1:
    has_overlap = False
    # Iterate over every unique pair of circles
    for i, j in itertools.combinations(range(n), 2):
      center_dist_sq = np.sum((centers[i] - centers[j]) ** 2)
      radii_sum_sq = (radii[i] + radii[j]) ** 2

      # Check if squared distance is less than squared sum of radii
      if center_dist_sq < radii_sum_sq:
        if not has_overlap: # Print header only once
          print('Error: Circles are overlapping.')
          has_overlap = True

        overlap_sq = radii_sum_sq - center_dist_sq
        # Distinguish between genuine overlap and touching circles (precision issue)
        if overlap_sq > TOLERANCE:
          print(f'  - Genuinely overlapping: Circles {i} and {j}. Squared overlap: {overlap_sq:.4g}')
        else:
          print(f'  - Potential precision error: Circles {i} and {j} are touching/minutely overlapping. Squared overlap: {overlap_sq:.4g}')

    if has_overlap:
      return {'sum_of_radii': -np.inf}

  if (
      radii.shape != (n,)
      or not np.isfinite(radii).all()
      or not (0 <= radii).all()
      or not np.isrealobj(radii)  # Added check for real numbers
  ):
    print('radii bad shape or contains non-real/non-finite values')
    return {'sum_of_radii': -np.inf}

  if _circles_overlap(centers, radii):
    print('circles overlap')
    return {'sum_of_radii': -np.inf}, {}

  print(
      f'Valid packing found with width={width}, height={height},'
      f' sum_radii={np.sum(radii)}'
  )

  print("The circles are disjoint and lie inside the rectangle.")
  return {'sum_of_radii': float(np.sum(radii))}
