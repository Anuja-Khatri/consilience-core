"""Glue for edges_vs_triangles. Each row of S holds the 20 part weights of a complete multipartite
graph (normalised by the scorer); each row gives one (edge density, triangle density) point."""
import math
from fractions import Fraction

import numpy as np


def to_scorer(c):
    return [np.array(c['S'], dtype=np.float64, copy=True), 20]


def _rows_positive(c):
    S = np.asarray(c['S'], dtype=float)
    bad = [i for i, row in enumerate(S) if sum(Fraction(float(v)) for v in row) <= 0]
    return (not bad, 0.0 if not bad else math.inf)


predicates = {"rows_positive_mass": _rows_positive}
