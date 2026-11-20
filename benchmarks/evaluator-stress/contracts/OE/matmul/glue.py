"""Matrix multiplication tensor decomposition (AlphaEvolve Appendix A), OpenEvolve formulation
(config.yaml, initial_program): an exact rank-R decomposition T[a, b, c] = sum_r U[a, r] V[b, r] W[c, r]
of the <n, m, p> = <2, 4, 5> tensor with T[i*m + j, j*p + k, k*n + i] = 1 (the example's own index
convention), U: (n*m, R), V: (m*p, R), W: (n*p, R). Exact rational arithmetic."""
import math
from fractions import Fraction as F

import numpy as np

N, M, P = 2, 4, 5


def _target():
    T = {}
    for i in range(N):
        for j in range(M):
            for k in range(P):
                T[(i * M + j, j * P + k, k * N + i)] = F(1)
    return T


def _factors(c):
    return [np.asarray(c[k], float) for k in ("U", "V", "W")]


def exact_decomposition(c):
    U, V, W = _factors(c)
    if any(a.ndim != 2 for a in (U, V, W)) or not (U.shape[1] == V.shape[1] == W.shape[1]) or U.shape[1] == 0 \
            or U.shape[0] != N * M or V.shape[0] != M * P or W.shape[0] != N * P \
            or not all(np.isfinite(a).all() for a in (U, V, W)):
        return (False, math.inf)
    acc = {}
    for r in range(U.shape[1]):
        a = [(i, F(float(v))) for i, v in enumerate(U[:, r]) if v != 0]
        b = [(i, F(float(v))) for i, v in enumerate(V[:, r]) if v != 0]
        w = [(i, F(float(v))) for i, v in enumerate(W[:, r]) if v != 0]
        for ia, va in a:
            for ib, vb in b:
                vab = va * vb
                for iw, vw in w:
                    key = (ia, ib, iw)
                    acc[key] = acc.get(key, 0) + vab * vw
    T = _target()
    worst = max((abs(acc.get(k, 0) - T.get(k, 0)) for k in set(acc) | set(T)), default=F(0))
    return (worst == 0, float(worst))


def _dims(c):
    U, V, W = _factors(c)
    nm, mp_, np_ = U.shape[0], V.shape[0], W.shape[0]
    n = math.isqrt(nm * np_ // mp_) if mp_ else 0
    if n == 0 or n * n * mp_ != nm * np_ or nm % n or np_ % n:
        return (math.nan, math.nan, math.nan)
    return (n, nm // n, np_ // n)


def rank_of(c):
    return int(np.asarray(c["U"]).shape[1])


def recon_loss(c):
    """Mean squared reconstruction error over the target tensor (0 for an exact decomposition)."""
    U, V, W = _factors(c)
    T = np.zeros((N * M, M * P, N * P))
    for (a, b, w), v in _target().items():
        T[a, b, w] = float(v)
    return float(np.mean((np.einsum("ir,jr,kr->ijk", U, V, W) - T) ** 2))


quantities = {"n": lambda c: _dims(c)[0], "m": lambda c: _dims(c)[1], "p": lambda c: _dims(c)[2],
              "rank": rank_of, "loss": recon_loss}
predicates = {"exact_decomposition": exact_decomposition}
