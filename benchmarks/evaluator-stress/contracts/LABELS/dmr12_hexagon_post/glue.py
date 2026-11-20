import itertools, math
import numpy as np

def _hex_vertices_mp(mp, cx, cy, s, deg):
    a = mp.radians(mp.mpf(deg))
    return [(mp.mpf(cx) + mp.mpf(s) * mp.cos(a + 2 * mp.pi * i / 6),
             mp.mpf(cy) + mp.mpf(s) * mp.sin(a + 2 * mp.pi * i / 6)) for i in range(6)]

def hexagon_packing(inner, center, side, angle, dps=60):
    """Unit regular hexagons (x, y, angle_deg) with pairwise disjoint interiors, all inside the closed
    regular hexagon (center, side, angle_deg). Evaluated with mpmath at `dps` digits from the exact
    float inputs (trigonometry is not rational, so this is not exact; magnitudes are reported)."""
    import mpmath as mp
    inner = np.asarray(inner, float); center = np.asarray(center, float).ravel()
    side = float(np.asarray(side, float)); angle = float(np.asarray(angle, float))
    if inner.ndim != 2 or inner.shape[1] != 3 or center.shape != (2,):
        return (False, math.inf)
    if not (np.isfinite(inner).all() and np.isfinite(center).all() and math.isfinite(side) and math.isfinite(angle)):
        return (False, math.inf)
    if side <= 0:
        return (False, math.inf)
    with mp.workdps(dps):
        H = [_hex_vertices_mp(mp, x, y, 1, t) for x, y, t in inner]
        O = _hex_vertices_mp(mp, center[0], center[1], side, angle)
        worst = mp.mpf(0)
        def axes(V):
            out = []
            for i in range(6):
                p, q = V[i], V[(i + 1) % 6]
                ex, ey = q[0] - p[0], q[1] - p[1]
                n = mp.sqrt(ex * ex + ey * ey)
                out.append((-ey / n, ex / n))
            return out
        for A, B in itertools.combinations(H, 2):
            pen = None                      # smallest interval overlap over all separating-axis candidates
            for ax in axes(A) + axes(B):
                pa = [v[0] * ax[0] + v[1] * ax[1] for v in A]
                pb = [v[0] * ax[0] + v[1] * ax[1] for v in B]
                ov = min(max(pa) - min(pb), max(pb) - min(pa))
                pen = ov if pen is None else min(pen, ov)
            if pen > 0:                     # interiors overlap on every axis
                worst = max(worst, pen)
        for V in H:
            for v in V:
                for i in range(6):
                    p, q = O[i], O[(i + 1) % 6]
                    ex, ey = q[0] - p[0], q[1] - p[1]
                    cr = (ex * (v[1] - p[1]) - ey * (v[0] - p[0])) / mp.sqrt(ex * ex + ey * ey)
                    if cr < 0:
                        worst = max(worst, -cr)
        return (worst == 0, float(worst))

def packing(c):
    return hexagon_packing(c["inner"], c["center"], c["side"], c["angle"])

def to_scorer(c):
    """verify_construction(inner_hex_data, outer_hex_center, outer_hex_side_length, outer_hex_angle_degrees)."""
    return [np.asarray(c["inner"], float).tolist(), np.asarray(c["center"], float).tolist(),
            float(c["side"]), float(c["angle"])]

def compose(out, c):
    """Cells 89/91: verify_construction raises on failure; the result is the outer side length."""
    return float(c["side"])

predicates = {"packing": packing}
