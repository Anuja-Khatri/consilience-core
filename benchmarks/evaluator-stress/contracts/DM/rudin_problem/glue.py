"""Glue for rudin_problem (degree k = 10 on S^2, the evaluator's default). c = the 2k+1 real coefficients
of a degree-k real spherical harmonic sum_m c_m Y_k^m."""
import math

import numpy as np


def to_scorer(c):
    return [np.array(c['c'], dtype=float)]


def _nonzero(c):
    ok = bool(np.any(np.asarray(c['c'], dtype=float) != 0))
    return (ok, 0.0 if ok else math.inf)


predicates = {"nonzero_harmonic": _nonzero}
