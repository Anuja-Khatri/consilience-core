# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/factoring_n_factorial/factoring_n_factorial.ipynb, notebook code cells 0 (0-based, counting code cells only) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import math
import re
import time
import numpy as np
import sympy
from sympy.ntheory import factorint

#@title Verification code

# pylint: disable=unused-import
# pylint: disable=g-bad-import-order








def solve(n, t_guess=None):
  """Finds a good initial partition using Andrew Sutherland's algorithm."""
  if t_guess is None:
    t = math.ceil(n / 3)
  else:
    t = t_guess
  primes = list(sympy.primerange(1, t))
  pi = {
      p: i + 1 for i, p in enumerate(primes)
  }  # Use dictionary for mapping primes to indices

  prime_exponents = {}  # Use dictionary to store exponents of primes in n!
  for p in primes:
    exponent = 0
    for i in range(1, int(math.log(n, p)) + 1):
      exponent += n // (p**i)
    prime_exponents[pi[p]] = exponent

  l_list = []
  for p in sympy.primerange(t, n + 1):
    l_list.extend([p] * (n // p))

  i = len(primes)
  minm = 0
  t_start = time.time()

  group_products = [1] * n  # Track product of each group
  group_assignments_primes = [
      [] for _ in range(n)
  ]  # Keep track of assigned primes in each group

  while True:
    while i > 0 and prime_exponents.get(i, 0) == 0:
      i -= 1
    if i == 0:
      break
    prime_counts = {}
    m = max(math.ceil(t / primes[i - 1]), minm)  # primes is 0-indexed in Python
    while m < t:
      factors_m = factorint(m)
      prime_counts = {}
      for q, count in factors_m.items():
        if q in pi:  # Check if prime factor is in P
          prime_counts[pi[q]] = count
      prime_counts[i] = (
          prime_counts.get(i, 0) + 1
      )  # Use .get() to handle missing key and increment

      valid_m = True
      for j in prime_counts:
        if prime_exponents.get(j, 0) < prime_counts[j]:
          valid_m = False
          break
      if valid_m:
        break

      m += 1
      if prime_exponents.get(i, 0) >= prime_exponents.get(
          i, 0
      ):  # Use .get() to handle missing keys
        minm = m

    if m == t:
      break

    for j in prime_counts:
      if j in prime_exponents:
        prime_exponents[j] = prime_exponents[j] - prime_counts[j]

    product_val = m * primes[i - 1]
    l_list.append(product_val)

    # Assign product_val to a group greedily
    min_product_group = min(range(n), key=lambda k: group_products[k])
    group_products[min_product_group] *= product_val

    factors = factorint(product_val)  # Get prime factors of product_val
    for p, exponent in factors.items():
      for _ in range(exponent):  # Add each prime factor to the assigned group
        group_assignments_primes[min_product_group].append(p)
  # Assign remaining primes in l_list to groups greedily
  prime_factor_list = []
  for p in sympy.primerange(1, n + 1):
    count = 0
    for k in range(1, int(math.log(n, p)) + 1):
      count += n // (p**k)
    prime_factor_list.extend([p] * count)

  assigned_primes_count = {}  # Count of assigned primes so far
  for group_prime_list in group_assignments_primes:
    for prime in group_prime_list:
      assigned_primes_count[prime] = assigned_primes_count.get(prime, 0) + 1

  for prime in prime_factor_list:
    if assigned_primes_count.get(prime, 0) < prime_factor_list.count(
        prime
    ):  # Check if prime is already fully assigned
      min_product_group = min(range(n), key=lambda k: group_products[k])
      group_products[min_product_group] *= prime
      group_assignments_primes[min_product_group].append(prime)
      assigned_primes_count[prime] = assigned_primes_count.get(prime, 0) + 1

  partition_assignment = []
  prime_factor_list_input = []
  for p in sympy.primerange(
      2, n + 1
  ):  # Corrected range to start from 2 for prime factors
    count = 0
    for k in range(1, int(math.log(n, p)) + 1):
      count += n // (p**k)
    prime_factor_list_input.extend([p] * count)

  group_assignments_prime_counts = [{} for _ in range(n)]
  for group_idx in range(n):
    for prime in group_assignments_primes[group_idx]:
      group_assignments_prime_counts[group_idx][prime] = (
          group_assignments_prime_counts[group_idx].get(prime, 0) + 1
      )

  for prime in prime_factor_list_input:
    assigned_group = -1
    for group_idx in range(n):
      if group_assignments_prime_counts[group_idx].get(prime, 0) > 0:
        assigned_group = group_idx
        group_assignments_prime_counts[group_idx][prime] -= 1
        break
    partition_assignment.append(assigned_group)

  t_end = time.time()
  print(t_end - t_start)

  assert all(l >= t for l in l_list)

  print(n, len(l_list), len(l_list) >= n)
  return n, len(l_list), len(l_list) >= n, l_list, t, partition_assignment


def create_partition_assignment(n):
  _, _, _, _, _, partition_assignment = solve(n)

  prime_factor_list_input = []
  for p in sympy.primerange(1, n + 1):
    count = 0
    for k in range(1, int(math.log(n, p)) + 1):
      count += n // (p**k)
    prime_factor_list_input.extend([p] * count)

  assert len(partition_assignment) == len(prime_factor_list_input)
  return partition_assignment


def find_largest_t(n, t_lower_bound, t_upper_bound):
  """Finds the largest valid t within a given range for the solve function."""
  best_t = t_lower_bound
  best_result = None
  best_partition_assignment = None

  while t_lower_bound <= t_upper_bound:
    t_mid = (t_lower_bound + t_upper_bound) // 2
    print(f'Trying T = {t_mid}...')
    try:
      n_val, length_l, ge_n, l_result, t_actual, partition_assignment = solve(
          n, t_mid
      )
      if ge_n:  # If solution is valid for t_mid
        best_t = max(best_t, t_mid)
        best_result = (n_val, length_l, ge_n, l_result, t_actual)
        best_partition_assignment = partition_assignment
        t_lower_bound = t_mid + 1  # Try for a larger T
      else:
        t_upper_bound = t_mid - 1  # Try for a smaller T
    except (
        AssertionError
    ):  # Handle potential assertion errors if solution is not found
      t_upper_bound = t_mid - 1  # Try for a smaller T

  if best_result:
    print(f'\nLargest T found: {best_t}')
    print(
        f'Results for T = {best_t}: n={best_result[0]},'
        f' length_l={best_result[1]}, len(l_list)>=n={best_result[2]}'
    )
    return best_t, best_result, best_partition_assignment
  else:
    print(f'No valid T found in range [{t_lower_bound}, {t_upper_bound}].')
    return None, None, None


def find_good_initial_partition(n):
  """Finds a good initial partition for n unit cubes into a container cube (3D)."""
  prime_factors_n_factorial_input = []
  for p in sympy.primerange(2, n + 1):
    count = 0
    for k in range(1, int(math.log(n, p)) + 1):
      count += n // (p**k)
    prime_factors_n_factorial_input.extend([p] * count)
  print(f'Prime factors of {n}!:', prime_factors_n_factorial_input)

  # --- Optimized Solution with Initial T = N/3 ---
  print('--- Optimized Solution with T = ceil(N/3) ---')
  n_val, length_l, ge_n, _, t_actual, partition_assignment = solve(n)
  print(
      f'Results for T = {t_actual}: n={n_val}, length_l={length_l},'
      f' len(l_list)>=n={ge_n}'
  )
  print('Partition Assignment:', partition_assignment)

  # Verify partition assignment
  group_products_verification = [1] * n
  for i in range(len(prime_factors_n_factorial_input)):
    group_index = partition_assignment[i]
    group_products_verification[group_index] *= prime_factors_n_factorial_input[
        i
    ]
  print('Group Products Verification:', group_products_verification)
  t_verification = min(group_products_verification)
  print('T Verification:', t_verification)

  # --- Binary Search for Largest T ---
  print('\n--- Binary Search for Largest T ---')
  t_lower_bound_search = math.ceil(
      n / 10
  )  # Example lower bound, adjust as needed
  t_upper_bound_search = math.ceil(
      n / 2
  )  # Example upper bound, adjust as needed

  largest_t, _, best_partition_assignment = find_largest_t(
      n, t_lower_bound_search, t_upper_bound_search
  )

  if largest_t:
    return best_partition_assignment
  else:
    return []


def calculate_smallest_group_product(curr_list, factors, num_groups):
  """Calculates the smallest group product for a list of factors."""
  if len(curr_list) != len(factors):
    return -1_000_001, 0
  # if any of the coordinates are nan, return -1_000_000
  for i in range(len(curr_list)):
    if np.isnan(curr_list[i]):
      return -1_000_002, 0
  # if any element of curr_list is not an integer in [1, num_groups], return
  # -1_000_000
  for i in range(len(curr_list)):
    if curr_list[i] not in range(num_groups):
      return -1_000_003, 0

  products = [1] * num_groups
  for i in range(len(curr_list)):
    products[curr_list[i]] *= factors[i]
  min_index = np.argmin(products)
  return products[min_index], min_index


def calculate_second_smallest_group_product(curr_list, factors, num_groups):
  """Calculates the smallest group product for a list of factors."""
  if len(curr_list) != len(factors):
    return -1_000_001, 0
  # if any of the coordinates are nan, return -1_000_000
  for i in range(len(curr_list)):
    if np.isnan(curr_list[i]):
      return -1_000_002, 0
  # if any element of curr_list is not an integer in [1, num_groups], return
  # -1_000_000
  for i in range(len(curr_list)):
    if curr_list[i] not in range(num_groups):
      return -1_000_003, 0

  products = [1] * num_groups
  for i in range(len(curr_list)):
    products[curr_list[i]] *= factors[i]
  # sort products in descending order
  products = sorted(products)
  second_smallest = products[1]
  return second_smallest


def get_list_of_prime_factors(max_number_to_factorize):
  """Returns a list of prime factors for a given number."""
  prime_factor_list = []
  for number_to_factorize in range(1, max_number_to_factorize + 1):
    prime_factors_dict = factorint(number_to_factorize)
    for prime, count in prime_factors_dict.items():
      prime_factor_list.extend([prime] * count)
  return sorted(prime_factor_list)


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


def evaluate(num_groups: int) -> tuple[dict[str, float], dict[str, str]]:
  """Evaluates the packing of n!

  into num_groups and returns a score and feedback.

  Args:
    num_groups: The number of groups to pack into.

  Returns:
    A tuple containing:
      - A dictionary with the score.
      - A dictionary with feedback information.
  """
  result = {}
  feedback = {}
  factors = get_list_of_prime_factors(num_groups)
  print(f'factors: {factors}')
  best_list = search_for_best_partition(factors, num_groups)
  score, _ = calculate_smallest_group_product(best_list, factors, num_groups)
  second_smallest_score = calculate_second_smallest_group_product(
      best_list, factors, num_groups
  )
  result['score'] = score - 10.0 / second_smallest_score
  feedback['best_score_found'] = score
  feedback['best_list'] = best_list
  feedback = format_feedback_repr(feedback)
  return result, feedback
