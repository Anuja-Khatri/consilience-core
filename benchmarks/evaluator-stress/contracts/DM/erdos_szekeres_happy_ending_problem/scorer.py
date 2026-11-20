# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/erdos_szekeres_happy_ending_problem/erdos_szekeres_happy_ending_problem.ipynb, notebook code cells 2 (0-based, counting code cells only), functions orientation_numba, calculate_score_numba, calculate_score (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import math
import random
import numba
import numpy as np
njit = numba.njit

@numba.jit(nopython=True, fastmath=True)
def orientation_numba(p, q, r):
  val = (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0])
  if val > 1e-9:
    return 1
  if val < -1e-9:
    return -1
  return 0


@numba.jit(nopython=True, fastmath=True)
def calculate_score_numba(points_np: np.ndarray, n: int) -> int:
  num_points = len(points_np)
  if num_points < n or n < 3:
    return 0
  if num_points != 2 ** (n - 2) + 1:
    return -np.inf

  # Proximity check: Add a large penalty if any two points are too close.
  # This prevents floating-point issues in orientation calculations.
  # We use squared distance to avoid the expensive sqrt operation.
  min_dist_sq = 1e-12  # Corresponds to a minimum distance of 1e-6
  for i in range(num_points):
    for j in range(i + 1, num_points):
      dist_sq = (points_np[i, 0] - points_np[j, 0])**2 + \
                (points_np[i, 1] - points_np[j, 1])**2
      if dist_sq < min_dist_sq:
        return -1e15  # Return a large penalty.

  collinearity_threshold = 1e-9
  for i in range(num_points):
    for j in range(i + 1, num_points):
      for k in range(j + 1, num_points):
        p1 = points_np[i]
        p2 = points_np[j]
        p3 = points_np[k]
        # This formula calculates a value proportional to the signed area of the triangle.
        area = p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1])
        if abs(area) < collinearity_threshold:
          print(area, p1, p2, p3)
          return -1e15+1000 # Return a large penalty

  P = points_np
  total_ngons = 0
  for i in range(num_points):
    pivot = P[i]
    Q_buffer = np.zeros((num_points - 1 - i, 2))
    count = 0
    for j in range(i + 1, num_points):
      Q_buffer[count] = P[j]
      count += 1
    if count == 0:
      continue
    Q_unsorted = Q_buffer[:count]
    angles = np.zeros(len(Q_unsorted))
    for j in range(len(Q_unsorted)):
      angles[j] = math.atan2(
          Q_unsorted[j, 1] - pivot[1], Q_unsorted[j, 0] - pivot[0]
      )
    sort_indices = np.argsort(angles)
    Q = Q_unsorted[sort_indices]
    M = len(Q)
    if M < n - 1:
      continue
    dp = np.zeros((n + 1, M, M), dtype=np.int64)
    for j in range(M):
      for k in range(j):
        if orientation_numba(pivot, Q[k], Q[j]) > 0:
          dp[3, k, j] = 1
    for length in range(4, n + 1):
      for j in range(M):
        for k in range(j):
          for prev_k in range(k):
            if (
                dp[length - 1, prev_k, k] > 0
                and orientation_numba(Q[prev_k], Q[k], Q[j]) > 0
            ):
              dp[length, k, j] += dp[length - 1, prev_k, k]
    for j in range(M):
      for k in range(j):
        if dp[n, k, j] > 0 and orientation_numba(Q[k], Q[j], pivot) > 0:
          total_ngons += dp[n, k, j]
  return -total_ngons


def calculate_score(points: list[list[float]], n: int) -> int:
  sorted_points = sorted([tuple(p) for p in points])
  points_np = np.array(sorted_points, dtype=np.float64)
  return calculate_score_numba(points_np, n)
