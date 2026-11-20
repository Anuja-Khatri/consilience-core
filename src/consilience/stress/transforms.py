"""Declared invariances (spec v1.0 §6.4): transformations that must not change the TRUE score.

Each `apply` returns (transformed candidate, factor). The transformed score is divided by
factor ** score_exponent for `scale` (factors are 2**k, exact in floating point); 1 otherwise.
Rotations and dihedral symmetries act about `center` (default: the origin).
"""

from __future__ import annotations

import math

import numpy as np

from .contract import INT_TYPES


def _rand_rotation(d: int, rng) -> np.ndarray:
    if d == 2:
        th = rng.uniform(0.0, 2.0 * math.pi)
        return np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    q, r = np.linalg.qr(rng.normal(size=(d, d)))
    q = q @ np.diag(np.sign(np.diag(r)))
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]
    return q


def _rand_orthogonal(d: int, rng) -> np.ndarray:
    q, r = np.linalg.qr(rng.normal(size=(d, d)))
    return q @ np.diag(np.sign(np.diag(r)))


def apply(t: dict, cand: dict, rng, field_type: str):
    x = {k: np.array(v, copy=True) for k, v in cand.items()}
    f = t["field"]
    a = x[f]
    T = t["transform"]
    fac = 1.0
    center = np.array([float(c) for c in t.get("center", [])]) if t.get("center") else None
    if T == "permute":
        x[f] = a[rng.permutation(a.shape[0])]
    elif T == "cyclic_shift":
        if a.shape[0] > 1:
            x[f] = np.roll(a, int(rng.integers(1, a.shape[0])), axis=0)
    elif T == "translate":
        if field_type in INT_TYPES:
            x[f] = a + int(rng.integers(-50, 51))
        else:
            d = a.shape[-1] if a.ndim >= 2 else 1
            x[f] = a + rng.normal(size=d) if a.ndim >= 2 else a + float(rng.normal())
    elif T == "rotate":
        d = t.get("dims", 2)
        R = _rand_rotation(d, rng)
        c = center if center is not None else np.zeros(d)
        x[f] = (a - c) @ R.T + c
    elif T == "dihedral":
        order = t.get("order", 4)
        k = int(rng.integers(0, order))
        th = 2.0 * math.pi * k / order
        R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
        if order == 4:                         # exact quarter turns
            R = np.round(R)
        if rng.random() < 0.5:
            R = R @ np.array([[-1.0, 0.0], [0.0, 1.0]])
        c = center if center is not None else np.zeros(2)
        x[f] = (a - c) @ R.T + c
    elif T == "reflect":
        c = center if center is not None else np.zeros(a.shape[-1])
        flip = np.ones(a.shape[-1])
        flip[0] = -1.0
        x[f] = (a - c) * flip + c
    elif T == "negate":
        x[f] = -a
    elif T == "conjugate":
        d = a.shape[-1]
        Q = _rand_orthogonal(d, rng)
        x[f] = np.array([Q @ m @ Q.T for m in a]) if a.ndim == 3 else Q @ a @ Q.T
    elif T == "scale":
        s = 2.0 ** int(rng.choice([-3, -2, -1, 1, 2, 3]))
        x[f] = a * s
        fac = s ** t["score_exponent"]
    elif T == "relabel":
        if a.size:
            n = int(a.max()) + 1
            perm = rng.permutation(n)
            x[f] = perm[a.astype(int)]
    else:  # pragma: no cover - rejected at load time
        raise ValueError(f"unknown transform {T}")
    return x, fac
