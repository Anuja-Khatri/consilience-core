"""Glue for smale_problem. Independent of the scorer."""
import numpy as np

GRID = 91   # evaluate() calls evaluate_smale_conjecture_h(best_construction, 91)


def to_scorer(c):
    return [np.array(c['z'], dtype=complex), GRID]
