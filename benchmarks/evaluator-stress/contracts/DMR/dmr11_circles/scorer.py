# Vendored from https://github.com/google-deepmind/alphaevolve_results @ 4226acbf237ff9ad10ba7673a2af127a2d8a5971, mathematical_results.ipynb, notebook cell 116 (0-based over all cells; B.12 '#@title Verification function', verify_circles) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
#@title Verification function
import numpy as np
import itertools

def verify_circles(circles: np.ndarray):
  """Checks that the circles are disjoint and lie inside a unit square.

    Args:
      circles: A numpy array of shape (num_circles, 3), where each row is
        of the form (x, y, radius), specifying a circle.

    Raises:
      AssertionError if the circles are not disjoint or do not lie inside the
      unit square.
  """
  # Check pairwise disjointness.
  for circle1, circle2 in itertools.combinations(circles, 2):
    center_distance = np.sqrt((circle1[0] - circle2[0])**2 + (circle1[1] - circle2[1])**2)
    radii_sum = circle1[2] + circle2[2]
    assert center_distance >= radii_sum, f"Circles are NOT disjoint: {circle1} and {circle2}."

  # Check all circles lie inside the unit square [0,1]x[0,1].
  for circle in circles:
    assert (0 <= min(circle[0], circle[1]) - circle[2] and max(circle[0],circle[1]) + circle[2] <= 1), f"Circle {circle} is NOT fully inside the unit square."
