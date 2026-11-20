# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/rudin_problem/rudin_problem.ipynb, notebook code cells 2 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import collections
import time
from typing import Any, Dict, Tuple, Union
import numpy as np
import scipy
import sympy
import sympy.physics.wigner

# @title Evaluator

import collections
import time
from typing import Any, Dict, Tuple, Union
import numpy as np
import scipy
import sympy


def lm_to_k(l: int, m: int) -> int:
  """Helper to get array index 'k' from an (l, m) pair."""
  return l**2 + l + m


def get_random_spherical_harmonic(
    k: int,
) -> Tuple[np.ndarray, Dict[Tuple[int, int], float]]:
  """Generates a random spherical harmonic of degree k."""
  l_max = k
  n_total = (l_max + 1) ** 2
  c_array = np.zeros(n_total)
  real_coeffs_dict = {}

  random_coeffs = np.random.randn(2 * k + 1)

  for i, m in enumerate(range(-k, k + 1)):
    coeff_val = random_coeffs[i]
    arr_index = lm_to_k(k, m)
    c_array[arr_index] = coeff_val
    real_coeffs_dict[(k, m)] = coeff_val

  return c_array, real_coeffs_dict


def parse_coefficients(
    coeffs: Union[np.ndarray, list[float]],
) -> Tuple[np.ndarray, Dict[Tuple[int, int], float]]:
  """Parses coefficients into the internal array format."""
  k = (len(coeffs) - 1) // 2
  l_max = k
  n_total = (l_max + 1) ** 2
  c_array = np.zeros(n_total)

  for i, m in enumerate(range(-k, k + 1)):
    coeff_val = coeffs[i]
    arr_index = lm_to_k(k, m)
    c_array[arr_index] = coeff_val

  return c_array


def calculate_norm_ratio_analytical(
    real_coeff_array: Union[np.ndarray, list[float]],
) -> float:
  """Computes the exact ratio ||f||_L4 / ||f||_L2 analytically using SymPy."""
  if not isinstance(real_coeff_array, np.ndarray):
    real_coeff_array = np.array(real_coeff_array, dtype=float)
  n = real_coeff_array.shape[0]
  if n == 0:
    return 0.0

  # === Step 1: Parse Input Array ===
  sqrt_n = np.sqrt(n)
  l_max_plus_1 = int(round(sqrt_n))
  if l_max_plus_1**2 != n:
    raise ValueError(f"Input array length N={n} is not a perfect square.")
  real_coeffs_dict = {}
  for k in range(n):
    if not np.isclose(real_coeff_array[k], 0.0):
      l = int(np.floor(np.sqrt(k)))
      m = k - l**2 - l
      real_coeffs_dict[(l, m)] = real_coeff_array[k]
  if not real_coeffs_dict:
    return 0.0

  # === Step 2: Convert to Complex Basis ===
  complex_coeffs_dict = collections.defaultdict(complex)
  l_values = collections.defaultdict(int)
  for l, m in real_coeffs_dict:
    l_values[l] = max(l_values[l], abs(m))
  for l, max_m in l_values.items():
    d_l0 = real_coeffs_dict.get((l, 0), 0.0)
    if not np.isclose(d_l0, 0.0):
      complex_coeffs_dict[(l, 0)] = d_l0
    for m_pos in range(1, max_m + 1):
      d_lm_pos = real_coeffs_dict.get((l, m_pos), 0.0)
      d_lm_neg = real_coeffs_dict.get((l, -m_pos), 0.0)
      if np.isclose(d_lm_pos, 0.0) and np.isclose(d_lm_neg, 0.0):
        continue
      c_lm_pos = (d_lm_pos - 1j * ((-1) ** m_pos) * d_lm_neg) / np.sqrt(2)
      c_lm_neg = ((-1) ** m_pos * d_lm_pos + 1j * d_lm_neg) / np.sqrt(2)
      complex_coeffs_dict[(l, m_pos)] = c_lm_pos
      complex_coeffs_dict[(l, -m_pos)] = c_lm_neg

  # === Step 3: L2-Normalize ===
  l2_norm_sq = sum(abs(c) ** 2 for c in complex_coeffs_dict.values())
  l2_norm = np.sqrt(l2_norm_sq)
  if np.isclose(l2_norm, 0):
    return 0.0
  normalized_complex_coeffs = {
      k: v / l2_norm for k, v in complex_coeffs_dict.items()
  }
  coeff_items = list(normalized_complex_coeffs.items())

  # === Step 4: Get Coefficients of |g|^2 ===
  coeffs_of_g_squared = collections.defaultdict(complex)
  for (l1, m1), c1 in coeff_items:
    for (l2, m2), c2 in coeff_items:
      m_val = m1 - m2
      l_start, l_end = abs(l1 - l2), l1 + l2
      if (l1 + l2 + l_start) % 2 != 0:
        l_start += 1
      for l in range(l_start, l_end + 1, 2):

        w3j_1_sym = sympy.physics.wigner.wigner_3j(l1, l2, l, 0, 0, 0)
        w3j_1 = float(w3j_1_sym.evalf())
        if np.isclose(w3j_1, 0.0):
          continue

        w3j_2_sym = sympy.physics.wigner.wigner_3j(l1, l2, l, m1, -m2, -m_val)
        w3j_2 = float(w3j_2_sym.evalf())
        if np.isclose(w3j_2, 0.0):
          continue

        prefactor = np.sqrt(
            (2 * l1 + 1) * (2 * l2 + 1) * (2 * l + 1) / (4 * np.pi)
        )
        gaunt_val = prefactor * w3j_1 * w3j_2

        term = c1 * np.conj(c2) * ((-1) ** m2) * gaunt_val
        coeffs_of_g_squared[(l, m_val)] += term

  # === Step 5: Calculate Final Norm ===
  l4_norm_fourth_power = 0.0
  for (l, m), b_lm in coeffs_of_g_squared.items():
    b_l_neg_m = coeffs_of_g_squared.get((l, -m), 0.0)
    l4_norm_fourth_power += (-1) ** m * b_lm * b_l_neg_m

  # === Step 6: Return Result ===
  return np.power(np.real(l4_norm_fourth_power), 0.25)


def get_score(coeffs: Union[np.ndarray, list[float]]) -> float:
  # Degenerate coefficients.
  score = -calculate_norm_ratio_analytical(parse_coefficients(coeffs))
  return score


def evaluate(
    degree: int = 10,
) -> tuple[dict[str, float], dict[str, str]]:
  """Returns the numerical bound for the polygons if valid, or 0 if invalid."""
  result = {}
  feedback = {}

  # Start construction evaluation
  time_start = time.time()
  xs = get_coefficients(degree)
  if len(xs) != 2 * degree + 1:
    feedback["error_message"] = "Wrong shape of coefficients."
    result["score_max"] = -10000.0
    return result, feedback

  if np.max(np.abs(xs)) < 1e-3:
    feedback["error_message"] = "Too small coefficients."
    result["score_max"] = -10000.0
    return result, feedback

  if np.max(np.abs(xs)) > 1e5:
    feedback["error_message"] = "Too large coefficient appearing."
    result["score_max"] = -10000.0
    return result, feedback

  feedback["degree"] = str(degree)
  feedback["suggested_coeffs"] = xs.copy()

  print(f"Degree: {degree}, Suggested coefficients: {xs}")

  score = get_score(xs)
  result["score_max"] = score
  feedback["ratio_value"] = score

  print(f"Time taken for full evaluation: {time.time() - time_start:.2f}s")

  return result, feedback
