"""Glue for erdos_gyarfas_conjecture (n = 16 vertices). Construction = edge list E (m x 2) of a simple graph
on {0, ..., 15}."""
import math

import numpy as np

N = 16


def to_scorer(c):
    return [N, [(int(u), int(v)) for u, v in np.asarray(c['E']).reshape(-1, 2)]]


def _min_degree_3(c):
    E = np.asarray(c['E']).reshape(-1, 2)
    deg = [0] * N
    seen = set()
    for u, v in E:
        u, v = int(u), int(v)
        if not (0 <= u < N and 0 <= v < N) or u == v:
            return (False, math.inf)
        e = (min(u, v), max(u, v))
        if e in seen:
            continue
        seen.add(e)
        deg[u] += 1
        deg[v] += 1
    short = sum(max(0, 3 - d) for d in deg)
    return (short == 0, 0.0 if short == 0 else math.inf)


predicates = {"min_degree_3": _min_degree_3}
