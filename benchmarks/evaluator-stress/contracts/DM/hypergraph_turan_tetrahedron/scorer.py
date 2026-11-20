# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/hypergraph_turan_tetrahedron/hypergraph_turan_tetrahedron.ipynb, notebook code cells 0 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import re
import numpy as np
from scipy import optimize

#@title Verification code

"""Initial program for the Turan Tetrahedron problem."""

# pylint: disable=unused-import
# pylint: disable=g-bad-import-order


linprog = optimize.linprog







def get_hypergraph_from_list(sequence, n):
  """Returns the hypergraph from a list of coefficients."""
  hypergraph = {}
  idx_count = 0
  for a in range(n):
    for b in range(n):
      if a < b:
        if sequence[idx_count] > 0.5:
          hypergraph[(a, a, b)] = 1
        idx_count += 1
      elif b < a:
        if sequence[idx_count] > 0.5:
          hypergraph[(b, a, a)] = 1
        idx_count += 1
  for a in range(n):
    for b in range(a + 1, n):
      for c in range(b + 1, n):
        if sequence[idx_count] > 0.5:
          hypergraph[(a, b, c)] = 1
        idx_count += 1
  return hypergraph


def remove_k4s(hypergraph, n):
  """Removes k4s from the hypergraph."""
  new_hypergraph = hypergraph.copy()

  # a a b b
  for a in range(n):
    for b in range(a + 1, n):
      if (a, a, b) in new_hypergraph and (a, b, b) in new_hypergraph:
        del new_hypergraph[(a, a, b)]

  # a a b c
  for a in range(n):
    for b in range(a + 1, n):
      for c in range(b + 1, n):
        if (
            (a, a, b) in new_hypergraph
            and (a, a, c) in new_hypergraph
            and (a, b, c) in new_hypergraph
        ):
          del new_hypergraph[(a, a, c)]

  # b a a c
  for a in range(n):
    for b in range(a):
      for c in range(a + 1, n):
        if (
            (b, a, a) in new_hypergraph
            and (a, a, c) in new_hypergraph
            and (b, a, c) in new_hypergraph
        ):
          del new_hypergraph[(b, a, c)]

  # b c a a
  for a in range(n):
    for b in range(a):
      for c in range(b + 1, a):
        if (
            (c, a, a) in new_hypergraph
            and (b, a, a) in new_hypergraph
            and (b, c, a) in new_hypergraph
        ):
          del new_hypergraph[(b, a, a)]

  # a b c d
  for a in range(n):
    for b in range(a + 1, n):
      for c in range(b + 1, n):
        for d in range(c + 1, n):
          if (
              (a, b, c) in new_hypergraph
              and (a, b, d) in new_hypergraph
              and (a, c, d) in new_hypergraph
              and (b, c, d) in new_hypergraph
          ):
            del new_hypergraph[(a, c, d)]

  return new_hypergraph


def get_score(hypergraph, weights):
  """Returns the score for a hypergraph."""
  score = 0
  for key in hypergraph:
    if key[0] == key[1] or key[1] == key[2] or key[2] == key[0]:
      coeff = 3.0
    else:
      coeff = 6.0
    score += coeff * weights[key[0]] * weights[key[1]] * weights[key[2]]
  return score


def evaluate_sequences(sequence, weights) -> float:
  """Evaluates a sequence of coefficients."""
  n = len(weights)
  weights = np.array(weights)
  weights = np.clip(weights, 0, 1)
  # normalize so that sum(weights) = 1
  weights /= np.sum(weights)
  hypergraph = get_hypergraph_from_list(sequence, n)
  hypergraph = remove_k4s(hypergraph, n)
  score = get_score(hypergraph, weights)
  return score


def format_feedback_repr(feedback):
  """Formats feedback dictionary for representation in code."""
  formatted_feedback = {}
  np.set_printoptions(threshold=np.inf)
  for key, value in feedback.items():
    if isinstance(value, np.ndarray):
      repr_str = repr(value)  # Get repr string (e.g., "array([[...], [...]])")
      cleaned_repr_str = re.sub(r'[\n\s]+', ' ', repr_str)  # Clean up

      # Remove the leading "array(" and trailing ")" from repr string, then wrap
      # with "np.array(...)"
      array_content = cleaned_repr_str[
          6:-1
      ]  # Extract content inside "array(...)"

      if np.iscomplexobj(value):
        formatted_feedback[key] = (  # Use extracted content in np.array
            f'np.array({array_content}, dtype=np.complex128)'
        )
      elif not np.issubdtype(value.dtype, np.inexact):
        formatted_feedback[key] = f'np.array({array_content}, dtype=np.float64)'
      else:
        formatted_feedback[key] = f'np.array({array_content})'

    elif isinstance(value, list):
      formatted_feedback[key] = repr(value)  # Use standard repr for lists
    else:
      formatted_feedback[key] = repr(value)
  return formatted_feedback


def evaluate(weights_length) -> tuple[dict[str, float], dict[str, str]]:
  """Returns the numerical bound for the polygons if valid, or 0 if invalid."""
  result = {}
  feedback = {}
  n = weights_length
  sequence_length = (-1 + n) * n * (4 + n) // 6
  best_sequence, best_weights = search_for_best_sequence(
      sequence_length, weights_length
  )
  result['score'] = evaluate_sequences(best_sequence, best_weights)

  best_weights = np.array(best_weights)
  best_weights = np.clip(best_weights, 0, 1)
  best_weights /= np.sum(best_weights)

  feedback['best_sequence'] = best_sequence
  feedback['best_weights'] = best_weights
  feedback['best_score_found'] = result['score']
  feedback = format_feedback_repr(feedback)
  return result, feedback
