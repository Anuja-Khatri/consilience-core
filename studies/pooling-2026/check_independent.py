"""Second-way check (PREREGISTRATION.md): recompute M1, M2 and M3 without the engine.

    python studies/pooling-2026/check_independent.py

A separate implementation with pandas and the standard library. It does NOT import
consilience. It re-implements, from the written rules (docs/packs/bioactivity.md and the
spec), the record rules, the condition classes, the log-scale comparison (bounds and
stated precision included), the consensus and the pooled value. It then compares its
numbers with results/results.json and writes results/independent_check.json. Every
mismatch is printed; none may remain before any number is reported.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
RESULTS = HERE / "results"

FIELDS_EMPTY_EQUAL = ["assay_type", "assay_organism", "assay_category", "assay_tax_id",
                      "assay_strain", "assay_tissue", "assay_cell_type",
                      "assay_subcellular_fraction", "bao_format", "assay_variant_mutation"]
LOG_TOL, LOG_FLOOR, ROUND = 0.3, 1.0, 1e-9
MOLAR_NM = {"nM": 1.0, "uM": 1e3, "µM": 1e3, "μM": 1e3, "mM": 1e6, "M": 1e9, "pM": 1e-3,
            "fM": 1e-6}
R0_NM = {"nm": 1.0, "um": 1e3, "µm": 1e3, "mm": 1e6, "m": 1e9, "pm": 1e-3, "fm": 1e-6}
UNSTATED = ("UNSTATED",)


def norm(s) -> str:
    return " ".join(str(s).split()) if isinstance(s, str) else ""


def cond_value(field, raw):
    s = norm(raw)
    if field == "assay_variant_mutation" and s == "UNDEFINED MUTATION":
        return UNSTATED
    if s.casefold() == "unstated":
        return UNSTATED
    if s == "":
        return ("EMPTY",) if field != "standard_type" else UNSTATED
    try:
        if s[0].isdigit() or s[0] in "+-.":
            return ("num", float(s))
    except ValueError:
        pass
    return ("txt", s)


def half_unit(text: str) -> float:
    """Implied half-unit of the last written digit (0 for no decimal point)."""
    t = text.strip()
    mant, exp = t, 0
    for e in ("e", "E"):
        if e in t:
            mant, ex = t.split(e)
            exp = int(ex)
    if "." not in mant:
        return 0.0
    k = len(mant.split(".")[1])
    return 0.5 * 10 ** (-k) * 10 ** exp


def record_status(r) -> str:
    if not norm(r["parent_molecule_chembl_id"]) or not norm(r["target_chembl_id"]):
        return "excluded:key"
    dvc = norm(r["data_validity_comment"])
    if dvc not in ("", "Manually validated"):
        return "excluded:BR1"
    cs = norm(r["confidence_score"])
    try:
        if cs == "" or float(cs) < 9:
            return "excluded:BR2"
    except ValueError:
        return "excluded:BR2"
    if norm(r["standard_relation"]) not in ("=", "<", "<=", ">", ">="):
        return "excluded:BR3"
    if norm(r["standard_value"]) == "":
        return "excluded:BR4"
    return "ok"


def prepare(df: pd.DataFrame, key_mol: bool):
    recs = []
    for i, r in enumerate(df.to_dict("records"), start=1):
        st = record_status(r)
        rec = {"row": i, "status": st, "raw": r}
        if st == "ok":
            u = norm(r["standard_units"])
            if u not in MOLAR_NM:
                rec["status"] = "other_unit"     # not molar: its own class(es)
                rec["unit_class"] = u or "(none)"
            else:
                rec["unit_class"] = "molar"
                v_own = float(norm(r["standard_value"]))
                if not v_own > 0:
                    rec["status"] = "unparseable"
                else:
                    rec["nM"] = v_own * MOLAR_NM[u]
                    rec["log"] = math.log10(rec["nM"])
                    h = half_unit(norm(r["standard_value"]))
                    rec["implied"] = math.log10(1 + h / v_own) if h else 0.0
                    rel = norm(r["standard_relation"])
                    rec["op"] = None if rel == "=" else rel
            conds = [("standard_type", cond_value("standard_type", r["standard_type"]))]
            conds += [(f, cond_value(f, r.get(f))) for f in FIELDS_EMPTY_EQUAL]
            rec["cond"] = (rec.get("unit_class"),) + tuple(c for _, c in conds)
            rec["stated"] = all(c != UNSTATED for _, c in conds)
            rec["unstated_fields"] = [f for f, c in conds if c == UNSTATED]
        k1 = "molecule_chembl_id" if key_mol else "parent_molecule_chembl_id"
        rec["key"] = (norm(r[k1]), norm(r["target_chembl_id"]))
        recs.append(rec)
    return recs


def sat(d, strict, slack, scale):
    rr = ROUND * scale
    if strict and slack == 0:
        return d < -rr
    return d <= slack + rr


def numeric(a, b):
    implied = a["implied"] + b["implied"]
    x, y = a["log"], b["log"]
    scale = max(abs(x), abs(y), 1.0)
    if a["op"] is None and b["op"] is None:
        d = abs(x - y)
        if d <= LOG_TOL + implied + ROUND * scale:
            return "agree"
        if d <= LOG_FLOOR + implied + ROUND * scale:
            return "within_floor"
        return "disagree"
    if a["op"] and b["op"]:
        up_a = a["op"] in ("<", "<=")
        up_b = b["op"] in ("<", "<=")
        if up_a == up_b:
            return "undecidable_bounds"
        (tu, su), (tl, sl) = ((x, a["op"]), (y, b["op"])) if up_a else ((y, b["op"]), (x, a["op"]))
        d = tl - tu
        strict = su in ("<", ">") or sl in ("<", ">")
        return "undecidable_bounds" if sat(d, strict, max(LOG_TOL, LOG_FLOOR) + implied,
                                           scale) else "disagree"
    val, (t, op) = (x, (y, b["op"])) if b["op"] else (y, (x, a["op"]))
    d = val - t if op in ("<", "<=") else t - val
    strict = op in ("<", ">")
    if sat(d, strict, LOG_TOL + implied, scale):
        return "agree"
    if sat(d, strict, LOG_FLOOR + implied, scale):
        return "within_floor"
    return "disagree"


def classes_of(recs):
    """Per key: class id by first appearance of each condition tuple (input order)."""
    by_key = defaultdict(list)
    for r in recs:
        if r["status"] in ("ok", "other_unit"):
            by_key[r["key"]].append(r)
    out = {}
    for k, ms in by_key.items():
        ids = {}
        for m in ms:
            if m["cond"] not in ids:
                ids[m["cond"]] = len(ids) + 1
            m["cls"] = ids[m["cond"]]
        out[k] = ms
    return out


def m1_m2(df, recs):
    groups = defaultdict(list)
    for r in recs:
        raw = r["raw"]
        u = norm(raw["standard_units"]).lower()
        try:
            ok = norm(raw["standard_value"]) != "" and u in R0_NM and \
                float(norm(raw["standard_value"])) == float(norm(raw["standard_value"]))
        except ValueError:
            ok = False
        if ok and r["key"][0] and r["key"][1]:
            groups[r["key"]].append(r)
    c = Counter()
    for ms in groups.values():
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                a, b = ms[i], ms[j]
                c["r0"] += 1
                if a["status"] not in ("ok", "other_unit") or b["status"] not in ("ok", "other_unit"):
                    c["excl"] += 1
                    continue
                c["paired"] += 1
                if a["cond"] != b["cond"] or not a["stated"]:
                    c["refused"] += 1
                    continue
                v = numeric(a, b)
                c["undecidable" if v == "undecidable_bounds" else "compared"] += 1
    n = sum(1 for r in recs if norm(r["raw"]["standard_value"]) and
            norm(r["raw"]["standard_units"]).lower() in R0_NM and _isnum(r["raw"]["standard_value"]))
    bounds = sum(1 for r in recs if norm(r["raw"]["standard_value"]) and
                 norm(r["raw"]["standard_units"]).lower() in R0_NM and
                 _isnum(r["raw"]["standard_value"]) and
                 norm(r["raw"]["standard_relation"]) not in ("=", ""))
    return {"r0_comparable_pairs": c["r0"], "pairs_paired_by_p": c["paired"],
            "refused": c["refused"], "involves_excluded_or_unparseable": c["excl"],
            "undecidable_bounds": c["undecidable"], "compared_within_class": c["compared"]}, \
        {"r0_values": n, "bounds": bounds}


def _isnum(s) -> bool:
    try:
        float(norm(s))
        return True
    except ValueError:
        return False


def m3(df, recs_mol):
    r1 = defaultdict(list)
    for r in df.to_dict("records"):
        p = norm(r.get("pchembl_value"))
        if p:
            r1[(norm(r.get("canonical_smiles")), norm(r["molecule_chembl_id"]))].append(float(p))
    r1m = {k[1]: sum(v) / len(v) for k, v in r1.items()}
    cls = classes_of(recs_mol)
    best = {}
    for k, ms in cls.items():
        by = defaultdict(list)
        for m in ms:
            by[m["cls"]].append(m)
        cands = []
        for cid, cm in by.items():
            usable = [m for m in cm if m["status"] == "ok" and m["op"] is None]
            if not cm[0]["stated"] or not usable:
                continue
            if cm[0]["unit_class"] != "molar":
                cands.append((len(usable), -cid, None))   # valid? consensus needs numbers
                continue
            verdicts = [numeric(cm[i], cm[j]) for i in range(len(cm)) for j in range(i + 1, len(cm))]
            if len(cm) == 1:
                cons = "single"
            elif "disagree" in verdicts:
                cons = "disagree"
            elif "within_floor" in verdicts:
                cons = "within_floor"
            else:
                cons = "agree"
            if cons == "disagree":
                continue
            v = sorted(m["nM"] for m in usable)
            n = len(v)
            pooled = v[n // 2] if n % 2 else math.sqrt(v[n // 2 - 1] * v[n // 2])
            cands.append((len(usable), -cid, pooled))
        if cands:
            best[k[0]] = max(cands)
    shifts = []
    for mol, r1v in r1m.items():
        b = best.get(mol)
        if b is None or b[2] is None:
            continue
        shifts.append(abs(r1v - (-math.log10(b[2] * 1e-9))))
    n = len(shifts)
    return {"groups_compared": n, "shift_gt_0_3": sum(s > 0.3 for s in shifts),
            "shift_gt_1_0": sum(s > 1.0 for s in shifts),
            "median_shift": float(pd.Series(shifts).median()) if n else None}


def main() -> int:
    res = json.loads((RESULTS / "results.json").read_text(encoding="utf-8"))
    out, mismatches = {}, []
    for t in res["per_target"]:
        tid = t["target"]
        df = pd.read_csv(WORK / "input" / f"{tid}.csv", dtype=str, keep_default_na=False)
        recs = prepare(df, key_mol=False)
        classes_of(recs)
        a1, a2 = m1_m2(df, recs)
        a3 = m3(df, prepare(df, key_mol=True))
        out[tid] = {"M1": a1, "M2": a2, "M3": a3}
        e1 = t["M1"]
        for k in ("r0_comparable_pairs", "pairs_paired_by_p", "refused",
                  "involves_excluded_or_unparseable", "undecidable_bounds",
                  "compared_within_class"):
            if a1[k] != e1[k]:
                mismatches.append(f"{tid} M1 {k}: engine {e1[k]} vs independent {a1[k]}")
        e2 = t["M2"]
        if a2["r0_values"] != e2["r0_values"]:
            mismatches.append(f"{tid} M2 r0_values: {e2['r0_values']} vs {a2['r0_values']}")
        eb = sum(v for k, v in e2["relations"].items() if k not in ("=", "(none)"))
        if a2["bounds"] != eb:
            mismatches.append(f"{tid} M2 bounds: {eb} vs {a2['bounds']}")
        e3 = t["M3"]
        for k in ("groups_compared", "shift_gt_0_3", "shift_gt_1_0"):
            if a3[k] != e3[k]:
                mismatches.append(f"{tid} M3 {k}: engine {e3[k]} vs independent {a3[k]}")
        if (a3["median_shift"] is None) != (e3["median_shift"] is None) or (
                a3["median_shift"] is not None and
                abs(a3["median_shift"] - e3["median_shift"]) > 1e-9):
            mismatches.append(f"{tid} M3 median_shift: {e3['median_shift']} vs "
                              f"{a3['median_shift']}")
        print(f"{tid}: checked", flush=True)
    (RESULTS / "independent_check.json").write_text(
        json.dumps({"independent": out, "mismatches": mismatches}, indent=1) + "\n",
        encoding="utf-8")
    print(f"{len(mismatches)} mismatches")
    for m in mismatches:
        print("  " + m)
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
