"""Glue for hypergraph_turan_tetrahedron (n = 6 vertex classes, sequence length (n-1) n (n+4) / 6 = 50).
The 0/1 sequence encodes a weighted blow-up: first the n(n-1) ordered pairs (a, b), a != b, in the order
(a, b) for a in range(n), b in range(n) (an edge with two vertices in class min/max as the notebook
encodes: {a, a, b}), then the triples a < b < c. Weights (in [0, 1], normalised) are the class sizes."""
import itertools
import math

import numpy as np

N = 6


def to_scorer(c):
    return [[int(v) for v in np.asarray(c['s']).ravel()], [float(v) for v in np.asarray(c['w'], dtype=float)]]


def _edges(seq):
    E, k = set(), 0
    for a in range(N):
        for b in range(N):
            if a != b:
                if seq[k] > 0.5:
                    E.add(tuple(sorted((a, a, b))))
                k += 1
    for a, b, c in itertools.combinations(range(N), 3):
        if seq[k] > 0.5:
            E.add((a, b, c))
        k += 1
    return E


def _tetrahedron_free(c):
    """No K4^(3) in the blow-up: no 4-multiset of classes (multiplicity <= 2; (a,a,a) is never an edge)
    all of whose 3-sub-multisets are edges."""
    E = _edges([int(v) for v in np.asarray(c['s']).ravel()])
    for quad in itertools.combinations_with_replacement(range(N), 4):
        if max(quad.count(x) for x in quad) > 2:
            continue
        subs = {tuple(sorted(quad[:i] + quad[i + 1:])) for i in range(4)}
        if subs <= E:
            return (False, math.inf)
    return (True, 0.0)


def _positive_mass(c):
    ok = float(np.sum(np.asarray(c['w'], dtype=float))) > 0
    return (ok, 0.0 if ok else math.inf)


predicates = {"tetrahedron_free": _tetrahedron_free, "positive_weight": _positive_mass}
