# Vendored verbatim from google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8 (Apache-2.0).
"""Vendored verbatim from google-deepmind/alphaevolve_repository_of_problems @ 8f44745 (Apache-2.0),
notebook Equidistant_points_in_convex_polygons.ipynb, code cell [4]. Only the scoring functions are copied; imports added."""
import numpy as np, itertools, math
from typing import List, Tuple

def calculate_vertex_error(
    vertex_index: int, polygon_points: List[Tuple[float, float]]
) -> float:
    """Calculates the minimum equidistance error for 4 points relative to a vertex.

    Error is defined as the range (max - min) of the best 4 equidistant points.
    """
    num_vertex = len(polygon_points)
    # We need at least 1 vertex + 4 others = 5 points total
    if num_vertex < 5:
        return float('inf')

    v = np.array(polygon_points[vertex_index])
    distances = []
    for i, p_tuple in enumerate(polygon_points):
        if i == vertex_index:
            continue
        # Calculate Euclidean distance
        distances.append(np.linalg.norm(v - np.array(p_tuple)))

    distances.sort()

    # We want the best cluster of 4 distances.
    # In a sorted list, the best 4 will always be consecutive.
    # We find the 4 consecutive distances with the smallest range (dist[i+3] - dist[i]).
    min_range = float('inf')
    # Iterate through all possible clusters of 4
    for i in range(len(distances) - 3):
        current_range = distances[i+3] - distances[i]
        if current_range < min_range:
            min_range = current_range

    return min_range


def calculate_polygon_score_new(
    polygon_points: List[Tuple[float, float]], num_vertex: int
) -> float:
    """Calculates the normalized error score for the polygon.

    Formula: Worst_Vertex_Error / (Min_Side_Length^2 / Diameter)
    Target: MINIMIZE this score (ideally towards 0).
    """
    # --- Basic Validation ---
    if len(polygon_points) != num_vertex or num_vertex < 5:
        return 1e9  # Return high error for invalid inputs

    points_np = np.array(polygon_points)

    # --- 1. Calculate Geometric Properties ---
    # Diameter: Maximum distance between any pair of points
    # (Using brute force O(N^2), sufficient for small N like 5-10)
    max_dist_sq = 0.0
    for i in range(num_vertex):
        for j in range(i + 1, num_vertex):
            dist_sq = np.sum((points_np[i] - points_np[j])**2)
            if dist_sq > max_dist_sq:
                max_dist_sq = dist_sq
    diameter = np.sqrt(max_dist_sq)

    # Min Side Length: Minimum distance between adjacent vertices
    # Assumes polygon_points are ordered around the perimeter.
    min_side_sq = float('inf')
    for i in range(num_vertex):
        p1 = points_np[i]
        p2 = points_np[(i + 1) % num_vertex] # Wrap around to first point
        side_sq = np.sum((p1 - p2)**2)
        if side_sq < min_side_sq:
            min_side_sq = side_sq
    min_side = np.sqrt(min_side_sq)

    # Avoid division by zero if points overlap significantly
    if min_side < 1e-9 or diameter < 1e-9:
        return -1e9 # Penalize degenerate polygons

    # Calculate the normalization factor: (min_side^2) / diameter
    denominator = (min_side ** 2) / diameter

    # --- 2. Calculate Worst Equidistance Error ---
    # Find the maximum error across all vertices
    max_vertex_error = 0.0
    for i in range(num_vertex):
        error = calculate_vertex_error(i, polygon_points)
        if error > max_vertex_error:
            max_vertex_error = error

    # --- 3. Final Score Calculation ---
    final_score = max_vertex_error / denominator

    # Now a score of 0 means a perfect solution
    return -final_score

