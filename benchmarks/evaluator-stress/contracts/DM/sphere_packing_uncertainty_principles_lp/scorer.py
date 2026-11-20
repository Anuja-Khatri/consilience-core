# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/sphere_packing_uncertainty_principles/sphere_packing_uncertainty_principles.ipynb, notebook code cells 1 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import sys
import numpy as np
import sympy
sys.set_int_max_str_digits(40000)  # as in the notebook's Utils cell (code cell 0)


def find_laguerre_combination(m, n, z):

  alpha = sympy.Rational(n, 2) - 1
  degrees = np.arange(1, 4 * m + 4, 2)
  x = sympy.symbols("x")
  lps = [
      sympy.polys.orthopolys.laguerre_poly(n=i, x=x, alpha=alpha, polys=False)
      for i in degrees
  ]

  num_lps = len(lps)
  num_conditions = 2 * m + 2  # Root at 0, double roots at z_i

  if num_lps < num_conditions:
    raise ValueError(
        "Not enough Laguerre polynomials to satisfy all conditions."
    )

  # Create a system of linear equations to solve for alpha_i
  A = sympy.Matrix(num_conditions, num_lps, lambda i, j: 0)
  b = sympy.Matrix(num_conditions, 1, lambda i, j: 0)

  b[1] = 1  # Set g'(0) = const

  # Condition 1: Root at 0 (g(0) = 0)
  for j in range(num_lps):
    A[0, j] = lps[j].subs(x, 0)
    A[1, j] = lps[j].diff(x).subs(x, 0)

  # Conditions 2 to 2m+2: Double roots at z_i (g(z_i) = 0 and g'(z_i) = 0)
  for i in range(0, m):
    zi = sympy.Rational(z[i])  # Ensure z_i is rational

    # g(z_i) = 0
    for j in range(num_lps):
      A[2 * i + 2, j] = lps[j].subs(x, zi)

    # g'(z_i) = 0 (derivative with respect to x)
    for j in range(num_lps):
      deriv_lp_j = lps[j].diff(x)  # Symbolic differentiation
      A[2 * i + 3, j] = deriv_lp_j.subs(x, zi)

  # Solve the linear system Ax = b for x (coefficients alpha_i)
  x = A.LUsolve(b)  # Use LU decomposition for efficient solving
  alpha_coeffs = [x[i] for i in range(num_lps)]
  g_fn = sum(alpha_coeffs[i] * lps[i] for i in range(len(alpha_coeffs)))
  return g_fn


ROOTS_NOT_ENFORCED = 10000


WRONG_Z_SHAPE = 10001


DERIVATIVES_NOT_ENFORCED = 10002


NO_SIGN_CHANGES = 10003


def get_score(m: int, n: int, zs: np.ndarray | list[float]) -> float:
  """Returns the score of the given Laguerre combination."""
  if len(zs) != m:
    return WRONG_Z_SHAPE

  g_fn = find_laguerre_combination(m, n, zs)
  x = sympy.symbols('x')
  dg_fn = sympy.diff(g_fn, x)

  div = sympy.prod([(x - sympy.Rational(z)) ** 2 for z in zs]) * x
  gq_fn = sympy.exquo(g_fn, div)

  g_fn.subs(x, sympy.Rational(0))
  dg_fn.subs(x, sympy.Rational(1))

  for z in zs:
    if g_fn.subs(x, sympy.Rational(z)) != 0:
      return ROOTS_NOT_ENFORCED
    if dg_fn.subs(x, sympy.Rational(z)) != 0:
      return DERIVATIVES_NOT_ENFORCED

  real_roots = sympy.real_roots(gq_fn, x)
  if not real_roots:
    return NO_SIGN_CHANGES

  approx_roots = list()
  largest_sign_change = 0

  for root in real_roots:
    approx_root = root.eval_rational(n=200)
    approx_root_p = approx_root + sympy.Rational(1e-198)
    approx_root_m = approx_root - sympy.Rational(1e-198)
    approx_roots.append(approx_root)
    is_sign_change = (
        gq_fn.subs(x, approx_root_p) > 0 and gq_fn.subs(x, approx_root_m) < 0
    ) or (gq_fn.subs(x, approx_root_p) < 0 and gq_fn.subs(x, approx_root_m) > 0)
    if is_sign_change:
      largest_sign_change = max(largest_sign_change, approx_root)

  return float(largest_sign_change)
