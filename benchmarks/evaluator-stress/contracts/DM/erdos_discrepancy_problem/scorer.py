# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/erdos_discrepancy_problem/erdos_discrepancy_problem.ipynb, notebook code cells 0 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import re
from typing import List
import numba
import numpy as np
njit = numba.njit

#@title Verification code

# pylint: disable=unused-import
# pylint: disable=g-bad-import-order
@njit
def calculate_discrepancy(sequence: tuple[int, ...]) -> tuple[int, int]:
  """Calculates the discrepancy of a given sign sequence."""
  max_discrepancy = 0
  violating_seq_count = 0
  length = len(sequence)
  for d in range(1, length + 1):
    # if the sequence length is divisible by d
    if length % d == 0:
      subsequence_sum = 0
      for i in range(d - 1, length, d):
        subsequence_sum += sequence[i]
      max_discrepancy = max(max_discrepancy, abs(subsequence_sum))
      if abs(subsequence_sum) > 2:
        violating_seq_count += 1
  return max_discrepancy, violating_seq_count


def calculate_discrepancy_score(sequence: List[int]) -> float:
  """Calculates a score based on the length of the initial discrepancy 2 subsequence."""
  if not sequence:
    return 0.0
  sequence = sequence[1:]
  for i in range(len(sequence)):
    val = sequence[i]
    if val != 1 and val != -1:
      return -1_000_000.0
  tuple_sequence = tuple(sequence)
  for length in range(1, len(tuple_sequence) + 1):
    initial_subsequence = tuple_sequence[:length]
    discrepancy, violating_seq_count = calculate_discrepancy(
        initial_subsequence
    )
    if discrepancy > 2:
      # We went too far, the discrepancy increased at this length
      return float(length - 1) + 1.0 / (violating_seq_count + 1)
  # If the entire sequence has discrepancy <= 2
  return float(len(tuple_sequence))


def format_feedback_repr(feedback):
  """Formats feedback dictionary for representation in code (same as 2D)."""
  formatted_feedback = {}
  np.set_printoptions(threshold=np.inf)
  for key, value in feedback.items():
    if isinstance(value, np.ndarray):
      repr_str = repr(value)
      cleaned_repr_str = re.sub(r'[\n\s]+', ' ', repr_str)
      array_content = cleaned_repr_str[6:-1]
      if np.iscomplexobj(value):
        formatted_feedback[key] = (
            f'np.array({array_content}, dtype=np.complex128)'
        )
      elif not np.issubdtype(value.dtype, np.inexact):
        formatted_feedback[key] = f'np.array({array_content}, dtype=np.float64)'
      else:
        formatted_feedback[key] = f'np.array({array_content})'
    elif isinstance(value, list):
      formatted_feedback[key] = repr(value)
    else:
      formatted_feedback[key] = repr(value)
  return formatted_feedback


def evaluate(params) -> tuple[dict[str, float], dict[str, str]]:
  """Evaluates sign sequences for the Erdős discrepancy problem (C=2)."""
  result = {}
  feedback = {}
  del params  # We are not using any input parameters for this search
  best_sequence = search_for_long_low_discrepancy_sequence()
  score = calculate_discrepancy_score(best_sequence)
  result['score'] = score
  feedback['best_score_found'] = score
  feedback['low_discrepancy_sequence'] = best_sequence
  feedback = format_feedback_repr(feedback)
  return result, feedback
