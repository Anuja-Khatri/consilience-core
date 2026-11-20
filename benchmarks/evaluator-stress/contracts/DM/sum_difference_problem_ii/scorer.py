# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/sum_difference_problem_ii/sum_difference_problem_ii.ipynb, notebook code cells 0 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import math
import re
from typing import Any, Mapping
import numba
import numpy as np
njit = numba.njit

#@title Verification code

# pylint: disable=unused-import
# pylint: disable=g-bad-import-order



def get_score(best_list):
  """Returns the score for the given list using Numba."""
  if len(best_list) < 2:
    return 0

  # if the list contains non-integers, return 0
  if not all(isinstance(x, int) for x in best_list):
    return 0

  return get_score_numba(best_list) + (1.0 - 1.0 / len(set(best_list))) / 100.0


@njit
def get_score_numba(best_list):
  """Returns the score for the given list using Numba."""

  a_minus_a = set()
  for i in best_list:
    for j in best_list:
      a_minus_a.add(i - j)

  a_plus_a = set()
  for i in best_list:
    for j in best_list:
      a_plus_a.add(i + j)

  lhs = len(a_minus_a)
  rhs = len(a_plus_a)

  try:
    return math.log(lhs) / math.log(rhs)
  except ValueError:
    return 0


def format_feedback_repr(feedback):
  """Formats feedback dictionary for representation in code."""
  formatted_feedback = {}
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


def evaluate(
    hypers: Mapping[str, Any],
) -> tuple[dict[str, float], dict[str, str]]:
  """Returns the ratio for the Sum-Difference Conjecture using joint distribution."""
  result = {}
  feedback = {}
  del hypers
  best_list = search_for_best_set()
  score = get_score(best_list)

  result['score'] = score
  feedback['best_list'] = best_list
  feedback['best_score_found'] = score
  feedback = format_feedback_repr(feedback)
  return result, feedback
