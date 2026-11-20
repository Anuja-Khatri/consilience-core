"""The five checks and their decision rules (spec v1.0 §7). Deterministic given the seed.

Terms (§7.0): scores are direction-normalised (larger is better). Sub-orbits are made per declared
invariance; the worst case of a candidate is the minimum over itself and its sub-orbits (skipping
transforms flagged by C4). m = max(r, sigma_ref, 1e-9 * max(1, |target|)). Invalid candidates found
by search are judged against a valid twin search with the same budget (paired gain).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .contract import INT_TYPES, record_resolution, parse_derived
from .harness import Harness, Outcome
from .transforms import apply
from .validity import caller_violations, project_type, violations

BUDGETS = {
    "small": {"esc": (1, 300), "c3": (4, 400), "k": 40, "cap": 120.0},
    "standard": {"esc": (3, 500), "c3": (8, 800), "k": 100, "cap": 600.0},
    "large": {"esc": (6, 1000), "c3": (32, 2000), "k": 400, "cap": 3600.0},
}
DEFAULT_MATERIALITY = 1e-9
INT_INVARIANCE_REL = 1e-9
SUSPECT_REL = 1e-9
SLOW_CALL_SECONDS = 0.05      # above this mean call cost, C3 and escalation are scaled to fit the cap


class _Abstain(Exception):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(reason)
        self.reason, self.detail = reason, detail


@dataclass
class Finding:
    check: str
    kind: str
    block: bool
    data: dict = field(default_factory=dict)
    candidates: dict = field(default_factory=dict)     # name -> candidate dict (kept for BLOCKs)

    def as_dict(self) -> dict:
        return {"check": self.check, "kind": self.kind, "block": self.block, **self.data}


@dataclass
class StressResult:
    verdict: str
    findings: list
    reported: list
    abstain_reasons: list
    c5: Optional[dict]
    info: dict

    @property
    def blocks(self):
        return [f for f in self.findings if f.block]


class Runner:
    """Holds the state of one run: contract, harness, seed, budget, counters."""

    def __init__(self, contract, harness: Harness, seed: int, budget: str, only=None):
        self.c = contract
        self.h = harness
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.budget_name = budget
        self.B = dict(BUDGETS[budget])
        self.only = set(only) if only else None
        self.sign = contract.direction_sign
        self.types = {n: f["type"] for n, f in contract.fields.items()}
        self.invs = contract.data["invariances"]
        self.nondeterministic = False
        self.repeats = contract.data["noise"]["probe_repeats"]
        self.timeouts = 0
        self.last: Optional[Outcome] = None
        self.check_started = 0.0
        self.exhausted: list = []
        self.flagged: set = set()
        self.current = ""

    # ------------------------------------------------------------ candidates
    def complete(self, cand: dict) -> dict:
        """Fill fixed, derived and claimed fields. Claimed fields get the recomputed true value."""
        x = {k: np.asarray(v) for k, v in cand.items()}
        for f in self.c.data["fields"]:
            n, role = f["name"], f["role"]
            if role == "fixed":
                x[n] = np.asarray(f["value"])
            elif role == "derived":
                frm = f["from"]
                if frm.startswith("glue:"):
                    x[n] = np.asarray(self.c.glue_fn(None, frm[5:])(x))
                else:
                    p = parse_derived(frm, "derived")
                    a = np.asarray(x[p[1]])
                    x[n] = np.asarray(len(a) if p[0] == "len" else a.shape[p[2]])
        for f in self.c.claimed:
            x[f["name"]] = np.asarray(self.true_claim(f, x))
        return x

    def true_claim(self, f: dict, x: dict) -> float:
        try:
            with np.errstate(all="ignore"):
                v = float(self.c.glue_fn("quantities", f["quantity"])(x))
        except Exception:
            v = math.nan
        return v

    # ------------------------------------------------------------ scoring
    def _call(self, x: dict) -> Outcome:
        o = self.h.score(x)
        if o.harness_error:
            raise _Abstain("harness_failed", o.harness_error + "\n" + self.h.stderr_tail())
        if o.timeout:
            self.timeouts += 1
        return o

    def S(self, x: dict) -> Optional[float]:
        """Direction-normalised score, or None if rejected / timed out. Candidates that break a
        caller-enforced rule are never sent (spec §6.3)."""
        if self.c.data["caller_enforced"] and caller_violations(self.c, x):
            self.last = Outcome(rejected=True, raw="caller_enforced")
            return None
        if not self.nondeterministic:
            o = self._call(x)
            self.last = o
            return None if o.score is None else self.sign * o.score
        vals = []
        for _ in range(self.repeats):
            o = self._call(x)
            self.last = o
            if o.score is None:
                return None
            vals.append(o.score)
        return self.sign * float(np.median(vals))

    def over_cap(self) -> bool:
        return time.time() - self.check_started > self.B["cap"]

    # ------------------------------------------------------------ orbits
    def suborbits(self, x: dict, k: int, valid_only: bool, skip=()) -> dict:
        res = {}
        if not self.invs:
            return res
        per = max(1, k // len(self.invs))
        for t in self.invs:
            name = f"{t['transform']}:{t['field']}"
            if name in skip:
                continue
            vals = []
            for _ in range(per):
                y, fac = apply(t, x, self.rng, self.types[t["field"]])
                y = self.complete(y)
                if valid_only and violations(self.c, y):
                    continue
                s = self.S(y)
                if s is not None:
                    vals.append((s / fac, y, fac))
            res[name] = vals
        return res

    def worst_best(self, x: dict, s: float, k: Optional[int] = None):
        """(worst, best, worst_member, worst_factor) over x and its sub-orbits (flagged skipped)."""
        o = self.suborbits(x, (k or self.B["k"]) // 2, valid_only=not violations(self.c, x), skip=self.flagged)
        worst, best, wm, wf = s, s, None, 1.0
        for vals in o.values():
            for v, y, fac in vals:
                if v < worst:
                    worst, wm, wf = v, y, fac
                best = max(best, v)
        return worst, best, wm, wf

    # ------------------------------------------------------------ search
    def search(self, x0: dict, steps: int, keep=None, project: bool = False):
        x = self.complete({k: np.array(v, copy=True) for k, v in x0.items()})
        s = self.S(x)
        s = -math.inf if s is None else s
        step, stall = 0.1, 0
        scales = {}
        for f in self.c.construction:
            a = np.asarray(x0[f])
            try:
                af = a.astype(float)
                scales[f] = float(np.std(af)) if af.size and np.isfinite(af).all() else 1.0
            except (TypeError, ValueError):
                scales[f] = 1.0
            scales[f] = scales[f] or 1.0
        proj = self.c.glue_fn(None, "project") if (project and self.c.glue is not None
                                                   and callable(getattr(self.c.glue, "project", None))) else None
        for _ in range(steps):
            if self.over_cap():
                self.exhausted.append(self.current)
                break
            y = dict(x)
            for f in self.c.construction:
                a = np.asarray(x[f])
                if self.types[f] in INT_TYPES:
                    y[f] = a + (self.rng.random(a.shape) < 0.2) * self.rng.integers(-1, 2, size=a.shape)
                elif np.iscomplexobj(a):
                    msk = self.rng.random(a.shape) < 0.3
                    y[f] = a + (self.rng.normal(size=a.shape) + 1j * self.rng.normal(size=a.shape)) * step * scales[f] * msk
                else:
                    y[f] = a + self.rng.normal(size=a.shape) * step * scales[f] * (self.rng.random(a.shape) < 0.3)
            if proj is not None:
                y = proj(y)
            y = self.complete(y)
            if keep is not None and not keep(y):
                continue
            sy = self.S(y)
            if sy is not None and sy >= s:
                x, s, stall = y, sy, 0
            else:
                stall += 1
                if stall > 100:
                    step *= 0.5
                    stall = 0
        return x, (None if s == -math.inf else s)


def run_checks(contract, harness: Harness, seed: int = 0, budget: str = "standard", only=None,
               steps=None) -> StressResult:
    """`steps` pins the search sizes instead of scaling them by measured call time:
    None scales (spec 7.1); {} disables scaling; {"c3": [r, s], "esc": [n, s]} uses those sizes.
    Pinning to a receipt's recorded sizes makes a re-run reproduce that receipt exactly."""
    with np.errstate(all="ignore"):
        return _run_checks(contract, harness, seed, budget, only, steps)


def _run_checks(contract, harness: Harness, seed: int, budget: str, only, steps=None) -> StressResult:
    R = Runner(contract, harness, seed, budget, only)
    c = contract
    t_start = time.time()
    findings: list = []
    reported: list = []
    info: dict = {"budget": budget, "seed": seed, "budget_params": dict(R.B)}
    want = lambda ch: R.only is None or ch in R.only

    try:
        # ---------------- reference
        ref = R.complete(dict(np.load(c.path(c.data["reference"]["file"]), allow_pickle=False)))
        for f in c.construction:
            if not any(r.get("field") == f for r in c.data["validity"]):
                raise _Abstain("no_validity_rules", f)
        if violations(c, ref):
            raise _Abstain("reference_invalid", "; ".join(v.rule for v in violations(c, ref)))
        R.check_started = time.time()
        R.current = "reference"
        probes = []
        for _ in range(R.repeats):
            o = R._call(ref)
            if o.timeout:
                raise _Abstain("timeout", "the reference timed out")
            if o.score is None:
                raise _Abstain("reference_rejected", repr(o.raw)[:300])
            probes.append(o.score)
        if len(set(probes)) > 1:
            R.nondeterministic = True
        sref = R.sign * float(np.median(probes))
        info["deterministic"] = not R.nondeterministic
        info["mean_call_seconds"] = harness.mean_call_seconds

        # ---------------- record, resolution, bound
        rec = c.data["score"]["record"]
        recS, r_res = None, 0.0
        if rec is not None:
            v = float(rec["value"])
            r0 = record_resolution(rec["value"])
            if rec.get("map"):
                mp = c.glue_fn("maps", rec["map"])
                v_s = float(mp(v))
                r_res = abs(float(mp(v + r0)) - float(mp(v - r0))) / 2.0 if r0 > 0 else 0.0
                v = v_s
            else:
                r_res = r0
            recS = R.sign * v
        bnd = c.data["score"]["bound"]
        boundS = None if bnd is None else R.sign * float(bnd["value"])

        # ---------------- C4 part 1: reference sub-orbits, integer invariance, sigma_ref
        R.check_started = time.time()
        R.current = "C4"
        so = R.suborbits(ref, R.B["k"], valid_only=True)
        for t in c.data["invariances"]:
            name = f"{t['transform']}:{t['field']}"
            vals = [v for v, _, _ in so.get(name, [])]
            if not vals:
                continue
            devs = [abs(v - sref) for v in vals]
            dev = max(devs)
            if R.types[t["field"]] in INT_TYPES:
                thr = max(INT_INVARIANCE_REL * max(1.0, abs(sref)), r_res)
                if dev > thr and want("C4"):
                    i = int(np.argmax(devs))
                    _, y, fac = so[name][i]
                    findings.append(Finding("C4", "invariance_broken_integer", True,
                                            {"transform": name, "deviation": dev, "threshold": thr},
                                            {"reference": ref, "transformed": y}))
                    R.flagged.add(name)
            elif t.get("invariance_tolerance") is not None:
                tol = float(t["invariance_tolerance"])
                if dev > tol and want("C4"):
                    i = int(np.argmax(devs))
                    findings.append(Finding("C4", "invariance_violated", True,
                                            {"transform": name, "deviation": dev, "tolerance": tol},
                                            {"reference": ref, "transformed": so[name][i][1]}))
                    R.flagged.add(name)
            elif dev > SUSPECT_REL * max(1.0, abs(sref)):
                reported.append(Finding("C4", "invariance_suspect", False,
                                        {"transform": name, "max_deviation": dev,
                                         "deviations": sorted(float(d) for d in devs)[-5:]}))
        sig = [max(abs(v - sref) for v, _, _ in vals) for name, vals in so.items() if vals and name not in R.flagged]
        sigma_ref = max(sig) if sig else 0.0
        target = sref if recS is None else max(sref, recS)
        m = max(r_res, sigma_ref, DEFAULT_MATERIALITY * max(1.0, abs(target)))
        msrc = ("record_resolution" if (m == r_res and r_res > 0) else
                "reference_floor" if (m == sigma_ref and sigma_ref > 0) else "default_1e-9_relative")
        info.update(reference_score=sref * R.sign, record_score_units=None if recS is None else recS * R.sign,
                    resolution=r_res, sigma_ref=sigma_ref, m=m, margin_source=msrc,
                    flagged_transforms=sorted(R.flagged))

        # scale the search budgets for slow scorers (spec §7.1)
        mc = harness.mean_call_seconds
        if steps is not None:
            if steps:
                R.B["c3"], R.B["esc"] = tuple(steps["c3"]), tuple(steps["esc"])
                info["scaled_budget"] = {"c3": list(R.B["c3"]), "esc": list(R.B["esc"])}
        elif mc > SLOW_CALL_SECONDS:
            fit = max(10, int(R.B["cap"] / (mc * 3)))
            n_r, n_s = R.B["c3"]
            if n_r * n_s > fit:
                R.B["c3"] = (max(2, min(n_r, fit // 50 or 1)), max(25, fit // max(2, min(n_r, fit // 50 or 1))))
            ne, se = R.B["esc"]
            R.B["esc"] = (ne, max(25, min(se, fit // max(1, ne))))
            info["scaled_budget"] = {"c3": list(R.B["c3"]), "esc": list(R.B["esc"])}

        has_equality = any((r["rule"] in ("sum", "norm")) or r.get("equality") for r in c.data["validity"])
        has_project = c.glue is not None and callable(getattr(c.glue, "project", None))
        twin: dict = {}

        def valid_twin():
            if "v" not in twin:
                if has_equality and not has_project:
                    twin["v"] = None
                else:
                    steps = R.B["c3"][0] * R.B["c3"][1] // 2
                    _, sb = R.search(ref, steps, keep=lambda y: not violations(c, y), project=True)
                    twin["v"] = sref if sb is None else max(sref, sb)
                info["valid_twin_base"] = None if twin["v"] is None else twin["v"] * R.sign
            return twin["v"]

        def judge(x: dict, s: Optional[float], base: float, where: str) -> Optional[Finding]:
            v = violations(c, x)
            if not v:
                return None
            rules = [vv.as_dict() for vv in v]
            classes = {vv.cls for vv in v}
            if s is None:
                o = R.last
                raw = o.raw if o is not None else None
                rv = raw if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None
                if rv is not None and rv in harness.h["reject"]["values"] and R.sign * rv > sref:
                    return Finding(where, "sentinel_is_best", True, {"rules": rules, "raw": rv}, {"candidate": x})
                if o is not None and isinstance(raw, float) and math.isnan(raw):
                    return Finding(where, "nan_score", False, {"rules": rules})
                return None
            if boundS is not None and s > boundS:
                lo, hi, wm, wf = R.worst_best(x, s)
                if lo > boundS:
                    return Finding(where, "exceeds_bound", True, {"rules": rules, "worst": lo * R.sign,
                                   "bound": bnd["value"]}, {"candidate": x, **({"worst_member": wm} if wm is not None else {})})
            if "gross" in classes:
                if s >= sref:
                    return Finding(where, "accepts_gross_invalid", True, {"rules": rules, "score": s * R.sign,
                                   "reference_score": sref * R.sign}, {"candidate": x})
                return Finding(where, "accepts_invalid_low_score", False, {"rules": rules, "score": s * R.sign})
            if classes == {"type"}:
                sp = R.S(R.complete(project_type(c, x)))
                # v1.1: the invalid candidate must beat BOTH its projected valid equivalent and the reference
                if sp is not None and s > max(sp, sref) + m:
                    return Finding(where, "exploitable_type_violation", True, {"rules": rules, "score": s * R.sign,
                                   "projected_score": sp * R.sign}, {"candidate": x})
                return Finding(where, "type_violation_harmless", False, {"rules": rules})
            lo, hi, wm, wf = R.worst_best(x, s)
            if where in ("C3", "C1-escalation"):
                tw = valid_twin()
                if tw is None:
                    # v1.1: "beats the record" means beats the better of the record and the valid base
                    beats = recS is not None and lo > max(recS, base) + m
                    if beats:
                        return Finding(where, "exploitable_invalid", True, {"rules": rules, "worst": lo * R.sign,
                                       "beats_record": True, "valid_base": None},
                                       {"candidate": x, **({"worst_member": wm} if wm is not None else {})})
                    return Finding(where, "unpaired_gain", False, {"rules": rules, "score": s * R.sign,
                                   "note": "equality rule without a projection: no valid base"})
                base = max(base, tw)
            paired = lo - base
            # v1.1: "beats the record" means beats the better of the record and the valid base (no zero-gain BLOCKs)
            beats = recS is not None and lo > max(recS, base) + m
            data = {"rules": rules, "worst": lo * R.sign, "paired_gain": paired, "valid_base": base * R.sign,
                    "beats_record": bool(beats), "worst_factor": wf}
            cands = {"candidate": x, **({"worst_member": wm} if wm is not None else {})}
            if classes <= {"small"}:
                if beats:
                    return Finding(where, "exploitable_invalid", True, data, cands)
                if paired > 0:
                    return Finding(where, "tolerance_headroom", False, data)
                return Finding(where, "accepts_invalid_low_score", False, {"rules": rules})
            if beats or paired > m:
                return Finding(where, "exploitable_invalid", True, data, cands)
            return Finding(where, "accepts_invalid_low_score", False, {"rules": rules})

        # ---------------- C1
        attacks = {}
        if want("C1"):
            R.check_started = time.time()
            R.current = "C1"
            c1 = []
            for f in c.construction:
                a = np.asarray(ref[f])
                isint = R.types[f] in INT_TYPES
                try:
                    af = a.astype(complex) if np.iscomplexobj(a) else a.astype(float)
                except (TypeError, ValueError):
                    continue
                spread = float(np.ptp(np.abs(af))) if af.size else 1.0
                atk = []
                if af.ndim == 0:
                    pos = [()]
                elif af.ndim >= 2:
                    pos = [(0,) * (af.ndim - 1) + (j,) for j in range(af.shape[-1])] if af.shape[0] else []
                elif af.size:
                    pos = sorted({(0,), (af.shape[0] // 2,), (af.shape[0] - 1,)})
                else:
                    pos = []
                for val in (np.nan, np.inf, -np.inf):
                    for p in pos:
                        y = af.astype(float).copy() if not np.iscomplexobj(af) else af.copy()
                        y[p] = val
                        atk.append((f"nonfinite{list(p)}={val}", y))
                if af.ndim >= 1 and af.size:
                    step = 1.0 if isint else 1e-3 * (spread or 1.0)
                    atk.append(("count+1", np.concatenate([af, af[-1:] + step])))
                    atk.append(("count-1", af[:-1]))
                if af.ndim >= 1:
                    atk.append(("empty", af[:0]))
                atk += [(f"magnitude*{g:g}", af * g) for g in (1e150, 1e300)]
                if not isint:
                    atk += [(f"scale*(1{sg * d:+g})", af * (1 + sg * d)) for d in (1e-9, 1e-6, 1e-4, 1e-3, 1e-2) for sg in (1, -1)]
                for r in c.data["validity"]:
                    if r.get("field") != f or not af.size:
                        continue
                    if r["rule"] == "range":
                        for d in (1e-12, 1e-9, 1e-6, 1e-3, 1e-1, 1.0):
                            y = af.astype(float).copy()
                            i = int(R.rng.integers(y.size))
                            if "min" in r:
                                b = float(r["min"]); y.flat[i] = b - d * max(1.0, abs(b))
                            else:
                                b = float(r["max"]); y.flat[i] = b + d * max(1.0, abs(b))
                            atk.append((f"range-{d:g}", y))
                    elif r["rule"] == "integral":
                        y = af.astype(float).copy(); y.flat[-1] += 0.5
                        atk.append(("fractional", y))
                    elif r["rule"] == "distinct" and len(af) > 1:
                        y = af.copy(); y[-1] = y[0]
                        atk.append(("duplicate", y))
                    elif r["rule"] == "alphabet":
                        allowed = [float(v) for v in r["values"]]
                        y = af.astype(float).copy(); y.flat[-1] = (max(allowed) + min(allowed)) / 2.0 + 0.5
                        atk.append(("outside_alphabet", y))
                for name, y in atk:
                    if R.over_cap():
                        R.exhausted.append("C1")
                        break
                    x = dict(ref)
                    x[f] = y
                    x = R.complete(x)
                    attacks[(f, name)] = x
                    variants = [(name, x)]
                    for q in c.claimed:
                        xl = dict(x)
                        xl[q["name"]] = np.asarray(ref[q["name"]])
                        variants.append((name + "+lie", xl))
                    for nm, xv in variants:
                        fd = judge(xv, R.S(xv), sref, "C1")
                        if fd is not None:
                            fd.data["attack"] = f"{f}:{nm}"
                            c1.append(fd)
            # escalation
            esc_src = [fd for fd in c1 if not fd.block and fd.kind in ("accepts_invalid_low_score", "tolerance_headroom")]
            seen = set()
            for fd in esc_src:
                if len(seen) >= R.B["esc"][0] or R.over_cap():
                    break
                f, nm = fd.data["attack"].split(":", 1)
                nm = nm[:-4] if nm.endswith("+lie") else nm
                if (f, nm) in seen or (f, nm) not in attacks:
                    continue
                seen.add((f, nm))
                R.current = "C1-escalation"
                xb, sb = R.search(attacks[(f, nm)], R.B["esc"][1], keep=lambda y: bool(violations(c, y)))
                jj = judge(xb, sb, sref, "C1-escalation")
                if jj is not None:
                    jj.data["escalated_from"] = f"{f}:{nm}"
                    c1.append(jj)
            findings += [fd for fd in c1 if fd.block]
            reported += [fd for fd in c1 if not fd.block]

        # ---------------- C2
        if want("C2"):
            R.check_started = time.time()
            R.current = "C2"
            for q in c.claimed:
                t = float(np.asarray(ref[q["name"]]))
                isint = q["type"] == "int"
                best_g, slack, best_x = 0.0, 0.0, None
                probes = [t + d for d in (1, -1, 2, -2)] if isint else \
                    [t + sg * (10.0 ** e) * max(1.0, abs(t)) for e in range(-12, 0) for sg in (1, -1)]
                for pv in probes:
                    xv = dict(ref)
                    xv[q["name"]] = np.asarray(pv)
                    s = R.S(xv)
                    if s is not None and s > sref:
                        slack = max(slack, abs(pv - t))
                        if s - sref > best_g:
                            best_g, best_x = s - sref, xv
                if not isint:                        # bisection refines the REPORTED slack only
                    for sg in (1, -1):
                        lo, hi = 0.0, 0.2 * max(1.0, abs(t))
                        for _ in range(50):
                            mid = (lo + hi) / 2.0
                            xv = dict(ref)
                            xv[q["name"]] = np.asarray(t + sg * mid)
                            s = R.S(xv)
                            if s is not None and s > sref:
                                lo = mid
                            else:
                                hi = mid
                        if lo > 0:
                            slack = max(slack, lo)
                            xv = dict(ref)
                            xv[q["name"]] = np.asarray(t + sg * lo)
                            s = R.S(xv)
                            if s is not None and s - sref > best_g:
                                best_g, best_x = s - sref, xv
                data = {"field": q["name"], "score_gain": best_g, "slack_claim_units": slack, "m": m,
                        "true_value": t}
                if best_g > m:
                    findings.append(Finding("C2", "trusts_self_report", True, data, {"candidate": best_x}))
                elif slack > 0:
                    reported.append(Finding("C2", "self_report_headroom", False, data))

        # ---------------- C3
        c3_valid = []
        if want("C3"):
            R.check_started = time.time()
            R.current = "C3"
            ends = []
            starts = [ref]
            if c.data.get("initial"):
                starts.append(R.complete(dict(np.load(c.path(c.data["initial"]["file"]), allow_pickle=False))))
            while len(starts) < R.B["c3"][0]:
                x0 = dict(ref)
                for f in c.construction:
                    a = np.asarray(ref[f])
                    if R.types[f] in INT_TYPES:
                        x0[f] = np.round(a + R.rng.normal(size=a.shape) * 2).astype(np.int64)
                    else:
                        af = a.astype(float)
                        x0[f] = af + R.rng.normal(size=af.shape) * (float(np.std(af)) + 1e-3) * 0.3
                starts.append(x0)
            for x0 in starts[: R.B["c3"][0]]:
                if R.over_cap():
                    R.exhausted.append("C3")
                    break
                ends.append(R.search(x0, R.B["c3"][1]))
            inv = [(x, s) for x, s in ends if s is not None and violations(c, x)]
            c3_valid = [(x, s) for x, s in ends if s is not None and not violations(c, x)]
            best_val = max([s for _, s in c3_valid], default=None)
            base = sref if best_val is None else max(sref, best_val)
            for x, s in sorted(inv, key=lambda e: -e[1]):
                fd = judge(x, s, base, "C3")
                if fd is not None and fd.block:
                    fd.data["share_invalid"] = len(inv) / max(1, len(ends))
                    findings.append(fd)
                    break
                if fd is not None and fd.kind in ("unpaired_gain", "tolerance_headroom"):
                    reported.append(fd)
                    break
            info["C3"] = {"restarts": len(ends), "share_invalid": round(len(inv) / max(1, len(ends)), 4),
                          "best_invalid": None if not inv else max(s for _, s in inv) * R.sign,
                          "best_valid": None if best_val is None else best_val * R.sign,
                          "limitation": "naive search; 'no drift found' is weak evidence"}

        # ---------------- C4 part 2: threshold flips on tool-generated valid candidates
        if want("C4") and rec is not None and rec["kind"] == "threshold":
            R.check_started = time.time()
            R.current = "C4"
            thr = recS + R.sign * 0.0
            mg = float(rec.get("margin", "0"))
            ge = rec.get("success", ">") == ">="

            def success(v):
                return v >= thr + mg if ge else v > thr + mg

            for x, s in [(ref, sref)] + c3_valid:
                lo, hi, wm, _ = R.worst_best(x, s)
                if success(hi) and not success(lo):
                    findings.append(Finding("C4", "decision_flips_under_invariance", True,
                                            {"orbit_worst": lo * R.sign, "orbit_best": hi * R.sign,
                                             "fix": "add a decision margin larger than the observed spread"},
                                            {"candidate": x, **({"worst_member": wm} if wm is not None else {})}))
                    break

        # ---------------- C5
        c5 = None
        if c.data.get("claimed_best") and rec is not None and want("C5"):
            R.check_started = time.time()
            R.current = "C5"
            cb = R.complete(dict(np.load(c.path(c.data["claimed_best"]["file"]), allow_pickle=False)))
            s = R.S(cb)
            if s is None:
                c5 = {"verdict": "claim_rejected_by_scorer"}
            else:
                lo, hi, _, _ = R.worst_best(cb, s)
                if rec["kind"] == "threshold":
                    mg = float(rec.get("margin", "0"))
                    ge = rec.get("success", ">") == ">="
                    ok = (lambda v: v >= recS + mg) if ge else (lambda v: v > recS + mg)
                    v = "beats_threshold" if ok(lo) else ("claim_within_rounding" if ok(hi) else "below_threshold")
                else:
                    v = ("beats_record" if lo > recS + r_res else
                         "below_record" if hi < recS - r_res else "within_resolution")
                c5 = {"verdict": v, "claimed_score": s * R.sign, "orbit_worst": lo * R.sign,
                      "orbit_best": hi * R.sign, "record": rec["value"], "resolution": r_res}
                if boundS is not None and lo > boundS:
                    c5["exceeds_bound"] = True

    except _Abstain as ab:
        info.update(calls=harness.calls, timeouts=R.timeouts)
        info["volatile"] = {"seconds": round(time.time() - t_start, 3), "mean_call_seconds": harness.mean_call_seconds}
        return StressResult("ABSTAIN", findings, reported, [{"reason": ab.reason, "detail": ab.detail[:2000]}], None, info)

    abstain = []
    if R.exhausted and not any(f.block for f in findings):
        abstain.append({"reason": "budget_exhausted", "detail": ",".join(sorted(set(R.exhausted)))})
    if R.timeouts:
        reported.append(Finding("harness", "timeouts", False, {"count": R.timeouts}))
    verdict = "BLOCK" if any(f.block for f in findings) else ("ABSTAIN" if abstain else "PASS")
    info.update(calls=harness.calls, timeouts=R.timeouts, budget_exhausted=sorted(set(R.exhausted)))
    info["volatile"] = {"seconds": round(time.time() - t_start, 3), "mean_call_seconds": harness.mean_call_seconds}
    return StressResult(verdict, findings, reported, abstain, c5, info)
