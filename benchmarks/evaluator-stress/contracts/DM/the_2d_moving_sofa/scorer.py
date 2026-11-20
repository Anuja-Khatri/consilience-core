# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/the_2d_moving_sofa/the_2d_moving_sofa.ipynb, notebook code cells 1,2 (0-based, counting code cells only), functions Corridor, calculate_intersection_area, smooth_path (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import transform

class Corridor:

  def __init__(self):
    """Initializes the corridor.

    Args:
        turns: A list of tuples, where each tuple represents a turn:
          (distance_before_turn, turn_angle_degrees) The first segment starts at
          (0, 0) and extends along the x-axis.
    """
    self.width = 1

  def get_corridor_shape(self, angle_degrees, inner_corner_path):
    """Calculates the polygon representing the corridor at a given angle and inner corner position.

    Args:
        angle_degrees: The current rotation angle of the corridor.
        inner_corner_path: A point (x, y) representing the inner corner.

    Returns:
        A shapely Polygon object representing the corridor.
    """
    angle_radians = np.deg2rad(angle_degrees)
    x_inner, y_inner = inner_corner_path

    big_const = 3

    points = [
        (0, 0),
        (0, -big_const * self.width),
        (self.width, -big_const * self.width),
        (self.width, self.width),
        (-big_const * self.width, self.width),
        (-big_const * self.width, 0),
    ]
    corridor_polygon = Polygon(points)

    # Rotate the corridor
    rotated_polygon = transform(
        lambda x, y: (
            x * np.cos(angle_radians) - y * np.sin(angle_radians),
            x * np.sin(angle_radians) + y * np.cos(angle_radians),
        ),
        corridor_polygon,
    )

    # Translate the corridor so its inner corner is at inner_corner_path
    translated_polygon = transform(
        lambda x, y: (x + x_inner, y + y_inner), rotated_polygon
    )

    return translated_polygon


def calculate_intersection_area(corridor, curr_path):
  """Calculates the area of the intersection of the corridor at different rotations/translations.

  Args:
      corridor: A Corridor object defining the corridor geometry.
      curr_path: A list of (x, y) tuples representing the inner corner path.
      total_turn_angle: The total angle in degrees for the corridor's rotation.

  Returns:
      The area of the intersection polygon.
  """
  curr_path = smooth_path(curr_path)
  intersection = None
  num_steps = len(curr_path)
  new_path = [(0, 0, 0)] + curr_path + [(-2, 0, 90)]

  for i in range(num_steps + 1):
    alpha_degrees = new_path[i][2]
    path_point = new_path[i][0:2]
    current_corridor = corridor.get_corridor_shape(alpha_degrees, path_point)

    if intersection is None:
      intersection = current_corridor
    else:
      intersection = intersection.intersection(current_corridor)

    if intersection.is_empty:
      return 0.0, intersection

  return intersection.area, intersection


def smooth_path(input_path):
  """Smoothens a path by inserting points so that the third element

  differs by at most one between consecutive points.

  Args:
    path: A list of lists, where each inner list has three numbers.

  Returns:
    A new list of lists representing the smoothened path.
  """
  path = [[0, 0, 0]] + input_path + [[-2, 0, 90]]
  smoothed_path = []
  if not path:
    return smoothed_path

  smoothed_path.append(path[0])

  for i in range(len(path) - 1):
    start_point = np.array(path[i])
    end_point = np.array(path[i + 1])

    start_z = int(start_point[2])
    end_z = int(end_point[2])

    if start_z == end_z:
      continue  # No need to insert points

    step = 1 if end_z > start_z else -1
    num_intermediate_points = abs(end_z - start_z) - 1

    if num_intermediate_points > 0:
      # Create the linearly spaced z values for the intermediate points
      intermediate_zs = np.arange(start_z + step, end_z, step)

      # Calculate the weights for the weighted average of x and y
      weights = np.linspace(0, 1, num_intermediate_points + 2)[
          1:-1
      ]  # Exclude 0 and 1

      for z_val, weight in zip(intermediate_zs, weights):
        intermediate_xy = (
            start_point[:2] * (1 - weight) + end_point[:2] * weight
        )
        smoothed_path.append(list(intermediate_xy) + [z_val])

    smoothed_path.append(path[i + 1])

  return smoothed_path
