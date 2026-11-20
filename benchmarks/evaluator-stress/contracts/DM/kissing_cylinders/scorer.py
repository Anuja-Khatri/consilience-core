# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/kissing_cylinders/kissing_cylinders.ipynb, notebook code cells 0 (0-based, counting code cells only), functions get_closest_approach_midpoint_numba, _normalize_vector_numba, _random_unit_vector_numba, _standardize_point_on_axis_numba, distance_between_skew_lines_numba, calculate_arrangement_score_numba, calculate_arrangement_score_hidden (Apache-2.0).
# Scoring cells copied verbatim; only imports added
from typing import List, Tuple
import numba
import numpy as np
njit = numba.njit

@njit
def get_closest_approach_midpoint_numba(p1: np.ndarray, v1: np.ndarray,
                                      p2: np.ndarray, v2: np.ndarray,
                                      epsilon_parallel: float = 1e-7) -> np.ndarray:
    """
    Calculates the midpoint of the segment of closest approach between two lines L1 and L2.
    L1(t) = p1 + t*v1
    L2(s) = p2 + s*v2
    Assumes v1, v2 are unit vectors.
    p1, p2 are points on the lines, standardized (p_i . v_i = 0).
    """
    dp = p1 - p2 # Vector from p2 to p1
    v1_dot_v2 = np.dot(v1, v2)

    if np.abs(np.abs(v1_dot_v2) - 1.0) < epsilon_parallel:
        # Parallel lines:
        # The line of midpoints between L1(t)=p1+t*v1 and L2(t)=p2+t*v1 is (p1+p2)/2 + t*v1.
        # We take the point on this line closest to the origin.
        mid_of_standardized_points = (p1 + p2) / 2.0
        m_closest_to_origin = mid_of_standardized_points - np.dot(mid_of_standardized_points, v1) * v1
        return m_closest_to_origin

    # Skew lines:
    # Solve for t_c, s_c such that C1=p1+t_c*v1 and C2=p2+s_c*v2 are closest points.
    # dp_dot_v1 = (p1-p2).v1
    # dp_dot_v2 = (p1-p2).v2
    dp_dot_v1 = np.dot(dp, v1)
    dp_dot_v2 = np.dot(dp, v2)

    denominator = 1.0 - v1_dot_v2 * v1_dot_v2
    # This denominator should not be zero if not parallel (already checked).

    # t_c is parameter for L1: p1 + t_c*v1
    # s_c is parameter for L2: p2 + s_c*v2
    # Using formulas from common sources (e.g. Eberly, Geometric Tools for Computer Graphics)
    # for parameters t1, t2 for lines P1+t1*D1 and P2+t2*D2
    # t1 = (dot(D1,D2)*dot(P2-P1,D2) - dot(P2-P1,D1)) / (1 - dot(D1,D2)^2)
    # t2 = (dot(P2-P1,D2) - dot(D1,D2)*dot(P2-P1,D1)) / (1 - dot(D1,D2)^2)
    # My v1=D1, v2=D2. My p1=P1, p2=P2. My dp = p1-p2. So (P2-P1) = -dp.
    # (P2-P1).D2 = -dp_dot_v2. (P2-P1).D1 = -dp_dot_v1.

    t_c = (v1_dot_v2 * (-dp_dot_v2) - (-dp_dot_v1)) / denominator
    s_c = ((-dp_dot_v2) - v1_dot_v2 * (-dp_dot_v1)) / denominator

    c1 = p1 + t_c * v1
    c2 = p2 + s_c * v2

    return (c1 + c2) / 2.0


@njit
def _normalize_vector_numba(v: np.ndarray) -> np.ndarray:
    """Normalizes a vector. Returns a zero vector if input is zero vector."""
    norm = np.linalg.norm(v)
    if norm < 1e-9: # Threshold for zero vector
        # Return a random unit vector as a fallback, or handle as error
        # For simplicity here, returning a fixed axis if this happens during mutation.
        # During init, we'd regenerate.
        fallback_v = np.zeros_like(v)
        if fallback_v.shape[0] > 0:
            fallback_v[0] = 1.0
        return fallback_v
    return v / norm


@njit
def _random_unit_vector_numba(dim: int) -> np.ndarray:
    """Generates a random unit vector in 'dim' dimensions."""
    v = np.empty(dim, dtype=np.float64)
    for i in range(dim):
        v[i] = np.random.normal(0,1) # Gaussian distribution
    return _normalize_vector_numba(v)


@njit
def _standardize_point_on_axis_numba(p: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Given a point p and a unit direction vector v, returns the point on the line (p,v)
    that is closest to the origin. This point p_std satisfies p_std · v = 0."""
    # v must be a unit vector for this formula
    return p - np.dot(p, v) * v


@njit
def distance_between_skew_lines_numba(p1: np.ndarray, v1: np.ndarray, p2: np.ndarray, v2: np.ndarray) -> float:
    """
    Calculates the shortest distance between two skew lines.
    Line 1: L1(s) = p1 + s * v1
    Line 2: L2(t) = p2 + t * v2
    v1 and v2 must be unit vectors.
    """
    # Vector connecting the two points p1 and p2
    p1_p2 = p2 - p1

    # Cross product of direction vectors
    v1_cross_v2 = np.cross(v1, v2)
    norm_v1_cross_v2 = np.linalg.norm(v1_cross_v2)

    if norm_v1_cross_v2 < 1e-9:  # Lines are parallel
        # Distance from p2 to line (p1, v1)
        # dist = || (p2 - p1) x v1 || / ||v1||
        # Since v1 is unit vector, dist = || (p2 - p1) x v1 ||
        return np.linalg.norm(np.cross(p1_p2, v1))
    else:
        # Lines are skew or intersecting
        # Distance = | (p2 - p1) · (v1 x v2) | / ||v1 x v2||
        return np.abs(np.dot(p1_p2, v1_cross_v2)) / norm_v1_cross_v2


@njit
def calculate_arrangement_score_numba(cylinder_params: List[Tuple[np.ndarray, np.ndarray]],
                                      target_dist: float,
                                      contact_box_limit: float = 100.0) -> float: # New parameter
    """
    Calculates the score for a given list of cylinder arrangements.
    Score = -sum_{i<j} (distance_between_axes_ij - target_dist)^2
    Also heavily penalizes if contact midpoints are outside [-box_limit, box_limit]^3.
    """
    num_cylinders = len(cylinder_params)
    if num_cylinders == 0:
        # Conventionally, score for empty set can be 0 or -np.inf.
        # If AlphaEvolve might try num_cylinders=0, 0 is safer to not immediately kill exploration.
        # But for a fixed num_cylinders problem, this branch is less critical.
        return -np.inf

    total_penalty = 0.0

    # Basic validation of individual cylinder parameters
    for i in range(num_cylinders):
        p_i, v_i = cylinder_params[i]
        if not np.all(np.isfinite(p_i)) or not np.all(np.isfinite(v_i)):
            return -np.inf # Invalid coordinates
        if np.abs(np.linalg.norm(v_i) - 1.0) > 1e-6: # v_i must be unit vector
            return -np.inf
        # p_i must be standardized (p_i . v_i = 0). This is done by evolve_me.
        # Adding a check here can catch issues if standardization is missed.
        if np.abs(np.dot(p_i, v_i)) > 1e-5: # Allow slightly larger tolerance due to float math
             return -np.inf # Standardization issue


    for i in range(num_cylinders):
        for j in range(i + 1, num_cylinders):
            p1, v1 = cylinder_params[i]
            p2, v2 = cylinder_params[j]

            # Standard distance penalty
            dist_axes = distance_between_skew_lines_numba(p1, v1, p2, v2)
            penalty_ij = (dist_axes - target_dist)**2
            total_penalty += penalty_ij

            # New: Check contact point location constraint
            midpoint_of_closest_approach = get_closest_approach_midpoint_numba(p1, v1, p2, v2)

            # Check if any coordinate of the midpoint exceeds the box limit
            for coord_idx in range(midpoint_of_closest_approach.shape[0]): # Iterate 0,1,2 for 3D
                if np.abs(midpoint_of_closest_approach[coord_idx]) > contact_box_limit:
                    # This configuration is invalid due to contact point location
                    return -np.inf # Immediate rejection

    return -total_penalty


def calculate_arrangement_score_hidden(
    cylinder_params: List[Tuple[np.ndarray, np.ndarray]],
    target_dist: float = 2.0,
    contact_box_limit: float = 100.0  # Add new parameter with default
    ) -> float:
    """
    Non-Numba wrapper for validation or if Numba is unavailable.
    Ensures type compatibility for Numba JIT call.
    """
    typed_cylinder_params = numba.typed.List()

    for p_val, v_val in cylinder_params:
        # Ensure p and v are numpy arrays and of correct dimension/type
        # More robust type checking
        if not (isinstance(p_val, np.ndarray) and p_val.ndim == 1 and p_val.shape[0] == 3 and p_val.dtype == np.float64 and
                isinstance(v_val, np.ndarray) and v_val.ndim == 1 and v_val.shape[0] == 3 and v_val.dtype == np.float64):
             return -np.inf # Invalid input format for Numba
        if not np.all(np.isfinite(p_val)) or not np.all(np.isfinite(v_val)):
            return -np.inf # Contains non-finite numbers

        typed_cylinder_params.append((p_val, v_val))

    # Call Numba version with all parameters
    return calculate_arrangement_score_numba(typed_cylinder_params, target_dist, contact_box_limit)
