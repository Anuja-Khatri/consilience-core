"""What a valid answer is, independently of the scorer (spec v1.0 §6.3).

Every rule is evaluated in exact rational arithmetic on the candidate's finite floats (every
binary float converts exactly to a Fraction). Each violation has a magnitude and a class:

    gross  finite, shape, count            (always decisive)
    type   integral, distinct, alphabet    (projectable: a valid equivalent can be computed)
    small  a finite magnitude <= 1e-6 * max(1, largest |value| in the field) beyond tolerance
    large  everything else (structural geometry rules have magnitude inf)
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

import numpy as np

SMALL_REL = 1e-6
GROSS = ("finite", "shape", "count")
TYPE = ("integral", "distinct", "alphabet")


@dataclass(frozen=True)
class Violation:
    index: int                # position of the rule in the contract's validity list (or caller_enforced)
    rule: str
    magnitude: float          # inf for structural rules
    cls: str                  # gross | type | small | large
    detail: str = ""

    def as_dict(self) -> dict:
        m = self.magnitude
        return {"index": self.index, "rule": self.rule, "class": self.cls, "detail": self.detail,
                "magnitude": ("inf" if math.isinf(m) else m)}


def F(x) -> Fraction:
    return Fraction(float(x)) if not isinstance(x, (str, Fraction)) else Fraction(x)


def _arr(v) -> np.ndarray:
    return np.asarray(v)


def _finite(a: np.ndarray) -> bool:
    if a.size == 0:
        return True
    if np.iscomplexobj(a):
        return bool(np.isfinite(a.real).all() and np.isfinite(a.imag).all())
    try:
        return bool(np.isfinite(a.astype(float)).all())
    except (TypeError, ValueError):
        return False


def _scale(a: np.ndarray) -> float:
    try:
        af = np.abs(a.astype(complex) if np.iscomplexobj(a) else a.astype(float))
        return max(1.0, float(np.max(af))) if af.size else 1.0
    except (TypeError, ValueError):
        return 1.0


def _cls_for(rule: str, mag: float, a: Optional[np.ndarray]) -> str:
    if rule in GROSS:
        return "gross"
    if rule in TYPE:
        return "type"
    if math.isfinite(mag) and mag <= SMALL_REL * (_scale(a) if a is not None else 1.0):
        return "small"
    return "large"


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _hull(pts) -> list:
    """Convex hull vertices in counter-clockwise order (Andrew's monotone chain, exact)."""
    s = sorted(set(pts))
    if len(s) < 3:
        return s
    lower, upper = [], []
    for p in s:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(s):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _hull_size(pts) -> int:
    return len(_hull(pts))


def convex_position(P) -> bool:
    """Strict, unordered: every point is a vertex of the convex hull (no repeats, none on an edge)."""
    pts = [(F(x), F(y)) for x, y in P]
    if len(set(pts)) != len(pts):
        return False
    if len(pts) < 3:
        return True
    return _hull_size(pts) == len(pts)


def convex_polygon_ordered(P) -> bool:
    """Strictly convex in the given cyclic order: every point is a hull vertex, and the given order
    is the hull's own cyclic order (up to the starting vertex and the direction). This excludes
    'bow ties' and stars such as a pentagram, whose turns all have the same sign."""
    pts = [(F(x), F(y)) for x, y in P]
    n = len(pts)
    if n < 3 or len(set(pts)) != n:
        return False
    h = _hull(pts)
    if len(h) != n:
        return False
    pos = {p: i for i, p in enumerate(h)}
    idx = [pos[p] for p in pts]
    fwd = all((idx[(i + 1) % n] - idx[i]) % n == 1 for i in range(n))
    bwd = all((idx[i] - idx[(i + 1) % n]) % n == 1 for i in range(n))
    return fwd or bwd


def _collinear_max(P) -> int:
    pts = [tuple(F(v) for v in p) for p in P]
    best = 2 if len(pts) >= 2 else len(pts)
    for i, j in itertools.combinations(range(len(pts)), 2):
        a, b = pts[i], pts[j]
        cnt = sum(1 for c in pts if _cross(a, b, c) == 0)
        best = max(best, cnt)
    return best


def _coplanar_max(P) -> int:
    pts = [tuple(F(v) for v in p) for p in P]
    best = min(3, len(pts))
    for i, j, k in itertools.combinations(range(len(pts)), 3):
        a, b, c = pts[i], pts[j], pts[k]
        u = [b[t] - a[t] for t in range(3)]
        v = [c[t] - a[t] for t in range(3)]
        nrm = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        if nrm == (0, 0, 0):
            continue
        cnt = sum(1 for d in pts if sum(nrm[t] * (d[t] - a[t]) for t in range(3)) == 0)
        best = max(best, cnt)
    return best


def check_rules(rules: list, cand: dict, contract=None, offset: int = 0) -> list:
    """Return the list of Violations of `rules` on candidate `cand` (field name -> array)."""
    out = []
    for idx, r in enumerate(rules):
        k = r["rule"]
        f = r.get("field")
        a = _arr(cand[f]) if f is not None else None
        tol = Fraction(r.get("tolerance", "0"))

        def add(mag, detail=""):
            mag = float(mag)
            out.append(Violation(idx + offset, k, mag, _cls_for(k, mag, a), detail))

        if k == "finite":
            if not _finite(a):
                add(math.inf, "non-finite value")
            continue
        if k == "shape":
            want = list(r["shape"])          # resolved to integers when the contract is loaded
            if list(a.shape) != want:
                add(math.inf, f"shape {list(a.shape)} != {want}")
            continue
        if k == "count":
            n = a.shape[0] if a.ndim else 1
            if ("equals" in r and n != r["equals"]) or ("min" in r and n < r["min"]) or ("max" in r and n > r["max"]):
                add(math.inf, f"count {n}")
            continue
        if k == "graph_simple":
            e = a.astype(float) if a.size else a
            if a.size and (not _finite(a) or not np.all(e == np.round(e))):
                add(math.inf, "non-integer vertex")
                continue
            ed = [tuple(sorted((int(x), int(y)))) for x, y in a.reshape(-1, 2)] if a.size else []
            if any(x == y for x, y in ed) or len(set(ed)) != len(ed):
                add(math.inf, "self-loop or repeated edge")
            continue
        # rules below need finite values; non-finite is the 'finite' rule's business
        if a is not None and not _finite(a):
            continue
        if k == "integral":
            af = a.astype(float)
            if not np.all(af == np.round(af)):
                add(math.inf, "fractional value")
        elif k == "distinct":
            flat = [tuple(row) for row in a.reshape(a.shape[0], -1).tolist()] if a.ndim > 1 else a.tolist()
            if len(set(map(lambda v: v if not isinstance(v, float) else F(v), flat))) != len(flat):
                add(math.inf, "repeated element")
        elif k == "alphabet":
            allowed = {Fraction(v) for v in r["values"]}
            bad = [v for v in a.astype(float).ravel() if F(v) not in allowed]
            if bad:
                add(math.inf, f"{len(bad)} value(s) outside the alphabet")
        elif k == "range":
            lo = Fraction(r["min"]) if "min" in r else None
            hi = Fraction(r["max"]) if "max" in r else None
            worst = Fraction(0)
            for v in a.astype(float).ravel():
                fv = F(v)
                if lo is not None and fv < lo:
                    worst = max(worst, lo - fv)
                if hi is not None and fv > hi:
                    worst = max(worst, fv - hi)
            if worst > tol:
                add(worst, "outside range")
        elif k == "sum":
            ax = r.get("axis")
            target = Fraction(r["equals"])
            sums = [sum(F(v) for v in a.astype(float).ravel())] if ax is None else \
                   [sum(F(v) for v in row) for row in np.moveaxis(a.astype(float), ax, -1).reshape(-1, a.shape[ax])]
            worst = max(abs(s - target) for s in sums) if sums else Fraction(0)
            if worst > tol:
                add(worst, "sum differs")
        elif k == "norm":
            ax = r.get("axis", -1)
            v = Fraction(r["equals"])
            rows = np.moveaxis(a.astype(float), ax, -1).reshape(-1, a.shape[ax])
            worst = 0.0
            for row in rows:
                sq = sum(F(t) * F(t) for t in row)
                lo2 = (v - tol) ** 2 if v > tol else Fraction(0)
                hi2 = (v + tol) ** 2
                if sq < lo2 or sq > hi2:
                    worst = max(worst, abs(math.sqrt(float(sq)) - float(v)))
            if worst > 0:
                add(worst, "norm differs")
        elif k == "in_disk":
            R = Fraction(r["radius"]) + tol
            cx, cy = (Fraction(c) for c in r["center"])
            z = a.astype(complex).ravel()
            worst = 0.0
            for t in z:
                d2 = (F(t.real) - cx) ** 2 + (F(t.imag) - cy) ** 2
                if d2 > R * R:
                    worst = max(worst, math.sqrt(float(d2)) - float(R - tol))
            if worst > 0:
                add(worst, "outside disk")
        elif k == "in_box":
            pts = a.astype(float).reshape(a.shape[0], -1)
            rad = _arr(cand[r["margin_from"]]).astype(float).ravel() if "margin_from" in r else np.zeros(len(pts))
            box = [(Fraction(lo), Fraction(hi)) for lo, hi in r["box"]]
            worst = Fraction(0)
            for p, rr in zip(pts, rad):
                fr = F(rr)
                for d, (lo, hi) in enumerate(box):
                    x = F(p[d])
                    worst = max(worst, (lo + fr) - x, x - (hi - fr))
            if worst > tol:
                add(worst, "outside box")
        elif k == "pairwise_separation":
            pts = a.astype(float).reshape(a.shape[0], -1)
            rad = _arr(cand[r["radii_from"]]).astype(float).ravel() if "radii_from" in r else None
            md = Fraction(r["min_distance"]) if "min_distance" in r else Fraction(0)
            worst = 0.0
            for i, j in itertools.combinations(range(len(pts)), 2):
                need = md + ((F(rad[i]) + F(rad[j])) if rad is not None else 0)
                if need <= 0:
                    continue
                d2 = sum((F(pts[i][t]) - F(pts[j][t])) ** 2 for t in range(pts.shape[1]))
                allowed = need - tol
                if allowed > 0 and d2 < allowed * allowed:
                    worst = max(worst, float(need) - math.sqrt(float(d2)))
            if worst > 0:
                add(worst, "too close")
        elif k == "convex_position":
            if len(a) >= 3 and not convex_position(a.astype(float)):
                add(math.inf, "not in convex position")
        elif k == "convex_polygon_ordered":
            if not convex_polygon_ordered(a.astype(float)):
                add(math.inf, "not a strictly convex polygon in the given order")
        elif k == "no_k_collinear":
            if len(a) >= r["k"] and _collinear_max(a.astype(float)) >= r["k"]:
                add(math.inf, f"{r['k']} or more collinear")
        elif k == "no_k_coplanar":
            if len(a) >= r["k"] and _coplanar_max(a.astype(float)) >= r["k"]:
                add(math.inf, f"{r['k']} or more coplanar")
        elif k == "predicate":
            fn = contract.glue_fn("predicates", r["call"])
            try:
                ok, mag = fn(cand)
                mag = float(mag)
            except Exception as exc:          # a predicate that cannot judge the candidate: not valid
                out.append(Violation(idx + offset, r["name"], math.inf, "large", f"predicate raised {type(exc).__name__}"))
                continue
            if not ok and (mag > float(tol) or math.isinf(mag) or math.isnan(mag)):
                mag = math.inf if math.isnan(mag) else mag
                out.append(Violation(idx + offset, r["name"], mag,
                                     "small" if (math.isfinite(mag) and mag <= SMALL_REL) else "large",
                                     "glue predicate"))
        else:  # pragma: no cover - load_contract rejects unknown rules
            raise ValueError(f"unknown rule {k}")
    return out


def violations(contract, cand: dict) -> list:
    return check_rules(contract.data["validity"], cand, contract)


def caller_violations(contract, cand: dict) -> list:
    return check_rules(contract.data["caller_enforced"], cand, contract, offset=1000)


def project_type(contract, cand: dict) -> dict:
    """The projected valid equivalent for type-class violations: round integral fields,
    snap alphabet fields to the nearest allowed value, de-duplicate distinct fields."""
    y = dict(cand)
    for r in contract.data["validity"]:
        f = r.get("field")
        if r["rule"] == "integral":
            y[f] = np.round(np.asarray(y[f], dtype=float))
        elif r["rule"] == "alphabet":
            allowed = np.array([float(Fraction(v)) for v in r["values"]])
            a = np.asarray(y[f], dtype=float)
            y[f] = allowed[np.argmin(np.abs(a[..., None] - allowed), axis=-1)]
    for r in contract.data["validity"]:
        if r["rule"] == "distinct":
            f = r["field"]
            a = np.asarray(y[f])
            _, idx = np.unique(a, axis=0, return_index=True)
            y[f] = a[np.sort(idx)]
    return y
