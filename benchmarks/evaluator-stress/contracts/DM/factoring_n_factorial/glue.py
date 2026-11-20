"""Glue for factoring_n_factorial (N = 180). The candidate assigns each prime factor of N!
(with multiplicity, in increasing order) to one of N groups; the score is the smallest group product."""
import numpy as np
import sympy

N = 180


def to_scorer(c):
    factors = sorted(p for k in range(1, N + 1) for p, e in sympy.factorint(k).items() for _ in range(e))
    return [[int(v) for v in np.asarray(c['assignment']).ravel()], factors, N]


def compose(out, c):
    return out[0] if isinstance(out, tuple) else out
