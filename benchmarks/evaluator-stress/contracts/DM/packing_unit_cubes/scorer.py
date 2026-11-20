# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/packing_unit_cubes/packing_unit_cubes.ipynb, notebook code cells 2 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
from typing import List, Tuple


NUM_CUBES_IN_CORNERS = 8


def rotation_matrix_3d(x_angle_deg, y_angle_deg, z_angle_deg):
  """Generates a 3D rotation matrix from Euler angles (XYZ convention)."""
  x_angle_rad = np.deg2rad(x_angle_deg)
  y_angle_rad = np.deg2rad(y_angle_deg)
  z_angle_rad = np.deg2rad(z_angle_deg)
  cos_x, sin_x = np.cos(x_angle_rad), np.sin(x_angle_rad)
  cos_y, sin_y = np.cos(y_angle_rad), np.sin(y_angle_rad)
  cos_z, sin_z = np.cos(z_angle_rad), np.sin(z_angle_rad)

  rotation_x = np.array([[1, 0, 0], [0, cos_x, -sin_x], [0, sin_x, cos_x]])
  rotation_y = np.array([[cos_y, 0, sin_y], [0, 1, 0], [-sin_y, 0, cos_y]])
  rotation_z = np.array([[cos_z, -sin_z, 0], [sin_z, cos_z, 0], [0, 0, 1]])

  return rotation_z @ rotation_y @ rotation_x


def get_cube_vertices(center, rotation_matrix, side_length=1.0):
  """Calculates the world coordinates of a cube's vertices."""
  half_side = side_length / 2.0
  local_vertices = np.array([
      [-half_side, -half_side, -half_side],
      [-half_side, -half_side, half_side],
      [-half_side, half_side, -half_side],
      [-half_side, half_side, half_side],
      [half_side, -half_side, -half_side],
      [half_side, -half_side, half_side],
      [half_side, half_side, -half_side],
      [half_side, half_side, half_side],
  ])
  return (local_vertices @ rotation_matrix.T) + center


def get_cube_axes(rotation_matrix):
  """Calculates the axes to test for SAT, which are the face normals."""
  local_axes = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
  return local_axes @ rotation_matrix.T


def project_cube_onto_axis(vertices, axis):
  """Projects a cube's vertices onto an axis."""
  projections = vertices @ axis
  return np.min(projections), np.max(projections)


def do_cubes_intersect(vertices1, vertices2, axes1, axes2):
  """Checks for intersection between two cubes using the full Separating Axis Theorem."""
  # Combine the 6 face-normal axes from both cubes
  axes_to_test = list(axes1) + list(axes2)

  # **CORRECTION**: Add the 9 axes from the cross products of the cubes' axes.
  # This is the part that was missing from the original.
  for i in range(3):
    for j in range(3):
      cross_product = np.cross(axes1[i], axes2[j])
      # Add the axis only if it's not a zero vector (avoids parallel axes)
      if np.linalg.norm(cross_product) > 1e-6:
        axes_to_test.append(cross_product)

  # Test for separation along all 15 (or fewer) axes
  for axis in axes_to_test:
    min1, max1 = project_cube_onto_axis(vertices1, axis)
    min2, max2 = project_cube_onto_axis(vertices2, axis)

    # If there is no overlap on any axis, the cubes do not intersect
    if max1 < min2 - 1e-9 or max2 < min1 - 1e-9:
      return False  # Found a separating axis

  # If no separating axis was found after checking all potential axes,
  # the cubes must be intersecting.
  return True


def min_bounding_cube_extent_3d(all_vertices):
  """Calculates the side length of the minimum axis-aligned bounding cube."""
  if not all_vertices:
    return 0, np.array([0, 0, 0]), np.array([0, 0, 0])
  all_vertices_np = np.vstack(all_vertices)
  min_coords = np.min(all_vertices_np, axis=0)
  max_coords = np.max(all_vertices_np, axis=0)
  side_lengths = max_coords - min_coords
  return np.max(side_lengths), min_coords, max_coords


def calculate_packing_score_cubes_3d(
    placements: List[Tuple],
    num_cubes: int,
    intersection_penalty_factor=100.0,
    return_adjusted_coordinates=True,
    verbose=False,
):
  """Calculates the score for a 3D cube packing configuration."""
  if not placements or len(placements) != num_cubes:
    return -1_000_000.0

  try:
    # Create a working copy of placements to modify
    final_placements = [list(p) for p in placements]

    # Determine the bounding box of the initial "free" cubes
    _, min_b, max_b = min_bounding_cube_extent_3d([
        get_cube_vertices(p[:3], rotation_matrix_3d(p[3], p[4], p[5]))
        for p in final_placements
    ])

    if verbose:
      print(f'Initial bounding box: {min_b}, {max_b}')

    # Set the positions for the corner cubes
    num_corner_cubes = min(num_cubes, NUM_CUBES_IN_CORNERS)
    if num_corner_cubes > 0:
      corner_centers = [
          np.array([min_b[0] + 0.5, min_b[1] + 0.5, min_b[2] + 0.5]),
          np.array([min_b[0] + 0.5, min_b[1] + 0.5, max_b[2] - 0.5]),
          np.array([min_b[0] + 0.5, max_b[1] - 0.5, min_b[2] + 0.5]),
          np.array([min_b[0] + 0.5, max_b[1] - 0.5, max_b[2] - 0.5]),
          np.array([max_b[0] - 0.5, min_b[1] + 0.5, min_b[2] + 0.5]),
          np.array([max_b[0] - 0.5, min_b[1] + 0.5, max_b[2] - 0.5]),
          np.array([max_b[0] - 0.5, max_b[1] - 0.5, min_b[2] + 0.5]),
          np.array([max_b[0] - 0.5, max_b[1] - 0.5, max_b[2] - 0.5]),
      ]
      for i in range(num_corner_cubes):
        final_placements[i][:3] = corner_centers[i]
        final_placements[i][3:] = [0, 0, 0]

    # NOW, calculate the definitive geometry based on the final placements
    rotation_matrices = [
        rotation_matrix_3d(p[3], p[4], p[5]) for p in final_placements
    ]
    all_vertices = [
        get_cube_vertices(p[:3], rot)
        for p, rot in zip(final_placements, rotation_matrices)
    ]
    all_axes = [get_cube_axes(rot) for rot in rotation_matrices]

    # The REAL side length is from the final, arranged configuration
    final_side_length, _, _ = min_bounding_cube_extent_3d(all_vertices)

    # Check for intersections
    intersection_count = 0
    for i in range(num_cubes):
      for j in range(i + 1, num_cubes):
        if do_cubes_intersect(
            all_vertices[i], all_vertices[j], all_axes[i], all_axes[j]
        ):
          intersection_count += 1
          if verbose:
            print(f'Intersection between cubes {i} and {j}')
            print(f'Vertices: {all_vertices[i]},\n {all_vertices[j]}')
            print(f'Axes: {all_axes[i]}, {all_axes[j]}')
            print(f'Minimum bounding box: {final_side_length}')

    score = (
        -final_side_length - intersection_count * intersection_penalty_factor
    )
    if return_adjusted_coordinates:
      return score, final_placements
    return score

  except (ValueError, IndexError) as e:
    return -1_000_002.0
