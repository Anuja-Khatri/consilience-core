# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/erdos_squares_in_a_square/erdos_squares_in_a_square.ipynb, notebook code cells 0 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import re
import numba
import numpy as np

#@title Verification code

# pylint: disable=unused-import
# pylint: disable=g-bad-import-order

njit = numba.njit






# Helper functions for geometry calculations (Numba-optimized)
@njit
def get_square_vertices(x, y, angle_norm, s):
  """Calculates the 4 vertices of a square given its center, normalized angle [0,1], and side length."""
  # Convert normalized angle to radians
  angle_rad = angle_norm * 2 * np.pi
  cos_a = np.cos(angle_rad)
  sin_a = np.sin(angle_rad)
  half_s = s / 2.0
  # Calculate vectors from center to corners
  dx1 = half_s * cos_a
  dy1 = half_s * sin_a
  dx2 = half_s * -sin_a
  dy2 = half_s * cos_a
  vertices = np.empty((4, 2), dtype=np.float64)
  # Calculate vertex coordinates
  vertices[0, :] = (x + dx1 + dx2, y + dy1 + dy2)
  vertices[1, :] = (x - dx1 + dx2, y - dy1 + dy2)
  vertices[2, :] = (x - dx1 - dx2, y - dy1 - dy2)
  vertices[3, :] = (x + dx1 - dx2, y + dy1 - dy2)
  return vertices


@njit
def square_in_unit_square(x, y, angle_norm, s):
  """Checks if a square is fully contained within the unit square [0,1]x[0,1]."""
  if s < -1e-9:
    return False  # Side length cannot be negative
    # (allow small tolerance for float errors)
  if s <= 1e-9:
    return (
        0.0 <= x <= 1.0 and 0.0 <= y <= 1.0
    )  # Point square is valid if center is inside

  vertices = get_square_vertices(x, y, angle_norm, s)
  for i in range(4):
    vx, vy = vertices[i, 0], vertices[i, 1]
    # Check if vertex is within the unit square boundaries (with small
    # tolerance)
    if not (-1e-9 <= vx <= 1.0 + 1e-9 and -1e-9 <= vy <= 1.0 + 1e-9):
      return False
  return True


@njit
def project_vertices(vertices, axis):
  """Projects square vertices onto a given axis and returns the min/max projection values."""
  min_proj = np.inf
  max_proj = -np.inf
  for i in range(4):
    projection = vertices[i, 0] * axis[0] + vertices[i, 1] * axis[1]
    min_proj = min(min_proj, projection)
    max_proj = max(max_proj, projection)
  return min_proj, max_proj


@njit
def get_axes(vertices):
  """Gets the normalized axes perpendicular to the edges of the square."""
  axes = np.empty(
      (2, 2), dtype=np.float64
  )  # A square only has 2 unique edge orientations
  for i in range(2):  # Check first two edges, others are parallel
    p1 = vertices[i]
    p2 = vertices[(i + 1)]  # % 4 not needed as we only take first 2
    edge = p2 - p1
    # Get perpendicular vector (normal)
    normal = np.array([-edge[1], edge[0]])
    # Normalize the axis
    norm = np.sqrt(normal[0] ** 2 + normal[1] ** 2)
    if norm < 1e-9:  # Should not happen for a square with s > 0
      # Return zero vector axes to indicate degeneracy or handle upstream?
      # Returning potentially invalid axes here might be problematic.
      # Let's return empty or handle s=0 earlier.
      # Assuming s>0 here based on checks in squares_intersect.
      axes[i, 0] = 0.0  # Or handle error case
      axes[i, 1] = 0.0
    else:
      axes[i, 0] = normal[0] / norm
      axes[i, 1] = normal[1] / norm
  return axes


@njit
def squares_intersect(sq1_params, sq2_params):
  """Checks if two squares intersect using the Separating Axis Theorem (SAT)."""
  x1, y1, angle1_norm, s1 = sq1_params
  x2, y2, angle2_norm, s2 = sq2_params

  # Squares with zero or near-zero side length don't have an interior to overlap
  if s1 <= 1e-9 or s2 <= 1e-9:
    return False

  vertices1 = get_square_vertices(x1, y1, angle1_norm, s1)
  vertices2 = get_square_vertices(x2, y2, angle2_norm, s2)

  axes1 = get_axes(vertices1)
  axes2 = get_axes(vertices2)

  # Check axes from square 1
  for i in range(axes1.shape[0]):
    axis = axes1[i]
    # Skip if axis is degenerate (can happen if get_axes failed)
    if np.sqrt(axis[0] ** 2 + axis[1] ** 2) < 1e-9:
      continue
    min1, max1 = project_vertices(vertices1, axis)
    min2, max2 = project_vertices(vertices2, axis)
    # Check for separation
    if (
        max1 < min2 - 1e-9 or max2 < min1 - 1e-9
    ):  # Use tolerance for float comparison
      return False  # Found a separating axis

  # Check axes from square 2
  for i in range(axes2.shape[0]):
    axis = axes2[i]
    # Skip if axis is degenerate
    if np.sqrt(axis[0] ** 2 + axis[1] ** 2) < 1e-9:
      continue
    min1, max1 = project_vertices(vertices1, axis)
    min2, max2 = project_vertices(vertices2, axis)
    # Check for separation
    if max1 < min2 - 1e-9 or max2 < min1 - 1e-9:  # Use tolerance
      return False  # Found a separating axis

  # No separating axis found means they intersect
  return True


@njit
def check_constraints_and_calculate_score_numba(squares_array, n):
  """Numba-optimized function to check constraints and calculate score."""
  total_side_length = 0.0

  # 1. Check containment and sum side lengths
  for i in range(n):
    params = squares_array[i]
    # Clamp values just in case mutation produced slightly out-of-bounds numbers
    x = min(max(params[0], 0.0), 1.0)
    y = min(max(params[1], 0.0), 1.0)
    angle_norm = params[2] % 1.0  # Wrap angle
    if angle_norm < 0:
      angle_norm += 1.0
    s = max(params[3], 0.0)  # Ensure non-negative side length

    squares_array[i] = np.array(
        [x, y, angle_norm, s]
    )  # Update array with clamped values

    if not square_in_unit_square(x, y, angle_norm, s):
      return -1_000_000.0  # Square not fully contained
    total_side_length += s

  # 2. Check intersection for all pairs
  for i in range(n):
    for j in range(i + 1, n):
      if squares_intersect(squares_array[i], squares_array[j]):
        return -1_000_000.0  # Found intersection

  # 3. All checks passed, return sum of side lengths
  return total_side_length


def calculate_packing_score(squares_params, n):
  """Calculates the score (sum of side lengths) for square packing."""
  # 1. Basic validation
  if not isinstance(squares_params, list):
    return -1_000_000.0
  if len(squares_params) != n:
    return -1_000_000.0

  current_squares_list = []
  for _, p in enumerate(squares_params):
    # Check type and length of parameters for each square
    if not isinstance(p, (tuple, list)) or len(p) != 4:
      return -1_000_000.0
    try:
      # Convert to float, check for NaN/inf
      params_float = [float(val) for val in p]
      if any(np.isnan(v) or v > 1 or v < 0 for v in params_float):
        return -1_000_000.0
      current_squares_list.append(np.array(params_float, dtype=np.float64))
    except (ValueError, TypeError):
      return -1_000_000.0  # Parameter conversion failed

  # Handle case where n=0 or conversion failed for all
  if not current_squares_list:
    if n == 0:
      return 0.0
    else:
      return -1_000_000.0

  # Convert list of numpy arrays to a 2D numpy array for Numba
  squares_array = np.array(current_squares_list)

  # Call the Numba-optimized checking and scoring function
  score = check_constraints_and_calculate_score_numba(squares_array, n)
  return score


def format_feedback_repr(feedback):
  """Formats feedback dictionary for representation in code."""
  formatted_feedback = {}
  np.set_printoptions(threshold=np.inf)
  for key, value in feedback.items():
    if isinstance(value, np.ndarray):
      repr_str = repr(value)  # Get repr string (e.g., "array([[...], [...]])")
      cleaned_repr_str = re.sub(
          r'[\n\s]+', ' ', repr_str
      )  # Clean up whitespace

      # Extract content inside "array(...)"
      # Handle potential differences in np.array repr format if needed
      match = re.match(r'array\((.*)\)', cleaned_repr_str, re.DOTALL)
      if match:
        array_content = match.group(1).strip()
        # Remove dtype=... if present, re-add based on actual dtype
        array_content = re.sub(r', dtype=[\w.]+', '', array_content)
      else:
        # Fallback or error handling if repr string is not as expected
        print(f'Warning: Could not parse numpy array repr: {repr_str}')
        array_content = '[]'  # Default to empty list

      if np.iscomplexobj(value):
        formatted_feedback[key] = (
            f'np.array({array_content}, dtype=np.complex128)'
        )
      # Check if it's an integer type NOT bool
      elif np.issubdtype(value.dtype, np.integer) and not np.issubdtype(
          value.dtype, np.bool_
      ):
        formatted_feedback[key] = (  # Or appropriate int type
            f'np.array({array_content}, dtype=np.int64)'
        )
      # Check specifically for float64 or other float types if needed
      elif np.issubdtype(value.dtype, np.floating):
        formatted_feedback[key] = (  # Ensure float64 for consistency
            f'np.array({array_content}, dtype=np.float64)'
        )
      else:  # Fallback for other types like bool, object, etc.
        formatted_feedback[key] = (
            f'np.array({array_content})'  # Let numpy decide dtype from content
        )

    elif isinstance(value, list):
      # Ensure lists contain tuples, consistent with search function output
      # format Convert internal lists back to tuples if needed
      formatted_list = [
          tuple(item) if isinstance(item, list) else item for item in value
      ]
      formatted_feedback[key] = repr(formatted_list)
    elif isinstance(value, tuple):
      # Ensure tuples contain tuples if nested, consistent with search output
      formatted_tuple = tuple(
          tuple(item) if isinstance(item, list) else item for item in value
      )
      formatted_feedback[key] = repr(formatted_tuple)
    else:
      formatted_feedback[key] = repr(value)  # Use standard repr for other types
  return formatted_feedback


def evaluate(n: int) -> tuple[dict[str, float], dict[str, str]]:
  """Evaluates square packing for nsquares."""
  result = {}
  feedback = {}
  # Calculate number of squares based on input k

  # Call the search function to find the best packing configuration
  best_squares_params_list = search_for_best_squares(n)

  # Validate the output format from the search function
  if (
      not isinstance(best_squares_params_list, list)
      or len(best_squares_params_list) != n
      or not all(
          isinstance(p, tuple) and len(p) == 4 for p in best_squares_params_list
      )
  ):
    print(
        f'Error: Search function returned unexpected format for n={n}. Output:'
        f' {best_squares_params_list}'
    )
    score = -1_000_000.0
    # Provide default feedback format or indicate error
    feedback_params_np = np.array([])
    feedback['error'] = 'Search function output invalid'
  else:
    # Calculate the score of the best configuration found
    # Pass the list of tuples directly to the score function
    score = calculate_packing_score(best_squares_params_list, n)

    # Convert the final list of tuples to a numpy array for feedback
    # This ensures consistent format for the PREVIOUS CONSTRUCTIONS block
    try:
      feedback_params_np = np.array(best_squares_params_list, dtype=np.float64)
      # Check if conversion resulted in the correct shape
      if feedback_params_np.shape != (n, 4):
        print(
            'Warning: Conversion to numpy array resulted in unexpected shape:'
            f' {feedback_params_np.shape}'
        )
        # Decide how to handle this: fallback or proceed with caution
        # Fallback to empty array for safety in feedback:
        # feedback_params_np = np.array([])
        # Or try to reshape if appropriate, but risky if data is wrong
    except (ValueError, TypeError) as e:
      print(f'Error converting best parameters to numpy array: {e}')
      feedback_params_np = np.array([])  # Fallback
      feedback['error'] = 'Failed to convert result to numpy array'
      # Adjust score maybe? If conversion fails, result might be unusable.
      # Score might already be -1e6 if params were bad, but double-check.
      score = min(score, -1_000_000.0)  # Ensure score reflects potential issue

  # Store results and feedback
  result['score'] = score
  feedback['best_score_found'] = score
  # The key must match the variable name used in the search function's loading
  # logic
  feedback_key = 'placed_squares'
  feedback[feedback_key] = feedback_params_np

  # Format feedback dictionary values into representation strings
  formatted_feedback = format_feedback_repr(feedback)

  return result, formatted_feedback
