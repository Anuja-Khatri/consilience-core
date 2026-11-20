import itertools, math
import numpy as np
from fractions import Fraction as F
def packing(c):
    C = np.asarray(c["circles"], float)
    if C.shape != (21, 3) or not np.isfinite(C).all():
        return (False, math.inf)
    R = [[F(float(v)) for v in row] for row in C]
    worst = F(0)
    for (_, _, r) in R:
        if r < 0:
            worst = max(worst, -r)
    for a, b in itertools.combinations(R, 2):
        d2 = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
        s = a[2] + b[2]
        if s > 0 and d2 < s * s:
            worst = max(worst, s - F(math.sqrt(float(d2))))
    w = max(f[0] + f[2] for f in R) - min(f[0] - f[2] for f in R)
    h = max(f[1] + f[2] for f in R) - min(f[1] - f[2] for f in R)
    if 2 * (w + h) > 4:
        worst = max(worst, (2 * (w + h) - 4) / 4)
    return (worst == 0, float(worst))
predicates = {"packing": packing}


# Record map (spec 6.4): the scorer's combined_score for a construction whose sum_radii equals v.
maps = {"score_from_sum": lambda v: v / 2.3658321334167627}
