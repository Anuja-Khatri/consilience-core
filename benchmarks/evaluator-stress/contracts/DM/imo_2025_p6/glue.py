"""Glue for imo_2025_p6 (n = 9). Row = tile (r, c, h, w): top-left cell (r, c), height h, width w."""
import math

import numpy as np

N = 9


def to_scorer(c):
    return [[tuple(int(v) for v in row) for row in np.asarray(c['T']).reshape(-1, 4)], N]


def _valid_tiling(c):
    grid = [[0] * N for _ in range(N)]
    for row in np.asarray(c['T']).reshape(-1, 4):
        r, cc, h, w = (int(v) for v in row)
        if h <= 0 or w <= 0 or r < 0 or cc < 0 or r + h > N or cc + w > N:
            return (False, math.inf)
        for i in range(r, r + h):
            for j in range(cc, cc + w):
                if grid[i][j]:
                    return (False, math.inf)        # two tiles overlap
                grid[i][j] = 1
    rows_ok = all(sum(grid[i]) == N - 1 for i in range(N))
    cols_ok = all(sum(grid[i][j] for i in range(N)) == N - 1 for j in range(N))
    ok = rows_ok and cols_ok                        # exactly one uncovered square per row and column
    return (ok, 0.0 if ok else math.inf)


predicates = {"valid_tiling": _valid_tiling}
