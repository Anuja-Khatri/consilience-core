"""The independent second way (spec v1.0 §10.4). Imports NOTHING from `consilience`.

    python -I benchmarks/evaluator-stress/check_independent.py

For every BLOCK in results/receipts/**/receipt.json it:
  1. re-scores each stored candidate with the vendored scorer in a FRESH process, using its own minimal
     calling code (not the engine's harness),
  2. re-checks the broken rule with its own exact arithmetic (fractions),
  3. re-checks the deciding inequality with its own code.
Writes results/independent_check.json and prints agree/disagree per finding. Any disagreement voids that
finding until it is resolved and logged in VERIFICATION_LOG.md.
The contract's glue file (the contract author's code, independent of scorer and engine) is used for
conversion (to_scorer/compose), quantities and predicates.
"""
from __future__ import annotations

import itertools
import json
import math
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

# ------------------------------------------------------------------ candidates

def untag(o):
    if isinstance(o, dict):
        if set(o) == {"$float"}:
            return {"nan": math.nan, "inf": math.inf, "-inf": -math.inf}[o["$float"]]
        return {k: untag(v) for k, v in o.items()}
    if isinstance(o, list):
        return [untag(v) for v in o]
    return o


def decode(d):
    out = {}
    for k, v in d.items():
        vals = untag(v["values"])
        if v["dtype"].startswith("complex"):
            a = np.array([complex(x, y) for x, y in vals], dtype=v["dtype"])
        else:
            a = np.array(vals, dtype=v["dtype"])
        out[k] = a.reshape(v["shape"])
    return out


# ------------------------------------------------------------------ scoring in a fresh process

SCORE_SCRIPT = r'''
import importlib.util, json, math, os, sys, uuid
import numpy as np
cfg = json.loads(sys.argv[1])
def load(p, n):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
os.chdir(os.path.dirname(cfg["evaluator"])); sys.path.insert(0, os.path.dirname(cfg["evaluator"]))
d = np.load(cfg["npz"]); cand = {k: d[k] for k in d.files}
glue = load(cfg["glue"], "g_" + uuid.uuid4().hex[:6]) if cfg.get("glue") else None
def prog_text():
    ret = []
    for name, typ in cfg["returns"]:
        ret.append(f"float(_d[{name!r}])" if typ == "real" else f"int(_d[{name!r}])" if typ == "int" else f"_d[{name!r}]")
    expr = ret[0] if len(ret) == 1 else "(" + ", ".join(ret) + ")"
    body = f"def {cfg['program_function']}(*a, **k):\n    import numpy as _np\n    _d = _np.load({cfg['npz']!r})\n    return {expr}\n"
    if cfg["kind"] == "template":
        t = open(cfg["program_template"]).read(); i, j = t.find(cfg["block_start"]), t.find(cfg["block_end"])
        return t[: i + len(cfg["block_start"])] + "\n" + body + t[j:]
    return body
out = {"ok": True}
try:
    if cfg["kind"] == "cli_json":
        raise SystemExit("cli_json is handled by the parent")
    ev = load(cfg["evaluator"], "ev_" + uuid.uuid4().hex[:6])
    entry = getattr(ev, cfg["entry"])
    if cfg["kind"] == "function":
        args = glue.to_scorer(cand) if (glue is not None and hasattr(glue, "to_scorer")) else \
            [float(cand[n]) if t == "real" else int(cand[n]) if t == "int" else cand[n] for n, t in cfg["returns"]]
        r = entry(*args, **cfg.get("call_args", {}))
    else:
        p = os.path.join(cfg["tmp"], "p_" + uuid.uuid4().hex[:10] + ".py"); open(p, "w").write(prog_text())
        r = entry({"content": {"files": [{"path": os.path.basename(p), "content": prog_text()}]}}) if cfg["kind"] == "sdk_dict" else entry(p)
    if glue is not None and hasattr(glue, "compose"):
        r = glue.compose(r, cand)
    out["raw"] = r if isinstance(r, (int, float, dict)) and not isinstance(r, bool) else repr(r)
except BaseException as e:
    out = {"ok": False, "exc": type(e).__name__}
def js(o):
    if isinstance(o, dict): return {str(k): js(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [js(v) for v in o]
    if isinstance(o, np.generic): o = o.item()
    if isinstance(o, float) and not math.isfinite(o): return {"$float": "nan" if math.isnan(o) else ("inf" if o > 0 else "-inf")}
    if isinstance(o, np.ndarray): return "ndarray"
    return o
print("@@RESULT@@" + json.dumps(js(out)))
'''


def get_path(o, key):
    if key is None:
        return o
    cur = o
    for part in key.split("."):
        if "[" in part and part.endswith("]"):
            name, sel = part[:-1].split("[", 1)
            k, v = sel.split("=", 1)
            lst = cur.get(name) if isinstance(cur, dict) else None
            cur = next((it for it in (lst or []) if isinstance(it, dict) and str(it.get(k)) == v), None)
        else:
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def score(contract: dict, cdir: Path, cand: dict):
    """Return (score or None, raw) using our own calling code in a fresh process."""
    h = contract["harness"]
    fields = {f["name"]: f["type"] for f in contract["fields"]}
    returns = [(n, fields[n]) for n in contract.get("returns") or [f["name"] for f in contract["fields"]]]
    tmp = Path(tempfile.mkdtemp(prefix="indep_"))
    npz = tmp / "c.npz"
    np.savez(npz, **{k: np.asarray(v) for k, v in cand.items()})
    ev = str((cdir / h["evaluator"]).resolve())
    rej = h.get("reject") or {}
    if h["kind"] == "cli_json":
        cfg = {"kind": "py_path", "program_function": h["program_function"], "returns": returns, "npz": str(npz),
               "block_start": "", "block_end": ""}
        ret = [f"float(_d[{n!r}])" if t == "real" else f"int(_d[{n!r}])" if t == "int" else f"_d[{n!r}]" for n, t in returns]
        expr = ret[0] if len(ret) == 1 else "(" + ", ".join(ret) + ")"
        prog = tmp / "prog.py"
        prog.write_text(f"def {h['program_function']}(*a, **k):\n    import numpy as _np\n    _d = _np.load({str(npz)!r})\n    return {expr}\n")
        outdir = tmp / "out"
        outdir.mkdir()
        argv = [a.replace("{evaluator}", ev).replace("{program}", str(prog)).replace("{outdir}", str(outdir))
                .replace("{python}", sys.executable) for a in h["argv"]]
        try:
            subprocess.run(argv, cwd=str(Path(ev).parent), capture_output=True, timeout=float(h.get("timeout_s", 30)) * 3)
        except subprocess.TimeoutExpired:
            return None, "timeout"
        rf = rej.get("file")
        if rf:
            rp = Path(rf["path"].replace("{outdir}", str(outdir)))
            if rp.is_file() and get_path(json.loads(rp.read_text()), rf["key"]) == rf["equals"]:
                return None, "reject_file"
        try:
            raw = json.loads(Path(h["result_file"].replace("{outdir}", str(outdir))).read_text())
        except Exception:
            return None, "no result file"
    else:
        cfg = {"kind": h["kind"], "evaluator": ev, "entry": h.get("entry"), "program_function": h.get("program_function"),
               "returns": returns, "npz": str(npz), "tmp": str(tmp), "call_args": h.get("call_args") or {},
               "glue": str((cdir / contract["glue"]).resolve()) if contract.get("glue") else None}
        if h["kind"] == "template":
            cfg.update(program_template=str((cdir / h["program_template"]).resolve()), block_start=h["block_start"],
                       block_end=h["block_end"])
        p = subprocess.run([sys.executable, "-I", "-c", SCORE_SCRIPT, json.dumps(cfg)], capture_output=True, text=True,
                           timeout=float(h.get("timeout_s", 30)) * 3 + 60)
        line = next((l for l in p.stdout.splitlines()[::-1] if l.startswith("@@RESULT@@")), None)
        if line is None:
            return None, "no answer: " + p.stderr[-300:]
        res = untag(json.loads(line[len("@@RESULT@@"):]))
        if not res.get("ok"):
            return None, {"exception": res.get("exc")}
        raw = res["raw"]
    if isinstance(raw, dict) and any(k in raw for k in rej.get("keys_present") or []):
        return None, raw
    v = get_path(raw, h.get("score_key")) if isinstance(raw, dict) else raw
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        return None, v
    if float(v) in [float(x) for x in rej.get("values") or []]:
        return None, float(v)
    return float(v), raw


# ------------------------------------------------------------------ exact rule checks (own code)

def F(x):
    return Fraction(float(x))


def hull(pts):
    s = sorted(set(pts))
    if len(s) < 3:
        return s
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in s:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(s):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def broken(rule: dict, cand: dict, glue) -> bool:
    """True if `rule` is violated (beyond its tolerance), by our own exact code."""
    k = rule["rule"]
    a = np.asarray(cand[rule["field"]]) if rule.get("field") else None
    tol = Fraction(str(rule.get("tolerance", "0")))
    finite = a is None or a.size == 0 or bool(np.all(np.isfinite(a.astype(complex) if np.iscomplexobj(a) else a.astype(float))))
    if k == "finite":
        return not finite
    if k == "shape":
        return list(a.shape) != list(rule["shape"])
    if k == "count":
        n = a.shape[0] if a.ndim else 1
        return ("equals" in rule and n != rule["equals"]) or ("min" in rule and n < rule["min"]) or ("max" in rule and n > rule["max"])
    if not finite:
        return False
    if k == "integral":
        return any(F(v).denominator != 1 for v in a.astype(float).ravel())
    if k == "distinct":
        flat = [tuple(F(x) for x in np.atleast_1d(r)) for r in a.reshape(a.shape[0], -1)] if a.ndim > 1 else [F(x) for x in a]
        return len(set(flat)) != len(flat)
    if k == "alphabet":
        allowed = {Fraction(str(v)) for v in rule["values"]}
        return any(F(v) not in allowed for v in a.astype(float).ravel())
    if k == "range":
        lo = Fraction(str(rule["min"])) if "min" in rule else None
        hi = Fraction(str(rule["max"])) if "max" in rule else None
        return any((lo is not None and F(v) < lo - tol) or (hi is not None and F(v) > hi + tol) for v in a.astype(float).ravel())
    if k in ("convex_position", "convex_polygon_ordered"):
        pts = [(F(x), F(y)) for x, y in a.astype(float)]
        if len(set(pts)) != len(pts):
            return True
        h = hull(pts)
        if len(h) != len(pts):
            return True
        if k == "convex_position":
            return False
        pos = {p: i for i, p in enumerate(h)}
        idx = [pos[p] for p in pts]
        n = len(idx)
        fwd = all((idx[(i + 1) % n] - idx[i]) % n == 1 for i in range(n))
        bwd = all((idx[i] - idx[(i + 1) % n]) % n == 1 for i in range(n))
        return not (fwd or bwd)
    if k == "predicate":
        try:
            ok, mag = getattr(glue, "predicates")[rule["call"]](cand)
        except Exception:
            return True
        return (not ok) and (float(mag) > float(tol) or not math.isfinite(float(mag)))
    # rules not re-implemented here (norm, sum, in_disk, in_box, pairwise_separation, collinear, coplanar, graph):
    return None


def load_glue(path: Path):
    if not path:
        return None
    import importlib.util
    s = importlib.util.spec_from_file_location("glue_indep", str(path))
    m = importlib.util.module_from_spec(s)
    sys.path.insert(0, str(path.parent))
    s.loader.exec_module(m)
    sys.path.remove(str(path.parent))
    return m


# ------------------------------------------------------------------ deciding inequalities (own code)

def judge(fd, cands, contract, cdir, glue, info):
    sign = 1.0 if contract["score"]["direction"] == "maximize" else -1.0
    ref = dict(np.load(cdir / contract["reference"]["file"]))
    ref = complete(ref, contract, glue)
    sref, _ = score(contract, cdir, ref)
    if sref is None:
        return False, "reference rejected on re-score"
    sref *= sign
    m = float(info.get("m", 0.0))
    kind = fd["kind"]
    x = cands.get("candidate")
    rules = contract.get("validity") or []

    def any_broken(c, idx=None):
        rs = [rules[i] for i in idx] if idx is not None else rules
        res = [broken(r, c, glue) for r in rs]
        return any(r is True for r in res), any(r is None for r in res)

    if kind in ("accepts_gross_invalid", "exploitable_invalid", "exceeds_bound", "exploitable_type_violation", "sentinel_is_best"):
        idx = [r["index"] for r in fd.get("rules", []) if isinstance(r.get("index"), int) and r["index"] < 1000]
        b, unknown = any_broken(x, idx)
        if not b and not unknown:
            return False, "our own rule check finds the candidate VALID"
    if kind == "sentinel_is_best":
        s, raw = score(contract, cdir, x)
        return s is None and isinstance(raw, (int, float)) and sign * float(raw) > sref, f"raw {raw} vs reference {sref * sign}"
    if kind == "accepts_gross_invalid":
        s, _ = score(contract, cdir, x)
        return s is not None and sign * s >= sref, f"score {s} vs reference {sref * sign}"
    if kind in ("exploitable_invalid", "exceeds_bound"):
        s, _ = score(contract, cdir, x)
        if s is None:
            return False, "candidate rejected on re-score"
        worst = sign * s
        if cands.get("worst_member") is not None:
            sw, _ = score(contract, cdir, cands["worst_member"])
            if sw is None:
                return False, "worst member rejected on re-score"
            worst = min(worst, sign * sw / float(fd.get("worst_factor", 1.0)))
        if kind == "exceeds_bound":
            b = sign * float(contract["score"]["bound"]["value"])
            return worst > b, f"worst {worst * sign} vs bound {b * sign}"
        if fd.get("beats_record"):
            rec = sign * float(info["record_score_units"])
            return worst > rec + m, f"worst {worst * sign} vs record {rec * sign} + m {m}"
        base = sign * float(fd["valid_base"])
        return worst - base > m, f"paired gain {worst - base} vs m {m}"
    if kind == "trusts_self_report":
        s, _ = score(contract, cdir, x)
        return s is not None and sign * s - sref > m, f"gain {None if s is None else sign * s - sref} vs m {m}"
    if kind in ("invariance_broken_integer", "invariance_violated"):
        a, _ = score(contract, cdir, cands["reference"])
        b, _ = score(contract, cdir, cands["transformed"])
        thr = float(fd.get("threshold", fd.get("tolerance", 0.0)))
        return a is not None and b is not None and abs(a - b) > thr, f"|{a} - {b}| vs {thr}"
    if kind == "decision_flips_under_invariance":
        rec = contract["score"]["record"]
        thr = sign * float(info["record_score_units"]) + float(rec.get("margin", "0"))
        ge = rec.get("success", ">") == ">="
        ok_ = (lambda v: v >= thr) if ge else (lambda v: v > thr)
        vals = []
        for nm in ("candidate", "worst_member"):
            if cands.get(nm) is not None:
                s, _ = score(contract, cdir, cands[nm])
                if s is not None:
                    vals.append(sign * s)
        return any(ok_(v) for v in vals) and any(not ok_(v) for v in vals), f"scores {vals} vs threshold {thr}"
    if kind == "exploitable_type_violation":
        return None, "not re-implemented independently (projection); checked by verify only"
    return None, f"kind {kind} not re-implemented"


def complete(c, contract, glue):
    for f in contract["fields"]:
        if f["role"] == "fixed":
            c[f["name"]] = np.asarray(f["value"])
        elif f["role"] == "derived" and f["from"].startswith("len("):
            c[f["name"]] = np.asarray(len(c[f["from"][4:-1].strip()]))
    for f in contract["fields"]:
        if f["role"] == "claimed":
            try:
                c[f["name"]] = np.asarray(float(glue.quantities[f["quantity"]](c)))
            except Exception:
                c[f["name"]] = np.asarray(math.nan)
    return c


def main():
    global RESULTS
    if len(sys.argv) > 2 and sys.argv[1] == "--results":
        RESULTS = Path(sys.argv[2]).resolve()
    out = []
    for rp in sorted((RESULTS / "receipts").glob("*/*/receipt.json")):
        rec = json.loads(rp.read_text())
        blocks = [f for f in rec.get("findings", []) if f.get("block")]
        if not blocks:
            continue
        cfile = (rp.parent / rec["contract_file"]).resolve()
        contract = yaml.safe_load(cfile.read_text())
        cdir = cfile.parent
        glue = load_glue(cdir / contract["glue"]) if contract.get("glue") else None
        info = untag(rec["info"])
        for i, fd in enumerate(untag(blocks)):
            cands = {n: decode(json.loads((rp.parent / r["file"]).read_text())) for n, r in (fd.get("candidates") or {}).items()}
            try:
                agree, why = judge(fd, cands, yaml.safe_load(cfile.read_text()), cdir, glue, info)
            except Exception as exc:
                agree, why = False, f"independent check crashed: {type(exc).__name__}: {exc}"
            key = f"{rp.parent.parent.name}/{rp.parent.name}"
            out.append({"key": key, "finding": i, "check": fd["check"], "kind": fd["kind"],
                        "agree": agree, "detail": why})
            print(f"{'AGREE   ' if agree else ('N/A     ' if agree is None else 'DISAGREE')} {key} #{i} {fd['check']} {fd['kind']}: {why}")
    (RESULTS / "independent_check.json").write_text(json.dumps(out, indent=1) + "\n")
    n_dis = sum(1 for o in out if o["agree"] is False)
    n_na = sum(1 for o in out if o["agree"] is None)
    print(f"{len(out)} findings checked; {n_dis} disagree; {n_na} not independently re-implemented")
    return 1 if n_dis else 0


if __name__ == "__main__":
    sys.exit(main())
