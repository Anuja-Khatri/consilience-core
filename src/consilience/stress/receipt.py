"""Stress receipts (spec v1.0 §8), the `stress()` API, and verification of a stress receipt.

A receipt is canonical JSON. Non-finite floats are written as {"$float": "nan" | "inf" | "-inf"}
because canonical JSON refuses NaN. Candidates behind every BLOCK are stored as JSON files under
`candidates/` (dtype, shape and exact values; floats written with repr, so they round-trip
exactly). Paths are relative to the receipt's folder. Two runs with the same contract and seed
give byte-identical receipts except for `created` and `environment`.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np

from .. import __version__
from ..hashing import canonical_json, sha256_json
from .checks import BUDGETS, StressResult, run_checks
from .contract import Contract, ContractError, load_contract
from .harness import Harness
from .validity import project_type, violations

SCHEMA = "consilience-stress-receipt/v1"
EXIT_PASS, EXIT_BLOCK, EXIT_ABSTAIN, EXIT_USAGE = 0, 1, 2, 64


def tag(o):
    """Make an object canonical-JSON safe (tagged non-finite floats, numpy scalars to Python)."""
    if isinstance(o, dict):
        return {str(k): tag(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [tag(v) for v in o]
    if isinstance(o, np.generic):
        o = o.item()
    if isinstance(o, complex):
        return {"$complex": [tag(o.real), tag(o.imag)]}
    if isinstance(o, float) and not math.isfinite(o):
        return {"$float": "nan" if math.isnan(o) else ("inf" if o > 0 else "-inf")}
    if isinstance(o, Path):
        return str(o)
    return o


def untag(o):
    if isinstance(o, dict):
        if set(o) == {"$float"}:
            return {"nan": math.nan, "inf": math.inf, "-inf": -math.inf}[o["$float"]]
        if set(o) == {"$complex"}:
            return complex(untag(o["$complex"][0]), untag(o["$complex"][1]))
        return {k: untag(v) for k, v in o.items()}
    if isinstance(o, list):
        return [untag(v) for v in o]
    return o


def encode_candidate(cand: dict) -> dict:
    out = {}
    for k in sorted(cand):
        a = np.asarray(cand[k])
        if np.iscomplexobj(a):
            vals = [[tag(float(z.real)), tag(float(z.imag))] for z in a.ravel()]
        elif a.dtype.kind in "iub":
            vals = [int(v) for v in a.ravel()]
        else:
            vals = [tag(float(v)) for v in a.astype(float).ravel()]
        out[k] = {"dtype": str(a.dtype), "shape": list(a.shape), "values": vals}
    return out


def decode_candidate(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        vals = untag(v["values"])
        if v["dtype"].startswith("complex"):
            arr = np.array([complex(a, b) for a, b in vals], dtype=v["dtype"])
        else:
            arr = np.array(vals, dtype=v["dtype"])
        out[k] = arr.reshape(v["shape"])
    return out


def _environment(result: StressResult) -> dict:
    return {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform(),
            **result.info.get("volatile", {})}


def build_receipt(contract: Contract, result: StressResult, contract_rel: str, out: Optional[Path]) -> dict:
    files = []
    findings = []
    for i, f in enumerate(result.findings):
        d = tag(f.as_dict())
        if f.block and f.candidates:
            refs = {}
            for name, cand in sorted(f.candidates.items()):
                if cand is None:
                    continue
                enc = encode_candidate(cand)
                rel = f"candidates/f{i:02d}_{f.check}_{f.kind}_{name}.json"
                text = canonical_json(enc)
                refs[name] = {"file": rel, "sha256": sha256_json(enc)}
                files.append((rel, text))
            d["candidates"] = refs
        findings.append(d)
    info = {k: v for k, v in result.info.items() if k not in ("volatile", "mean_call_seconds")}
    rec = {
        "receipt": SCHEMA, "consilience_version": __version__,
        "contract_file": contract_rel, "contract": contract.data, "contract_sha256": contract.hash,
        "file_hashes": dict(sorted(contract.file_hashes.items())), "glue_sha256": contract.glue_hash,
        "contract_author": contract.data.get("contract_author", "human"),
        "verdict": result.verdict, "abstain_reasons": result.abstain_reasons,
        "findings": findings, "reported": [tag(f.as_dict()) for f in result.reported],
        "C5": tag(result.c5), "info": tag(info),
        "limits": ["PASS means no counterexample was found within the stated budget; it is not a proof",
                   "C3 is a naive search standing in for an optimiser; 'no drift found' is weak evidence",
                   "not a security sandbox: the scorer's code runs with the caller's permissions",
                   "findings describe the scoring code at the hashed files, nothing else"],
    }
    rec = tag(rec)
    rec["sha256"] = sha256_json(rec)
    rec["created"] = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    rec["environment"] = tag(_environment(result))
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        for rel, text in files:
            p = out / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text + "\n", encoding="utf-8")
        (out / "receipt.json").write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
    return rec


@dataclass
class StressRun:
    result: StressResult
    receipt: dict
    text: str

    @property
    def verdict(self) -> str:
        return self.result.verdict

    @property
    def exit_code(self) -> int:
        return {"PASS": EXIT_PASS, "BLOCK": EXIT_BLOCK, "ABSTAIN": EXIT_ABSTAIN}[self.result.verdict]


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def render(contract: Contract, result: StressResult, budget: str, seed: int) -> str:
    L = []
    info = result.info
    L.append(f"consilience stress: {contract.data['name']}")
    if result.verdict == "PASS":
        L.append(f"PASS: no counterexample found within the '{budget}' budget (seed {seed}). Not a proof.")
    elif result.verdict == "BLOCK":
        L.append(f"BLOCK: {len(result.blocks)} finding(s) with a counterexample you can re-run.")
    else:
        L.append("ABSTAIN: " + "; ".join(f"{a['reason']}" + (f" ({a['detail'][:200]})" if a.get("detail") else "")
                                         for a in result.abstain_reasons))
    if "m" in info:
        L.append(f"margin m = {_fmt(info['m'])} (from {info['margin_source']}); reference score {_fmt(info['reference_score'])}"
                 + (f"; record {contract.data['score']['record']['value']}" if contract.data['score']['record'] else ""))
    for f in result.findings:
        if f.block:
            d = f.data
            extra = ", ".join(f"{k}={_fmt(d[k])}" for k in ("attack", "transform", "deviation", "score", "worst",
                                                             "paired_gain", "score_gain", "slack_claim_units", "raw",
                                                             "orbit_worst", "orbit_best") if k in d)
            rules = ",".join(r["rule"] for r in d.get("rules", []))
            L.append(f"  BLOCK {f.check} {f.kind}" + (f" [{rules}]" if rules else "") + (f": {extra}" if extra else ""))
    if result.c5:
        L.append(f"  C5 claimed record: {result.c5['verdict']}" +
                 (f" (orbit {_fmt(result.c5.get('orbit_worst'))} .. {_fmt(result.c5.get('orbit_best'))}, record "
                  f"{result.c5.get('record')})" if "orbit_worst" in result.c5 else ""))
    kinds = sorted({(f.check, f.kind) for f in result.reported})
    if kinds:
        L.append("  reported (not blocking): " + ", ".join(f"{c}:{k}" for c, k in kinds))
    if "C3" in info:
        c3 = info["C3"]
        L.append(f"  C3 naive search: {c3['restarts']} restarts, {c3['share_invalid']:.0%} ended invalid "
                 f"(best invalid {_fmt(c3['best_invalid'])}, best valid {_fmt(c3['best_valid'])})")
    if contract.data["caller_enforced"]:
        L.append("  assumed (caller-enforced): " + ", ".join(r["rule"] for r in contract.data["caller_enforced"]))
    if contract.data.get("contract_author") == "model":
        L.append("  note: this contract was drafted by a model; read it before trusting a PASS")
    L.append("  limits: naive search; not a security sandbox; findings concern the hashed scoring code only")
    return "\n".join(L)


def stress(contract: Union[str, Path, dict, Contract], *, budget: str = "standard", seed: int = 0,
           out: Union[str, Path, None] = None, only=None, base=None, steps=None) -> StressRun:
    """Run the five checks on the scorer named in `contract`. Writes a receipt if `out` is given.

    `steps` pins the search sizes (see `run_checks`); `steps_from_receipt(path)` reads them from an
    earlier receipt so that a re-run reproduces it on any machine."""
    if budget not in BUDGETS:
        raise ContractError(f"budget must be one of {list(BUDGETS)}")
    c = load_contract(contract, base=base)
    outp = Path(out) if out else None
    with Harness(c) as h:
        res = run_checks(c, h, seed=seed, budget=budget, only=only, steps=steps)
    if isinstance(contract, (str, Path)):
        cp = Path(contract).resolve()
        rel = os.path.relpath(cp, outp.resolve()) if outp else str(cp.name)
    else:
        rel = None
    rec = build_receipt(c, res, rel, outp)
    return StressRun(res, rec, render(c, res, budget, seed))


def steps_from_receipt(path: Union[str, Path]) -> dict:
    """The search sizes an earlier run used: {} if it did not scale them, else {"c3": .., "esc": ..}."""
    rec = json.loads(Path(path).read_text(encoding="utf-8"))
    sb = untag(rec.get("info", {})).get("scaled_budget")
    return {"c3": list(sb["c3"]), "esc": list(sb["esc"])} if sb else {}


# ------------------------------------------------------------------------------------- verify

def verify_stress(rec: dict, receipt_path: Optional[Path], contract_path=None):
    """Re-check every BLOCK's deciding inequality from the receipt (spec §8.3). Returns (ok, steps, note)."""
    steps = []
    body = {k: v for k, v in rec.items() if k not in ("sha256", "created", "environment")}
    integrity = sha256_json(body)
    steps.append(("receipt hash", integrity == rec.get("sha256"),
                  "matches its contents" if integrity == rec.get("sha256") else "the receipt was edited"))
    base = receipt_path.parent if receipt_path else Path(".")
    cfile = contract_path or (base / rec["contract_file"] if rec.get("contract_file") else None)
    if cfile is None or not Path(cfile).is_file():
        return False, steps + [("contract", False, f"contract file not found ({cfile}); pass --contract")], None
    c = load_contract(cfile)
    steps.append(("contract hash", c.hash == rec["contract_sha256"],
                  "same contract" if c.hash == rec["contract_sha256"] else "the contract changed"))
    fh_ok = c.file_hashes == rec["file_hashes"]
    steps.append(("scorer and input files", fh_ok, "same bytes" if fh_ok else
                  f"changed: {sorted(k for k in set(c.file_hashes) | set(rec['file_hashes']) if c.file_hashes.get(k) != rec['file_hashes'].get(k))}"))
    info = untag(rec["info"])
    from .checks import Runner, _Abstain
    try:
        return _verify_findings(rec, c, base, steps, info, Runner)
    except _Abstain as a:
        last = [ln for ln in (a.detail or "").splitlines() if ln.strip()]
        why = f"{a.reason}: {last[-1].strip()}" if last else a.reason
        hint = " (install the scorer's dependencies)" if "ModuleNotFoundError" in (a.detail or "") else ""
        return False, steps + [("scorer", False, f"could not run the scorer: {why}{hint}")], None


def _verify_findings(rec, c, base, steps, info, Runner):
    m = info.get("m", 0.0)
    sign = c.direction_sign
    with Harness(c) as h:
        R = Runner(c, h, seed=0, budget=info.get("budget", "standard"))
        ref = R.complete(dict(np.load(c.path(c.data["reference"]["file"]), allow_pickle=False)))
        sref = R.S(ref)
        if sref is None:
            return False, steps + [("reference", False, "the scorer now rejects the reference")], None
        rec_v = info.get("record_score_units")
        recS = None if rec_v is None else sign * rec_v
        for i, fd in enumerate(untag(rec["findings"])):
            if not fd.get("block"):
                continue
            cands, edited = {}, None
            for name, ref_ in (fd.get("candidates") or {}).items():
                p = base / ref_["file"]
                try:
                    enc = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    edited = f"candidate file {ref_['file']} is missing or unreadable"
                    break
                if sha256_json(enc) != ref_["sha256"]:
                    edited = f"candidate file {ref_['file']} was edited"
                    break
                cands[name] = decode_candidate(enc)
            if edited:
                steps.append((f"finding {i}: {fd['check']} {fd['kind']}", False, edited))
                continue
            ok, detail = _recheck(fd, cands, R, c, sref, recS, m, sign, h)
            steps.append((f"finding {i}: {fd['check']} {fd['kind']}", ok, detail))
    ok = all(s[1] for s in steps)
    return ok, steps, None


def _recheck(fd, cands, R, c, sref, recS, m, sign, h):
    kind = fd["kind"]
    x = cands.get("candidate")
    if kind == "accepts_gross_invalid":
        s = R.S(x)
        v = [vv for vv in violations(c, x) if vv.cls == "gross"]
        good = bool(v) and s is not None and s >= sref
        return good, f"gross violation {[vv.rule for vv in v]}, score {None if s is None else s * sign} vs reference {sref * sign}"
    if kind == "sentinel_is_best":
        s = R.S(x)
        raw = R.last.raw if R.last else None
        good = s is None and isinstance(raw, (int, float)) and raw in h.h["reject"]["values"] and sign * raw > sref
        return good, f"rejected with raw {raw}; better than the reference {sref * sign}"
    if kind in ("exploitable_invalid", "exceeds_bound"):
        s = R.S(x)
        if s is None or not violations(c, x):
            return False, "the candidate is no longer accepted, or no longer invalid"
        worst = s
        wm = cands.get("worst_member")
        if wm is not None:
            sw = R.S(wm)
            if sw is None:
                return False, "the stored worst orbit member is now rejected"
            worst = min(worst, sw / fd.get("worst_factor", 1.0))
        if kind == "exceeds_bound":
            b = sign * float(c.data["score"]["bound"]["value"])
            return worst > b, f"worst {worst * sign} vs bound {b * sign}"
        if fd.get("beats_record"):
            base = sign * fd["valid_base"] if fd.get("valid_base") is not None else -float("inf")
            tgt = max(recS, base) if recS is not None else None
            return tgt is not None and worst > tgt + m, f"worst {worst * sign} vs max(record, valid base) + m {m}"
        base = sign * fd["valid_base"]
        return worst - base > m, f"paired gain {worst - base} vs m {m}"
    if kind == "exploitable_type_violation":
        s = R.S(x)
        sp = R.S(R.complete(project_type(c, x)))
        return s is not None and sp is not None and s > max(sp, sref) + m, f"score {s} vs max(projected {sp}, reference {sref}) + m {m}"
    if kind == "trusts_self_report":
        s = R.S(x)
        return s is not None and s - sref > m, f"gain {None if s is None else s - sref} vs m {m}"
    if kind in ("invariance_broken_integer", "invariance_violated"):
        a, b = R.S(cands["reference"]), R.S(cands["transformed"])
        thr = fd.get("threshold", fd.get("tolerance", 0.0))
        return a is not None and b is not None and abs(a - b) > thr, f"deviation {None if a is None or b is None else abs(a - b)} vs {thr}"
    if kind == "decision_flips_under_invariance":
        rec = c.data["score"]["record"]
        thr = recS + float(rec.get("margin", "0"))
        ge = rec.get("success", ">") == ">="
        ok_ = (lambda v: v >= thr) if ge else (lambda v: v > thr)
        s = R.S(x)
        vals = [s] if s is not None else []
        if cands.get("worst_member") is not None:
            sw = R.S(cands["worst_member"])
            if sw is not None:
                vals.append(sw)
        good = len(vals) >= 1 and any(ok_(v) for v in vals) and any(not ok_(v) for v in vals)
        return good, f"scores {[v * sign for v in vals]} straddle the threshold"
    return False, f"unknown finding kind {kind}"
