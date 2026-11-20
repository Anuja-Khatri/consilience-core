# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 04fbf24280c069892a7830cb2acbadd5ce51db19, experiments/difference_bases/difference_bases.ipynb, notebook code cell 0 (0-based over code cells; function(s) get_score) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np, itertools, math
from typing import List, Tuple

def get_score(combined_set):
  mylist = list(combined_set)

  temp_B_start_list = []
  for x in mylist:  # Ensure all elements are valid integers
    if isinstance(x, (int, float, np.integer, np.floating)) and not np.isnan(x):
      temp_B_start_list.append(int(x))
    else:
      return -float('inf'), False  # Invalid element in list

  B_start = sorted(list(set(temp_B_start_list)))
  if (
      0 not in B_start
  ):  # Ensure 0 is in B_start for the greedy completion strategy
    B_start.append(0)
    B_start.sort()

  differences = set()
  # print(len(B_start))
  if len(B_start) > 2000:
    return -float('inf')
  for i in range(len(B_start)):
    for j in range(i + 1, len(B_start)):
      diff = B_start[j] - B_start[i]
      differences.add(diff)

  max_achieved_diff = 0
  if differences:
    max_achieved_diff = max(differences)

  for v_val in range(1, max_achieved_diff + 2):
    if v_val not in differences:
      if v_val == 1:
        return -100
      # print(v_val,[int(x) for x in combined_set], combined_set, differences)
      return len(B_start) ** 2 / (v_val - 1)
