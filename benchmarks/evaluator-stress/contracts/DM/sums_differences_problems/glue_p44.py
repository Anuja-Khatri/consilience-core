"""Glue for problem 44 (code cell 6, compute_lower_bound). The construction is a finite set U of
non-negative integers with 0 in U (the reduction stated in the cell's docstring)."""
import math

import numpy as np


def to_scorer(c):
    return [[int(v) for v in np.asarray(c['U']).ravel()]]


def compose(out, c):
    return float(out)


def _contains_zero(c):
    u = np.asarray(c['U'])
    ok = bool(u.size) and bool(np.any(u == 0))
    return (ok, 0.0 if ok else math.inf)


predicates = {"contains_zero": _contains_zero}
