# Vendored from https://github.com/google-deepmind/alphaevolve_results @ 4226acbf237ff9ad10ba7673a2af127a2d8a5971, mathematical_results.ipynb, notebook cell 86 (0-based over all cells; B.7 '#@title Verification code', verify_construction and helpers) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
#@title Verification code

import numpy as np
import math
import matplotlib.pyplot as plt


def hexagon_vertices(
    center_x: float,
    center_y: float,
    side_length: float,
    angle_degrees: float,
) -> list[tuple[float, float]]:
  """Generates the vertices of a regular hexagon.

  Args:
    center_x: x-coordinate of the center.
    center_y: y-coordinate of the center.
    side_length: Length of each side.
    angle_degrees: Rotation angle in degrees (clockwise from horizontal).

  Returns:
    A list of tuples, where each tuple (x, y) represents the vertex location.
  """
  vertices = []
  angle_radians = math.radians(angle_degrees)
  for i in range(6):
    angle = angle_radians + 2 * math.pi * i / 6
    x = center_x + side_length * math.cos(angle)
    y = center_y + side_length * math.sin(angle)
    vertices.append((x, y))
  return vertices


def normalize_vector(v: tuple[float, float]) -> tuple[float, float]:
  """Normalizes a 2D vector."""
  magnitude = math.sqrt(v[0]**2 + v[1]**2)
  return (v[0] / magnitude, v[1] / magnitude) if magnitude != 0 else (0., 0.)


def get_normals(
    vertices: list[tuple[float, float]]
) -> list[tuple[float, float]]:
  """Gets the outward normals of a polygon's edges."""
  normals = []
  for i in range(len(vertices)):
    p1 = vertices[i]
    p2 = vertices[(i + 1) % len(vertices)]  # Wrap around to the first vertex.
    edge = (p2[0] - p1[0], p2[1] - p1[1])
    normal = normalize_vector((-edge[1], edge[0]))  # Rotate edge by 90 degrees.
    normals.append(normal)
  return normals


def project_polygon(
    vertices: list[tuple[float, float]],
    axis: tuple[float, float],
) -> tuple[float, float]:
  """Projects a polygon onto an axis and returns the min/max values."""
  min_proj = float('inf')
  max_proj = float('-inf')
  for vertex in vertices:
    projection = vertex[0] * axis[0] + vertex[1] * axis[1]  # Dot product.
    min_proj = min(min_proj, projection)
    max_proj = max(max_proj, projection)
  return min_proj, max_proj


def overlap_1d(min1: float, max1: float, min2: float, max2: float) -> bool:
  """Determines whether two 1D intervals overlap."""
  return max1 >= min2 and max2 >= min1


def polygons_intersect(
    vertices1: list[tuple[float, float]],
    vertices2: list[tuple[float, float]],
) -> bool:
  """Determines if two polygons intersect using the Separating Axis Theorem."""
  normals1 = get_normals(vertices1)
  normals2 = get_normals(vertices2)
  axes = normals1 + normals2

  for axis in axes:
    min1, max1 = project_polygon(vertices1, axis)
    min2, max2 = project_polygon(vertices2, axis)
    if not overlap_1d(min1, max1, min2, max2):
      return False  # Separating axis found, polygons are disjoint.
  return True  # No separating axis found, polygons intersect.


def hexagons_are_disjoint(
    hex1_params: tuple[float, float, float, float],
    hex2_params: tuple[float, float, float, float],
) -> bool:
  """Determines if two hexagons are disjoint given their parameters."""
  hex1_vertices = hexagon_vertices(*hex1_params)
  hex2_vertices = hexagon_vertices(*hex2_params)
  return not polygons_intersect(hex1_vertices, hex2_vertices)


def is_inside_hexagon(
    point: tuple[float, float],
    hex_params: tuple[float, float, float, float],
) -> bool:
  """Checks if a point is inside a hexagon (given its parameters)."""
  hex_vertices = hexagon_vertices(*hex_params)
  for i in range(len(hex_vertices)):
    p1 = hex_vertices[i]
    p2 = hex_vertices[(i + 1) % len(hex_vertices)]
    edge_vector = (p2[0] - p1[0], p2[1] - p1[1])
    point_vector = (point[0] - p1[0], point[1] - p1[1])
    cross_product = (
        edge_vector[0] * point_vector[1] - edge_vector[1] * point_vector[0]
    )
    if cross_product < 0:
      return False
  return True


def all_hexagons_contained(
    inner_hex_params_list: list[tuple[float, float, float, float]],
    outer_hex_params: tuple[float, float, float, float],
) -> bool:
  """Checks if all inner hexagons are contained within the outer hexagon."""
  for inner_hex_params in inner_hex_params_list:
    inner_hex_vertices = hexagon_vertices(*inner_hex_params)
    for vertex in inner_hex_vertices:
      if not is_inside_hexagon(vertex, outer_hex_params):
        return False
  return True


def verify_construction(
    inner_hex_data: tuple[float, float, float],
    outer_hex_center: tuple[float, float],
    outer_hex_side_length: float,
    outer_hex_angle_degrees: float,
):
  """Verifies the hexagon packing construction with a rotated outer hexagon.

  Args:
    inner_hex_data: List of (x, y, angle_degrees) tuples for inner hexagons.
    outer_hex_center: (x, y) tuple for the outer hexagon center.
    outer_hex_side_length: Side length of the outer hexagon.
    outer_hex_angle_degrees: Rotation angle of the outer hexagon in degrees.

  Raises:
    AssertionError if the construction is not valid.
  """

  inner_hex_params_list = [
      (x, y, 1, angle) for x, y, angle in inner_hex_data
  ]  # Sets the side length to 1.
  outer_hex_params = (
      outer_hex_center[0], outer_hex_center[1],
      outer_hex_side_length, outer_hex_angle_degrees
  )

  # Disjointness check.
  for i in range(len(inner_hex_params_list)):
    for j in range(i + 1, len(inner_hex_params_list)):
      if not hexagons_are_disjoint(
          inner_hex_params_list[i], inner_hex_params_list[j]
      ):
        raise AssertionError(f"Hexagons {i+1} and {j+1} intersect!")

  # Containment check.
  if not all_hexagons_contained(inner_hex_params_list, outer_hex_params):
    raise AssertionError(
        "Not all inner hexagons are contained in the outer hexagon!"
    )

  print("Construction is valid.")
