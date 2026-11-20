# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/sidorenko_conjecture/sidorenko_conjecture.ipynb, notebook code cells 0 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
import numba
from scipy import optimize


Matrix = np.ndarray


@numba.njit
def count_homomorphisms_mobius_graph_weighted(
    adjacency_matrix: Matrix,
) -> np.float64:
  """Returns the number of homomorphisms from K_{5,5} - C_10 to the input graph.

  A homomorphism from graph G to graph H is a function f: V(G) -> V(H) such that
  for any vertices u and v in G, if u, v are connected then f(u) and f(v) are
  also connected. Note that f is defined on labelled graphs.
  The graph K_{5,5} is the complete bipartite graph with 5 vertices in each
  part. The graph C_10 is a cycle on 10 vertices. And K_{5,5} - C_10 just means
  we start from K_{5,5} and delete a set of edges that make a 10-cycle.

  This function runs an O(n^5) time algorithm but tries taking symmetry into
  account. It was written by Adam Wagner and optimized by us.

  Args:
    adjacency_matrix: the adjacency matrix of the input graph.
  """  # pylint: disable=g-docstring-has-escape
  # TODO(mehrabian): try coding this in C++ to allow for larger sizes
  # TODO(mehrabian): try parallelization for speed up

  n = np.shape(adjacency_matrix)[0]

  assert n <= 85  # if n>85, the answer may not fit in 64 bits (overflow)

  common_neighbours = np.zeros((n, n, n), dtype=np.float64)
  # counts the number of common neighbours of each triple of vertices

  for a in range(n):
    for b in range(a, n):
      for c in range(b, n):
        for d in range(n):
          common_neighbours[a, b, c] += (
              adjacency_matrix[a, d]
              * adjacency_matrix[b, d]
              * adjacency_matrix[c, d]
          )
        common_neighbours[a, c, b] = common_neighbours[a, b, c]
        common_neighbours[b, a, c] = common_neighbours[a, b, c]
        common_neighbours[b, c, a] = common_neighbours[a, b, c]
        common_neighbours[c, a, b] = common_neighbours[a, b, c]
        common_neighbours[c, b, a] = common_neighbours[a, b, c]

  # H = K_{5,5} - C_10 is bipartite: call its parts left part and right part.
  # We do a loop over the ways the left part can be embedded into G.
  # The embedding of this part is described by the 5-tuple v.
  # Since multiple vertices of H can be mapped to same vertex of G, we need to
  # do a case analysis.

  output = np.float64(0)
  old_output = output

  # Case 1: v contains five different vertices. By symmetry, we can assume
  # v0 is strictly smallest, v1 < v4, and multiply the total count by 10
  for v0 in range(n):
    for v1 in range(v0 + 1, n):
      for v4 in range(v1 + 1, n):
        for v2 in range(v0 + 1, n):
          if v2 == v1 or v2 == v4:
            continue
          for v3 in range(v0 + 1, n):
            if v3 != v2 and v3 != v1 and v3 != v4:
              output += np.float64(
                  common_neighbours[v0, v1, v2]
                  * common_neighbours[v1, v2, v3]
                  * common_neighbours[v2, v3, v4]
                  * common_neighbours[v3, v4, v0]
                  * common_neighbours[v4, v0, v1]
                  * 10
              )

  assert output >= old_output  # sanity check to avoid overflow
  old_output = output

  # Case 2: v[i] = v[i+1] for some i, and other vertices are all different. By
  # symmetry, we assume v0 = v1, v2 < v4, and multiply total count by 10
  for v2 in range(n):
    for v4 in range(v2 + 1, n):
      for v0 in range(n):
        v1 = v0
        if v2 == v0 or v4 == v0:
          continue
        for v3 in range(n):
          if v3 != v0 and v3 != v2 and v3 != v4:
            output += np.float64(
                common_neighbours[v0, v1, v2]
                * common_neighbours[v1, v2, v3]
                * common_neighbours[v2, v3, v4]
                * common_neighbours[v3, v4, v0]
                * common_neighbours[v4, v0, v1]
                * 10
            )
  assert output >= old_output  # sanity check to avoid overflow
  old_output = output

  # Case 3: v[i] = v[i+2] for some i, and other vertices are all different. By
  # symmetry, we assume v0 = v2, v3 < v4, and multiply total count by 10
  for v3 in range(n):
    for v4 in range(v3 + 1, n):
      for v0 in range(n):
        v2 = v0
        if v3 == v0 or v4 == v0:
          continue
        for v1 in range(n):
          if v1 != v0 and v1 != v3 and v1 != v4:
            output += np.float64(
                common_neighbours[v0, v1, v2]
                * common_neighbours[v1, v2, v3]
                * common_neighbours[v2, v3, v4]
                * common_neighbours[v3, v4, v0]
                * common_neighbours[v4, v0, v1]
                * 10
            )
  assert output >= old_output  # sanity check to avoid overflow
  old_output = output

  # Case 4: v[i] = v[i+1] = v[i+2] for some i, and other vertices are different.
  # By symmetry we assume v0 = v1 = v2, v3 < v4, and multiply by 10.
  for v0 in range(n):
    v1 = v0
    v2 = v0
    for v3 in range(n):
      if v3 == v0:
        continue
      for v4 in range(v3 + 1, n):
        if v4 == v0:
          continue
        output += np.float64(
            common_neighbours[v0, v1, v2]
            * common_neighbours[v1, v2, v3]
            * common_neighbours[v2, v3, v4]
            * common_neighbours[v3, v4, v0]
            * common_neighbours[v4, v0, v1]
            * 10
        )
  assert output >= old_output  # sanity check to avoid overflow
  old_output = output

  # Case 5: v[i] = v[i+1] = v[i+3] for some i, and other vertices are different.
  # By symmetry we assume v0 = v1 = v3, v2 < v4, and multiply by 10.
  for v0 in range(n):
    v1 = v0
    v3 = v0
    for v2 in range(n):
      if v2 == v0:
        continue
      for v4 in range(v2 + 1, n):
        if v4 == v0:
          continue
        output += np.float64(
            common_neighbours[v0, v1, v2]
            * common_neighbours[v1, v2, v3]
            * common_neighbours[v2, v3, v4]
            * common_neighbours[v3, v4, v0]
            * common_neighbours[v4, v0, v1]
            * 10
        )
  assert output >= old_output  # sanity check to avoid overflow
  old_output = output

  # Case 6: v[i+1] = v[i+2], v[i+3] = v[i+4] for some i, and v[i] is different.
  # By symmetry: v0 != v1 = v2 < v3 = v4 != v0, and multiply by 10.
  for v0 in range(n):
    for v1 in range(n):
      if v1 == v0:
        continue
      v2 = v1
      for v3 in range(v1 + 1, n):
        if v3 == v0:
          continue
        v4 = v3
        output += np.float64(
            common_neighbours[v0, v1, v2]
            * common_neighbours[v1, v2, v3]
            * common_neighbours[v2, v3, v4]
            * common_neighbours[v3, v4, v0]
            * common_neighbours[v4, v0, v1]
            * 10
        )
  assert output >= old_output  # sanity check to avoid overflow
  old_output = output

  # Case 7: v[i+1] = v[i+3], v[i+2] = v[i+4] for some i, and v[i] is different.
  # By symmetry: v0 != v1 = v3 < v2 = v4 != v0, and multiply by 10.
  for v0 in range(n):
    for v1 in range(n):
      if v1 == v0:
        continue
      v3 = v1
      for v2 in range(v1 + 1, n):
        if v2 == v0:
          continue
        v4 = v2
        output += np.float64(
            common_neighbours[v0, v1, v2]
            * common_neighbours[v1, v2, v3]
            * common_neighbours[v2, v3, v4]
            * common_neighbours[v3, v4, v0]
            * common_neighbours[v4, v0, v1]
            * 10
        )
  assert output >= old_output  # sanity check to avoid overflow
  old_output = output

  # Case 8: v[i+1] = v[i+4], v[i+2] = v[i+3] for some i, and v[i] is different.
  # By symmetry: v1 = v4 != v0, v2 = v3 != v0, and multiply by 5.
  for v0 in range(n):
    for v1 in range(n):
      if v1 == v0:
        continue
      v4 = v1
      for v2 in range(n):
        if v2 == v0 or v2 == v1:
          continue
        v3 = v2
        output += np.float64(
            common_neighbours[v0, v1, v2]
            * common_neighbours[v1, v2, v3]
            * common_neighbours[v2, v3, v4]
            * common_neighbours[v3, v4, v0]
            * common_neighbours[v4, v0, v1]
            * 5
        )
  assert output >= old_output  # sanity check to avoid overflow
  old_output = output

  # Case 9: v[i] = v[i+1] = v[i+2] = v[i+3] for some i, and v[i+4] is different.
  # By symmetry: v1=v2=v3=v4 != v0, and multiply the count by 5.
  for v0 in range(n):
    for v1 in range(n):
      if v1 == v0:
        continue
      v2 = v1
      v3 = v1
      v4 = v1
      output += np.float64(
          common_neighbours[v0, v1, v2]
          * common_neighbours[v1, v2, v3]
          * common_neighbours[v2, v3, v4]
          * common_neighbours[v3, v4, v0]
          * common_neighbours[v4, v0, v1]
          * 5
      )
  assert output >= old_output  # sanity check to avoid overflow
  old_output = output

  # Case 10: v[i] = v[i+1] != v[i+2] = v[i+3] = v[i+4] for some i. By symmetry,
  # we can assume v0=v1!=v2=v3=v4, and multiply the count by 5
  for v0 in range(n):
    v1 = v0
    for v2 in range(n):
      if v2 == v0:
        continue
      v3 = v2
      v4 = v2
      output += np.float64(
          common_neighbours[v0, v1, v2]
          * common_neighbours[v1, v2, v3]
          * common_neighbours[v2, v3, v4]
          * common_neighbours[v3, v4, v0]
          * common_neighbours[v4, v0, v1]
          * 5
      )
  assert output >= old_output
  old_output = output

  # Case 11: v[i] = v[i+2] != v[i+1] = v[i+3] = v[i+4] for some i. By symmetry,
  # we can assume v0=v2!=v1=v3=v4, and multiply the count by 5
  for v0 in range(n):
    v2 = v0
    for v1 in range(n):
      if v1 == v0:
        continue
      v3 = v1
      v4 = v1
      output += np.float64(
          common_neighbours[v0, v1, v2]
          * common_neighbours[v1, v2, v3]
          * common_neighbours[v2, v3, v4]
          * common_neighbours[v3, v4, v0]
          * common_neighbours[v4, v0, v1]
          * 5
      )
  assert output >= old_output  # sanity check to avoid overflow
  old_output = output

  # Case 12: all v[i] are equal to some vertex u
  for u in range(n):
    output += np.float64(common_neighbours[u, u, u] ** 5)
  assert output >= old_output  # sanity check to avoid overflow

  return output


def score_weighted_h(adjacency_matrix: Matrix) -> np.double:
  """Weighted score function for Sidorenko conjecture for Mobius graph.

  Let H = K_{5,5} - C_10. For input weighted graph G (with adjacency matrix),
  this function computes:
  (2 * weighted_edges(G))^15 / (v(G)^20 * hom(H, G)) - 1
  where v(G) is the number of vertices, weighted_edges(G) is the sum of edge
  weights, and hom(H, G) is the weighted homomorphism count from H to G.
  A positive score would suggest a counterexample to (weighted) Sidorenko's
  conjecture.

  Args:
    adjacency_matrix: Weighted adjacency matrix of the graph.

  Returns:
    A score in [-1, infinity). Returns -1 if hom(H, G) = 0 or no edges.
  """
  vertices: int = int(np.shape(adjacency_matrix)[0])
  if vertices == 0:
    return -1.0

  if vertices != 30:
    return -1.0

  # clip all the weights to be in [0, 1]
  adjacency_matrix = np.clip(adjacency_matrix, 0, 1)

  # make sure that the adjacency matrix is symmetric
  adjacency_matrix = (adjacency_matrix + adjacency_matrix.T) / 2

  # Scale it so the mean is 0.5
  # First check if dividing by zero
  if adjacency_matrix.mean() < 0.01:
    return -1.0
  adjacency_matrix = adjacency_matrix / (2 * adjacency_matrix.mean())
  adjacency_matrix = np.clip(adjacency_matrix, 0, 1)

  # If the matrix is near-constant, return -1
  if np.max(adjacency_matrix) - np.min(adjacency_matrix) < 0.25:
    return -1.0

  # If the standard deviation of the matrix is small, return -1
  if np.std(adjacency_matrix) < 0.23:
    return -1.0

  weighted_twice_edges: float = np.sum(adjacency_matrix)  # Sum of all weights
  if weighted_twice_edges == 0:
    return -1.0

  homomorphisms: float = count_homomorphisms_mobius_graph_weighted(
      adjacency_matrix
  )
  if homomorphisms == 0:
    return -1.0

  numerator_weighted: float = (weighted_twice_edges**15) - (
      vertices**20
  ) * homomorphisms
  denominator_weighted: float = (vertices**20) * homomorphisms

  return np.double(numerator_weighted / denominator_weighted)
