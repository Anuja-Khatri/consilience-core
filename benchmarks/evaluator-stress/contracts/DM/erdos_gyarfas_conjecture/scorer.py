# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/erdos_gyarfas_conjecture/erdos_gyarfas_conjecture.ipynb, notebook code cells 0 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import collections
import copy
import re
from typing import Any, Dict, List, Mapping, Set, Tuple, Union
import numpy as np

#@title Verification code

# pylint: disable=unused-import
# pylint: disable=g-bad-import-order




# --- Helper Functions (Outside Evolve Block) ---


def build_adjacency_list(
    num_vertices: int, edges: List[Tuple[int, int]]
) -> Dict[int, Set[int]]:
  """Builds an adjacency list representation from edges."""
  adj = collections.defaultdict(set)
  valid_edges = set()  # To store canonical edges (u, v) with u < v
  max_v_idx = num_vertices - 1

  for u, v in edges:
    # Ensure vertices are within the valid range [0, num_vertices-1]
    # Ensure u and v are integers
    if not (
        isinstance(u, int)
        and isinstance(v, int)
        and 0 <= u <= max_v_idx
        and 0 <= v <= max_v_idx
    ):
      # Skip invalid vertices quietly during build, score func will handle
      # overall validity
      continue
    # Avoid self-loops
    if u == v:
      continue
    # Ensure canonical edge representation (smaller index first)
    u_canon, v_canon = min(u, v), max(u, v)
    # Avoid duplicate edges
    if (u_canon, v_canon) in valid_edges:
      continue

    valid_edges.add((u_canon, v_canon))
    adj[u].add(v)
    adj[v].add(u)  # Graph is undirected

  # Ensure all vertices from 0 to num_vertices-1 exist as keys, even if isolated
  for i in range(num_vertices):
    if i not in adj:
      adj[i] = set()

  return adj


def get_degrees(num_vertices: int, adj: Dict[int, Set[int]]) -> List[int]:
  """Calculates the degree of each vertex."""
  degrees = [0] * num_vertices
  for i in range(num_vertices):
    degrees[i] = len(
        adj.get(i, set())
    )  # Use .get for safety if adj list isn't complete
  return degrees


def has_power_of_2_cycle(
    num_vertices: int, adj: Dict[int, Set[int]], min_k: int = 2
) -> bool:
  """Checks if the graph contains a cycle of length 2^k for k >= min_k (default k>=2 -> len 4, 8, 16...).

  Uses DFS. This can be computationally expensive for large graphs.

  Args:
      num_vertices: The number of vertices in the graph.
      adj: The adjacency list representation of the graph.
      min_k: The minimum value of k to consider (default 2, for cycles of length
        4).

  Returns:
      True if a cycle of length 2^k is found for any k >= min_k, False
      otherwise.
  """
  max_len = num_vertices  # Max possible simple cycle length
  target_lengths = set()
  k = min_k
  while True:
    length = 2**k
    if length > max_len:
      break
    target_lengths.add(length)
    k += 1

  if not target_lengths:  # No target cycle lengths possible (e.g., N=3)
    return False

  for start_node in range(num_vertices):
    # Stack stores (current_node, path_list, visited_in_path_set)
    stack = [(start_node, [start_node])]

    while stack:
      u, path = stack.pop()
      path_set = set(
          path
      )  # Keep track of nodes in the current path for O(1) lookup

      # Explore neighbors
      for v in adj.get(u, set()):
        # Check if neighbor v closes a cycle
        if (
            v == path[0] and len(path) in target_lengths
        ):  # Cycle closed back to start_node
          # print(f"Found cycle of length {len(path)}: {path + [v]}")
          return True
        elif (
            v in path_set
        ):  # Found a cycle, but maybe not back to start, or wrong length.
          # Ignore.
          continue  # Continue exploring other branches from u
        # If v is not in the current path, extend the path
        else:
          # Optimization: Prune search if path length exceeds max target length
          if len(path) + 1 <= max(target_lengths):
            new_path = path + [v]
            stack.append((v, new_path))

  return False  # No target length cycles found


def count_power_of_2_cycles(
    num_vertices: int, adj: Dict[int, Set[int]], min_k: int = 2
) -> Dict[Union[float, int], Union[float, int]]:
  """Counts simple cycles of length 2^k for k >= min_k.

  Uses DFS. Normalizes
  count by 2*L to correct for starting nodes and direction.

  Args:
      num_vertices: The number of vertices in the graph.
      adj: The adjacency list representation of the graph.
      min_k: The minimum value of k to consider (default 2, for cycles of length
        4).

  Returns:
      A dictionary mapping cycle length L to its count.
  """
  max_len = num_vertices
  target_lengths = set()
  k = min_k
  while True:
    length = 2**k
    if length > max_len:
      break
    target_lengths.add(length)
    k += 1

  if not target_lengths:
    return {}  # No target lengths possible (e.g., N=3)

  # Initialize counts for target lengths
  final_counts = {length: 0 for length in target_lengths}
  # Temporary counts before normalization
  raw_counts = {length: 0 for length in target_lengths}

  for start_node in range(num_vertices):
    # Stack stores (current_node, path_list)
    # Path list stores nodes visited in the current DFS path from start_node
    stack = [(start_node, [start_node])]

    while stack:
      u, path = stack.pop()
      path_set = set(path)  # Efficient lookup for nodes in the current path

      # Explore neighbors of u
      for v in adj.get(u, set()):
        # Check if neighbor v closes a cycle back to the start_node
        if v == start_node:
          cycle_len = len(path)
          if cycle_len in target_lengths:
            # Found a cycle of a target length closing back to start_node
            raw_counts[cycle_len] += 1
          # Do not continue path back to start node to avoid trivial
          # cycles/repetition here
          continue  # Go to next neighbor of u

        # Check if v is already in the current path (but not the start node)
        # This means we found a cycle, but not one closing back to the start
        # node here. We must avoid traversing back along the path immediately
        # (path[-2]) and avoid cycles not involving the start_node directly in
        # this count pass. We allow revisiting nodes *not* on the current path
        # back to the start_node.
        elif v in path_set:
          # If v is in the path but isn't the start node, ignore it to avoid
          # cycles not anchored at start_node and prevent immediate backtracking
          # (though adj list structure should prevent path[-2] typically).
          continue  # Go to next neighbor of u

        # If v is a new node for this path, extend the path
        else:
          # Optimization: Prune search if path length exceeds max target length
          if len(path) < max(
              target_lengths
          ):  # Only extend if path can still reach a target length
            new_path = path + [v]
            stack.append((v, new_path))
          # If len(path) == max target length, we can't reach any target length
          # by adding v.

  # Normalize counts: Each cycle of length L is found L times (once for each
  # node as start) and 2 times (for direction). Divide raw counts by 2*L.
  for length in raw_counts:
    if (
        length > 0
    ):  # Avoid division by zero if target_lengths included 0 (it shouldn't)
      # Ensure integer division
      final_counts[length] = raw_counts[length] // (2 * length)

  return final_counts


def simplify_graph_simple_iterative(
    num_vertices: int, initial_adj: Dict[int, Set[int]]
) -> Dict[int, Set[int]]:
  """Applies a simple, order-dependent edge removal heuristic.

  Iteratively removes edges (u,v) if current deg(u)>=4 and deg(v)>=4. Updates
  degrees immediately. Explicitly randomizes iteration order. IMPORTANT: After
  iterating, checks if min_degree dropped below 3.

             If it did, returns the ORIGINAL graph. Otherwise, returns the
             modified graph.

  Args:
      num_vertices: The number of vertices.
      initial_adj: The initial adjacency list of the graph (must have min_degree
        >= 3).

  Returns:
      The adjacency list of the simplified graph, guaranteed to have min_degree
      >= 3.
      This might be the original graph if simplification failed the degree
      check.
  """
  modified_adj = copy.deepcopy(initial_adj)
  current_degrees = get_degrees(num_vertices, modified_adj)

  edges_to_iterate = []
  processed_edges = set()  # To avoid adding (v, u) if (u, v) was added
  # Iterate over a copy of keys if modifying dict, but here reading is fine
  for u in list(modified_adj.keys()):
    # Iterate over a copy of neighbors as we might modify the set
    neighbors_copy = list(modified_adj.get(u, set()))
    for v in neighbors_copy:
      edge = tuple(sorted((u, v)))
      if edge not in processed_edges:
        edges_to_iterate.append(edge)
        processed_edges.add(edge)

  edges_actually_removed_count = 0
  for u, v in edges_to_iterate:
    if u in modified_adj and v in modified_adj.get(u, set()):
      # Check *current* degrees at the moment of processing
      # Ensure degrees array is accessed correctly
      if (
          u < num_vertices
          and v < num_vertices
          and current_degrees[u] >= 4
          and current_degrees[v] >= 4
      ):
        # Remove edge immediately
        modified_adj[u].remove(v)
        modified_adj[v].remove(u)
        # Update degrees immediately
        current_degrees[u] -= 1
        current_degrees[v] -= 1
        edges_actually_removed_count += 1
        # Optional debug
        # print(f"Debug: simple removal: removed ({u},{v}). New degs:
        # {current_degrees[u]}, {current_degrees[v]}")

  # --- Post-Simplification Check ---
  # Recalculate degrees from the final modified_adj for safety
  final_degrees = get_degrees(num_vertices, modified_adj)
  # Handle case of N=0 or graph becoming disconnected resulting in empty
  # final_degrees list
  final_min_degree = min(final_degrees) if final_degrees else 0

  min_degree_required = 3
  if final_min_degree < min_degree_required:
    print(
        'Warning: Simple iterative removal dropped min degree to'
        f' {final_min_degree} (< {min_degree_required}). Reverting to original'
        ' graph for scoring.'
    )  # Optional debug
    # Simplification failed safety check, return the input graph
    return initial_adj
  else:
    # Simplification succeeded or did nothing, return the modified graph
    # print(f"Debug: Simple iterative removal finished. Removed
    # {edges_actually_removed_count} edges. Final min degree:
    # {final_min_degree}.") # Optional debug
    return modified_adj


# --- Modified calculate_score Function ---


def calculate_score(num_vertices: int, edges: List[Tuple[int, int]]) -> float:
  """Calculates the score for a graph based on the Erdos-Gyarfas criteria.

  1. Checks initial minimum degree >= 3. Penalty if not. 2. Calls
  simplify_graph_simple_iterative to potentially simplify the graph,

     ensuring the result still has minimum degree >= 3.
  3. Counts cycles of length 2^k (k>=2) on the (potentially simplified) graph.
  4. Score is primarily -(total_forbidden_cycle_count), plus bonus if 0.

  Args:
      num_vertices: The number of vertices in the graph.
      edges: A list of tuples, where each tuple represents an edge (u, v)
        between vertices u and v.

  Returns:
      The calculated score for the graph.
  """
  # --- Basic Validity Checks ---
  if not isinstance(num_vertices, int) or num_vertices <= 0:
    return -1_000_000.0  # Invalid input N
  if not isinstance(edges, list):
    return -1_000_001.0  # Invalid input type for edges

  # --- Build Initial Adjacency List and Check Initial Degrees ---
  initial_adj = build_adjacency_list(num_vertices, edges)
  initial_degrees = get_degrees(num_vertices, initial_adj)

  # Check if degree list is valid
  if len(initial_degrees) != num_vertices:
    # This indicates an issue with build_adjacency_list or get_degrees if N>0
    print(
        f'Error: Degree list length mismatch! N={num_vertices},'
        f' len(degrees)={len(initial_degrees)}'
    )
    return -1_000_002.0  # Internal error state

  min_degree_required = 3
  degree_penalty = 0
  # Handle N=0 case where initial_degrees might be empty
  actual_min_degree = min(initial_degrees) if initial_degrees else 0

  # Check initial minimum degree constraint
  if num_vertices > 0:  # Only check penalty if graph can have edges
    for d in initial_degrees:
      if d < min_degree_required:
        degree_penalty += min_degree_required - d
    if actual_min_degree < min_degree_required:
      # Initial graph doesn't meet criteria, penalize immediately
      score = -100_000.0 * degree_penalty - 10000.0  # Base penalty + deviation
      return score
  elif num_vertices == 0:  # N=0 graph trivially meets criteria. Score 0.
    return 0.0  # Empty graph has no cycles and min degree >= 3

  # --- Apply Simple Iterative Simplification (with safety revert) ---
  # The initial graph passed the min_degree check, so we can simplify.
  # The function guarantees the returned graph also has min_degree >= 3.
  # print("Debug: Applying simple iterative simplification...") # Optional debug
  modified_adj = simplify_graph_simple_iterative(num_vertices, initial_adj)
  # Note: modified_adj could be the same as initial_adj if simplification was
  # reverted or did nothing.

  # --- Count Forbidden Cycles in the Resulting Graph ---
  num_edges_after_simplification = (
      sum(len(neighbors) for neighbors in modified_adj.values()) // 2
  )
  # print(f"Debug: Counting cycles on graph with"
  #       f" {num_edges_after_simplification} edges...") # Optional debug

  # Ensure cycle counter handles potentially empty modified_adj (though simplify
  # func tries to avoid this)
  cycle_counts = count_power_of_2_cycles(num_vertices, modified_adj, min_k=2)
  total_forbidden_cycle_count = (
      sum(cycle_counts.values())
      + 999 * cycle_counts[4]
      + 99 * cycle_counts[8]
      + 9 * cycle_counts[16]
  )
  # print(f"Debug: Cycle counts: {cycle_counts}, Total:"
  #       f" {total_forbidden_cycle_count}") # Optional debug

  cycle_penalty = -1.0 * float(total_forbidden_cycle_count)

  if cycle_penalty == 0.0:
    if num_edges_after_simplification > 0 or num_vertices == 0:
      max_possible_edges = num_vertices * (num_vertices - 1) / 2
      edge_bonus = 0
      if max_possible_edges > 0:
        edge_bonus = (
            num_edges_after_simplification / max_possible_edges
        ) * 1.0  # Max bonus 1.0
      return edge_bonus
    else:
      print('Warning: Score calculated on an empty graph (N>0) despite checks.')
      return -50001.0  # Error state, should have been reverted
  else:
    return cycle_penalty


def calculate_score_hidden(
    num_vertices: int, edges: List[Tuple[int, int]]
) -> float:
  """Calculates the score for a graph based on the Erdos-Gyarfas criteria.

  1. Checks initial minimum degree >= 3. Penalty if not. 2. Calls
  simplify_graph_simple_iterative to potentially simplify the graph,

     ensuring the result still has minimum degree >= 3.
  3. Counts cycles of length 2^k (k>=2) on the (potentially simplified) graph.
  4. Score is primarily -(total_forbidden_cycle_count), plus bonus if 0.

  Args:
      num_vertices: The number of vertices in the graph.
      edges: A list of tuples, where each tuple represents an edge (u, v)
        between vertices u and v.

  Returns:
      The calculated score for the graph.
  """
  # --- Basic Validity Checks ---
  if not isinstance(num_vertices, int) or num_vertices <= 0:
    return -1_000_000.0  # Invalid input N
  if not isinstance(edges, list):
    return -1_000_001.0  # Invalid input type for edges

  # --- Build Initial Adjacency List and Check Initial Degrees ---
  initial_adj = build_adjacency_list(num_vertices, edges)
  initial_degrees = get_degrees(num_vertices, initial_adj)

  # Check if degree list is valid
  if len(initial_degrees) != num_vertices:
    # This indicates an issue with build_adjacency_list or get_degrees if N>0
    print(
        f'Error: Degree list length mismatch! N={num_vertices},'
        f' len(degrees)={len(initial_degrees)}'
    )
    return -1_000_002.0  # Internal error state

  min_degree_required = 3
  degree_penalty = 0
  # Handle N=0 case where initial_degrees might be empty
  actual_min_degree = min(initial_degrees) if initial_degrees else 0

  # Check initial minimum degree constraint
  if num_vertices > 0:  # Only check penalty if graph can have edges
    for d in initial_degrees:
      if d < min_degree_required:
        degree_penalty += min_degree_required - d
    if actual_min_degree < min_degree_required:
      # Initial graph doesn't meet criteria, penalize immediately
      score = -100000.0 * degree_penalty - 10000.0  # Base penalty + deviation
      return score
  elif num_vertices == 0:
    return 0.0

  modified_adj = simplify_graph_simple_iterative(num_vertices, initial_adj)

  num_edges_after_simplification = (
      sum(len(neighbors) for neighbors in modified_adj.values()) // 2
  )

  cycle_counts = count_power_of_2_cycles(num_vertices, modified_adj, min_k=2)
  total_forbidden_cycle_count = (
      sum(cycle_counts.values())
      + 999 * cycle_counts[4]
      + 99 * cycle_counts[8]
      + 9 * cycle_counts[16]
  )

  cycle_penalty = -1.0 * float(total_forbidden_cycle_count)

  if cycle_penalty == 0.0:
    if num_edges_after_simplification > 0 or num_vertices == 0:
      max_possible_edges = num_vertices * (num_vertices - 1) / 2
      edge_bonus = 0
      if max_possible_edges > 0:
        edge_bonus = (
            num_edges_after_simplification / max_possible_edges
        ) * 1.0  # Max bonus 1.0
      return edge_bonus
    else:
      print('Warning: Score calculated on an empty graph (N>0) despite checks.')
      return -50001.0  # Error state, should have been reverted
  else:
    return cycle_penalty


def adjacency_list_to_edge_list(
    adj: Dict[int, Set[int]],
) -> List[Tuple[int, int]]:
  """Converts an adjacency list back to a canonical edge list (sorted tuples)."""
  edges = set()
  for u, neighbors in adj.items():
    for v in neighbors:
      # Add edge in canonical order (smaller index first)
      edge = tuple(sorted((u, v)))
      edges.add(edge)
  # Return as a sorted list for deterministic representation
  return sorted(list(edges))


def format_feedback_repr(feedback: Mapping[str, Any]) -> dict[str, str]:
  """Formats feedback dictionary for representation in code."""
  formatted_feedback = {}
  np.set_printoptions(
      threshold=np.inf
  )  # Ensure full array printing if numpy arrays are used
  for key, value in feedback.items():
    if isinstance(value, np.ndarray):
      repr_str = repr(value)
      cleaned_repr_str = re.sub(r'\s+', ' ', repr_str).replace('\n', '')
      array_content = cleaned_repr_str[
          cleaned_repr_str.find('(') + 1 : cleaned_repr_str.rfind(')')
      ]
      dtype_str = (
          f', dtype={value.dtype.name}'
          if value.dtype.name not in ['int64', 'float64']
          else ''
      )
      formatted_feedback[key] = f'np.array({array_content}{dtype_str})'
    elif isinstance(value, list):
      # Check if it's a list of tuples (likely our edges)
      if all(isinstance(item, tuple) for item in value):
        formatted_feedback[key] = repr(value)
      else:  # Handle other lists generically
        formatted_feedback[key] = repr(value)
    elif isinstance(value, (int, float, bool, str, dict, set, tuple)):
      formatted_feedback[key] = repr(value)
    elif isinstance(value, (np.integer, np.floating, np.bool_)):
      formatted_feedback[key] = repr(value.item())  # Convert numpy scalar
    else:
      formatted_feedback[key] = repr(value)  # Fallback
  return formatted_feedback


def evaluate(params: Any) -> tuple[dict[str, float], dict[str, str]]:
  """Evaluates a graph construction for the Erdos-Gyarfas conjecture.

  Stores the simplified graph (if valid) in the feedback.

  Args:
      params: The number of vertices for the graph construction.

  Returns:
      A tuple containing:
        - A dictionary with the final score.
        - A dictionary with feedback containing the best found graph,
          the number of vertices, and the best score.
  """
  result = {}
  feedback = {}

  num_vertices = int(params)
  logging.info('num_vertices: %s', num_vertices)

  # Validate num_vertices
  if num_vertices is None:
    error_msg = (
        f'Invalid params: {params}. Expected positive integer num_vertices > 0.'
    )
    print(f'Evaluation error: {error_msg}')
    result['score'] = -1_000_000.0
    feedback['error'] = error_msg
    feedback['best_score_found'] = -1_000_000.0
    feedback['num_vertices'] = params  # Store original invalid params
    feedback['best_graph'] = []  # Empty list for graph
    return result, format_feedback_repr(feedback)

  print(f'Starting evaluation for num_vertices = {num_vertices}')
  if num_vertices > 30:
    print(f'Warning: Cycle detection for N={num_vertices} might be very slow.')

  # --- Call the search function ---
  try:
    best_edges_tuples = search_for_best_graph(num_vertices)
    # Validate return type from search
    if not isinstance(best_edges_tuples, list) or not all(
        isinstance(e, tuple) and len(e) == 2 for e in best_edges_tuples
    ):
      # Allow list of lists as well, try to convert
      if isinstance(best_edges_tuples, list) and all(
          isinstance(e, list) and len(e) == 2 for e in best_edges_tuples
      ):
        best_edges_tuples = [tuple(e) for e in best_edges_tuples]
      else:
        raise TypeError(
            'Search function returned invalid type'
            f' {type(best_edges_tuples)} or structure, expected list of pairs'
            ' (tuples or lists).'
        )
    # Ensure canonical form (u,v) with u<v and remove duplicates from search
    # result
    initial_edges_set = set(
        tuple(sorted(e)) for e in best_edges_tuples if e[0] != e[1]
    )
    best_graph_edges = sorted(list(initial_edges_set))  # Use this cleaned list

  except (ValueError, TypeError, RuntimeError) as e:
    print(
        'Error during search or processing search result for'
        f' N={num_vertices}: {e}'
    )
    result['score'] = -1_000_000.0
    feedback['error'] = f'Search function failed or returned invalid data: {e}'
    feedback['best_score_found'] = -1_000_000.0
    feedback['num_vertices'] = num_vertices
    feedback['best_graph'] = []
    return result, format_feedback_repr(feedback)

  # --- Calculate Score (will simplify internally) ---
  # We pass the original (but cleaned) edges found by search to calculate_score.
  # calculate_score handles the simplification internally for scoring purposes.

  # --- Prepare Feedback: Simplify graph *again* for storage ---
  # This seems redundant, but calculate_score doesn't return the simplified
  # graph. We need the simplified *edge list* for feedback['best_graph'].

  # 1. Build initial adjacency list from the search result
  initial_adj = build_adjacency_list(num_vertices, best_graph_edges)
  initial_degrees = get_degrees(num_vertices, initial_adj)

  # 2. Check if the initial graph was valid (min_degree >= 3)
  min_degree_required = 3
  actual_min_degree = min(initial_degrees) if initial_degrees else 0

  if num_vertices > 0 and actual_min_degree < min_degree_required:
    # If the graph from search was already invalid, store it as is.
    # FunSearch should learn to avoid this via the low score.
    print(
        'Info: Storing original graph in feedback as initial min degree'
        f' ({actual_min_degree}) was < 3.'
    )
    graph_to_store_in_feedback = best_graph_edges
  elif num_vertices > 0:
    # If initial graph was valid, apply simplification for storage.
    # simplify_graph_simple_iterative returns the adj list (simplified or
    # original).
    simplified_adj = simplify_graph_simple_iterative(num_vertices, initial_adj)
    # Convert the resulting adjacency list back to an edge list for storage.
    graph_to_store_in_feedback = adjacency_list_to_edge_list(simplified_adj)
    # print(f"Debug: Storing simplified graph with"
    #       f" {len(graph_to_store_in_feedback)} edges.") # Optional debug
  else:  # Case N=0
    graph_to_store_in_feedback = []  # Empty graph for N=0

  final_score = calculate_score_hidden(num_vertices, graph_to_store_in_feedback)

  # --- Populate Results and Feedback ---
  result['score'] = final_score
  feedback['best_score_found'] = final_score
  feedback['num_vertices'] = num_vertices
  # Store the potentially simplified graph edge list
  feedback['best_graph'] = graph_to_store_in_feedback

  print(
      f'Evaluation complete for N = {num_vertices}. Final Score:'
      f' {final_score:.4f}'
  )

  feedback_formatted = format_feedback_repr(feedback)
  return result, feedback_formatted
