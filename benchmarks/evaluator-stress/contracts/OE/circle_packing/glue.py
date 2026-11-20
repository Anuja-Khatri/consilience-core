"""Circle packing in the unit square, n = 26 (AlphaEvolve B.12; README, initial_program docstring).
run_packing() returns (centers, radii, sum_radii); sum_radii is a self-report (claimed)."""
import math

import numpy as np


def sum_radii_of(c):
    return float(math.fsum(float(v) for v in np.asarray(c["radii"], float).ravel()))


def compose(out, cand):
    """Output adapter, no value changed. (1) An EvaluationResult object is unwrapped to its metrics
    dict. (2) This evaluator says 'rejected' by validity == 0.0 (with combined_score 0.0) rather than
    by an error key, and 0.0 is also a legitimate score (all radii zero), so a rejection is marked
    with an 'error' key for the contract's reject rule."""
    m = getattr(out, "metrics", out)
    if isinstance(m, dict) and m.get("validity") == 0.0 and "error" not in m:
        m = dict(m, error="validity 0.0 (the evaluator rejected the packing)")
    return m


quantities = {"sum_radii": sum_radii_of}


# Record map (spec 6.4): the scorer's combined_score for a construction whose sum_radii equals v.
maps = {"score_from_sum": lambda v: v / 2.635}
