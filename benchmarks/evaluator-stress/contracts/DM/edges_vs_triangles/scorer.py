# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/edges_vs_triangles/edges_vs_triangles.ipynb, notebook code cells 0 (0-based, counting code cells only), functions sum_pairwise_triple_products_batch, analyze_density_curve, get_score (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import warnings
import numpy as np

def sum_pairwise_triple_products_batch(
    A: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
  """Calculates the sum of pairwise and triple products for each row of a 2D array.

  Args:
    A: A 2D numpy array of shape (M, N), where M is the number of lists and N is
      the size of each list (e.g., 20).

  Returns:
    A tuple containing two 1D numpy arrays:
    - pairwise_sums: Array of shape (M,) with sum_{i<j} a_i*a_j for each row.
    - triple_sums: Array of shape (M,) with sum_{i<j<k} a_i*a_j*a_k for each
    row.
  """
  if A.ndim != 2:
    raise ValueError(
        f'Input array must be 2-dimensional, but got shape {A.shape}'
    )

  M, N = A.shape

  triple_sums = np.zeros(M, dtype=A.dtype)
  # Handle cases where products are not possible
  if N < 2:
    pairwise_sums = np.zeros(M, dtype=A.dtype)
    return pairwise_sums, triple_sums

  # Calculate power sums along axis 1 (rows)
  # S1 will have shape (M,)
  S1 = np.sum(A, axis=1)
  # np.square(A) is element-wise, result (M, N). Sum along axis 1 -> shape (M,)
  S2 = np.sum(np.square(A), axis=1)

  # Calculate pairwise sums (shape M,)
  # All operations (**, *) are element-wise on the (M,) arrays S1, S2
  pairwise_sums = np.square(S1) - S2

  # Calculate triple sums only if N >= 3
  if N >= 3:
    # np.power(A, 3) is element-wise, result (M, N). Sum along axis 1 -> shape (M,)
    S3 = np.sum(np.power(A, 3), axis=1)
    # All operations (**, *) are element-wise on the (M,) arrays S1, S2, S3
    triple_sums = np.power(S1, 3) - 3 * S1 * S2 + 2 * S3
  # else triple_sums was already initialized to zeros if N < 3

  return pairwise_sums, triple_sums


def analyze_density_curve(
        edge_densities: np.ndarray,
    triangle_densities: np.ndarray,
    gap_range_min: float = 0.0,
    gap_range_max: float = 1.0,
) -> tuple[float, float]:
    """Calculates area under piecewise f defined by slope 3 capped by y_{i+1},
    and finds the max gap.

    f(0)=0, f(1)=1. f(xi)=yi.
    For xi <= x < x_{i+1}:
    - If yi > y_{i+1}, f(x) = yi (horizontal).
    - If yi <= y_{i+1}:
        - Start with slope 3 from (xi, yi).
        - If slope 3 reaches y_{i+1} at or before x reaches x_{i+1}:
            f increases with slope 3 until y=y_{i+1}, then is horizontal at y_{i+1}
            until x=x_{i+1}.
        - If slope 3 does not reach y_{i+1} by x=x_{i+1}:
            f increases with slope 3 for the entire interval.

    Args:
        edge_densities: 1D array of edge densities (x-coordinates).
        triangle_densities: 1D array of triangle densities (y-coordinates).
        gap_range_min: Min edge density for gap analysis.
        gap_range_max: Max edge density for gap analysis.

    Returns:
        Tuple (area, max_gap_in_range). Area under the capped slope-3 func.
    """
    if (
        edge_densities.shape != triangle_densities.shape
        or edge_densities.ndim != 1
    ):
        print(f"Invalid input shapes: {edge_densities.shape}, {triangle_densities.shape}")
        return -1.0, -1.0 # Indicate error

    # Prepare points including boundaries (0,0) and (1,1)
    if edge_densities.size > 0:
        sort_indices = np.argsort(edge_densities)
        sorted_x = edge_densities[sort_indices]
        sorted_y = triangle_densities[sort_indices]
        dtype = sorted_x.dtype
        full_x = np.concatenate(
            ([np.array(0.0, dtype=dtype)], sorted_x, [np.array(1.0, dtype=dtype)])
        )
        full_y = np.concatenate(
            ([np.array(0.0, dtype=dtype)], sorted_y, [np.array(1.0, dtype=dtype)])
        )
        # Remove duplicates based on x-values
        unique_full_x, unique_indices_full = np.unique(full_x, return_index=True)
        if len(unique_full_x) < len(full_x):
            #print('Note: Removing duplicate x-values after adding boundaries.')
            full_x = full_x[unique_indices_full]
            full_y = full_y[unique_indices_full]
    else:
        # Only boundary points if input is empty
        full_x = np.array([0.0, 1.0])
        full_y = np.array([0.0, 1.0])

    # Handle case where only one unique point remains (e.g., input was just [0])
    if len(full_x) < 2:
        # Area for (0,0) to (1,1) with capping:
        # xi=0, yi=0, x_next=1, y_next=1. yi <= y_next.
        # y_calc = 0 + 3*(1-0) = 3. y_calc > y_next. Case 2b.
        # x_hit = 0 + (1-0)/3 = 1/3. w1 = 1/3. w2 = 1 - 1/3 = 2/3.
        # Area = (0+1)/2 * w1 + 1 * w2 = 0.5 * (1/3) + 1 * (2/3) = 1/6 + 4/6 = 5/6
        area = 5.0 / 6.0
        max_gap = 1.0
        # Check if the single gap [0, 1) falls in the range
        if gap_range_min <= 0.0 < gap_range_max:
             max_gap_in_range = 1.0
        else:
             # No gap starts within the range if the only gap starts at 0 and 0 is excluded
             max_gap_in_range = 0.0 # Or return a specific indicator like None or np.nan? Sticking with 0.0 for now.

        # Return 1.0 if no gap qualified, consistent with previous versions' default
        # Let's return the actual max gap (1.0) if it qualifies, else 0.0.
        # If we want to return 1.0 default, uncomment the line below
        # max_gap_in_range = max_gap_in_range if max_gap_in_range > 0 else 1.0
        return area, max_gap_in_range


    # --- Calculate Area segment by segment ---
    total_area = 0.0
    slope = 3.0
    epsilon = 1e-9 # For floating point comparisons

    for i in range(len(full_x) - 1):
        xi = full_x[i]
        yi = full_y[i]
        x_next = full_x[i+1]
        y_next = full_y[i+1]

        w = x_next - xi
        if w < epsilon: # Skip zero-width segments
            continue

        # Case 1: yi > y_next (Use user's rule: horizontal at yi)
        # Use epsilon for robust comparison
        if yi > y_next + epsilon :
            segment_area = yi * w
        # Case 2: yi <= y_next (within epsilon tolerance)
        else:
            # Calculate potential y value if slope 3 continues uninterrupted
            y_calc = yi + slope * w

            # Subcase 2a: Slope 3 does NOT overshoot y_next (y_calc <= y_next)
            if y_calc <= y_next + epsilon:
                # Area is trapezoid under slope 3 line: heights yi and y_calc
                segment_area = (yi + y_calc) * w / 2.0
                # Alternative: segment_area = yi * w + 0.5 * slope * w**2

            # Subcase 2b: Slope 3 overshoots y_next (y_calc > y_next)
            else:
                # Calculate width of the initial slope-3 part until y hits y_next
                # w1 = x_hit - xi = (y_next - yi) / slope
                delta_y = y_next - yi
                if delta_y < 0: delta_y = 0 # Should not happen if yi<=y_next, but safe guard

                # Avoid division by zero if slope is ever zero
                if abs(slope) < epsilon:
                     if delta_y > epsilon: # Cannot reach y_next if slope is zero and yi<y_next
                         warnings.warn(f"Slope is near zero ({slope}), cannot reach y_next={y_next} from yi={yi}")
                         # Treat as if y_calc = yi <= y_next (Subcase 2a with slope=0)
                         segment_area = (yi + yi) * w / 2.0 # Area = yi * w
                     else: # yi is already at (or above) y_next, delta_y approx 0
                         w1 = 0.0 # No slope-3 part needed
                else:
                    w1 = delta_y / slope

                # Clamp w1 to be within [0, w] due to potential floating point issues
                w1 = max(0.0, min(w1, w))
                w2 = w - w1 # Width of the horizontal part at y_next

                # Area = Area of trapezoid (slope 3 part) + Area of rectangle (horizontal part)
                # Trapezoid: (xi, yi) -> (xi+w1, y_next)
                area1 = (yi + y_next) * w1 / 2.0
                # Rectangle: (xi+w1, y_next) -> (x_next, y_next)
                area2 = y_next * w2
                segment_area = area1 + area2

        total_area += segment_area

    # --- Calculate Max Gap (same logic as before) ---
    gaps = np.diff(full_x)
    # Find indices i where the gap starts: gap_range_min <= full_x[i] < gap_range_max
    indices_in_range = np.where(
        (full_x[:-1] >= gap_range_min) & (full_x[:-1] < gap_range_max)
    )[0]

    if indices_in_range.size > 0:
        relevant_gaps = gaps[indices_in_range]
        max_gap_in_range = np.max(relevant_gaps)
    else:
        # No gap starts within the specified range
        # Return 0.0 to indicate no qualifying gap found
        max_gap_in_range = 0.0
        # If a default value like 1.0 is desired when no gap qualifies:
        # max_gap_in_range = 1.0

    return total_area, max_gap_in_range


def get_score(solutions, max_length):
  """Returns the score for the given solutions."""
  solutions = np.array(solutions)

  for i, solution in enumerate(solutions):
    if len(solution) != max_length:
      return -10_000_001
    if not all(isinstance(x, float) for x in solution):
      return -10_000_002
    if not all(0 <= x <= 1 for x in solution):
      return -10_000_003
    if np.sum(solution) < 1e-7:
      return -10_000_004
    solutions[i] = solution / np.sum(solution)

  edge_densities, triangle_densities = sum_pairwise_triple_products_batch(
      solutions
  )
  if np.any(np.isnan(edge_densities)) or np.any(np.isnan(triangle_densities)):
    return -10_000_005

  area, max_gap_in_range = analyze_density_curve(
      edge_densities, triangle_densities
  )
  # print(f"Solution {i + 1}: Area = {area}, Max Gap = {max_gap_in_range}")
  # print(f"Edge Densities: {edge_densities}")
  # print(f"Triangle Densities: {triangle_densities}")
  return -(area + 10 * max_gap_in_range)
