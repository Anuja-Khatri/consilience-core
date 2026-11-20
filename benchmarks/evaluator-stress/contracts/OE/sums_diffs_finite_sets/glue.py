"""Sums and differences of finite sets (AlphaEvolve B.6), OpenEvolve formulation (README, config.yaml):
U is a finite set of non-negative integers containing 0 (and a positive element);
C6(U) = 1 + log(|U - U| / |U + U|) / log(2 max(U) + 1)."""
import math

import numpy as np


def _ints(c):
    return [int(v) for v in np.asarray(c["U"], float).ravel()]


def c6_of(c):
    U = sorted(set(_ints(c)))
    S = {a + b for a in U for b in U}
    D = {a - b for a in U for b in U}
    return 1.0 + math.log(len(D) / len(S)) / math.log(2 * max(U) + 1)


def contains_zero_and_positive(c):
    a = np.asarray(c["U"], float).ravel()
    if a.size == 0 or not np.isfinite(a).all():
        return (False, math.inf)
    ok = bool(np.any(a == 0)) and bool(np.any(a > 0))
    return (ok, 0.0 if ok else math.inf)


quantities = {"c6": c6_of}
predicates = {"contains_zero_and_positive": contains_zero_and_positive}


# Record map (spec 6.4): the scorer's combined_score for a construction whose c6 equals v.
maps = {"score_from_c6": lambda v: v / 1.158417281556896}
