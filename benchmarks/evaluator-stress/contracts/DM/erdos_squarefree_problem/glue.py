"""Glue for erdos_squarefree_problem, modulus M = 625. Construction = residues A in {0..624}; valid means
gcd(ab+1, M) is NOT squarefree for every pair (a, b) in A x A including a = b (the prompt's proxy for
'ab+1 is never squarefree'), so every lift of A to the integers has ab+1 non-squarefree."""
import math

import numpy as np

M = 625


def to_scorer(c):
    return [[int(v) for v in np.asarray(c['A']).ravel()], M]


def _not_squarefree(g):
    p = 2
    while p * p <= g:
        if g % (p * p) == 0:
            return True
        p += 1
    return False


def _all_pairs_nonsquarefree(c):
    A = [int(v) for v in np.asarray(c['A']).ravel()]
    bad = sum(1 for i, a in enumerate(A) for b in A[i:] if not _not_squarefree(math.gcd(a * b + 1, M)))
    return (bad == 0, 0.0 if bad == 0 else math.inf)


predicates = {"all_pairs_gcd_not_squarefree": _all_pairs_nonsquarefree}
