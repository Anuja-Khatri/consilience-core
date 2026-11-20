"""Run the preregistered study (PREREGISTRATION.md): measures M1-M5 for EGFR and the panel.

    python studies/pooling-2026/run_study.py

Inputs: work/input/<target>.csv (from join.py). Outputs:
- work/out/P/<target>/: the pooling check's records.csv, classes.csv, summary.json and
  receipt.json (pairs.csv kept for EGFR only, to save space; verify re-runs everything);
- results/results.json: every measure, per target, for EGFR, and for the panel;
- results/per_target.csv: the headline numbers per target.

R0 and R1 are re-implemented here from their pinned code (cited at each function). P is
the engine's public API only: consilience.compare_table.
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from consilience import __version__ as ENGINE_VERSION
from consilience.table import compare_table
from consilience.units import as_quantity

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
RESULTS = HERE / "results"
KINASES = {"CHEMBL203", "CHEMBL1862", "CHEMBL4203", "CHEMBL262", "CHEMBL2835", "CHEMBL2971",
           "CHEMBL2147", "CHEMBL4005"}
# EGFR, ABL1, CLK4, GSK3B, JAK1, JAK2, PIM1, PIK3CA (MoleculeACE metadata receptor class
# "Kinase", plus EGFR and PIK3CA, a lipid kinase listed there as "Transferase")
MUTANT_TEXT = re.compile(r"\b(mutant|mutants|mutation|mutations|variant|variants)\b", re.I)

# --- R0: google-deepmind/science-skills @370f8f3, skills/chembl_database/scripts/chembl_api.py
UNIT_CONVERSION_TO_NM = {"nm": 1.0, "um": 1e3, "µm": 1e3, "mm": 1e6, "m": 1e9, "pm": 1e-3,
                         "fm": 1e-6}


def r0_nm(row: dict):
    """_normalize_activity: lower-cased standard_units, float(standard_value) x factor.
    It does not read standard_relation, standard_type or any assay field."""
    units = (row.get("standard_units") or "").strip().lower()
    value = row.get("standard_value")
    if value in (None, "") or units not in UNIT_CONVERSION_TO_NM:
        return None
    try:
        return float(value) * UNIT_CONVERSION_TO_NM[units]
    except (ValueError, TypeError):
        return None


# --- R1: cthoyt/chembl-downloader @14e3aee, src/chembl_downloader/contrib.py,
#     get_target_smi_df(aggregate="mean"): groupby(canonical_smiles, molecule_chembl_id)
#     mean of pchembl_value, over the records the query returns (pchembl_value not null).
def r1_means(rows: list) -> dict:
    acc = defaultdict(list)
    for r in rows:
        p = r.get("pchembl_value")
        if p not in (None, ""):
            acc[(r.get("canonical_smiles") or "", r["molecule_chembl_id"])].append(float(p))
    return {k[1]: sum(v) / len(v) for k, v in acc.items()}


def read_rows(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def share(n, d):
    return None if not d else n / d


# ------------------------------------------------------------------------- M1
def m1(rows: list, res) -> dict:
    """Pairs in the same parent-molecule + target group that R0 treats as comparable."""
    status = {r["row"]: r["record_status"] for r in res.records}
    verdict = {(p["a"], p["b"]): (p["verdict"], p["label"]) for p in res.pairs}
    groups = defaultdict(list)
    for i, r in enumerate(rows, start=1):
        if r.get("parent_molecule_chembl_id") and r.get("target_chembl_id") and \
                r0_nm(r) is not None:
            groups[(r["parent_molecule_chembl_id"], r["target_chembl_id"])].append(i)
    out = Counter()
    by_reason = Counter()
    excluded_by = Counter()
    for members in groups.values():
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                a, b = members[x], members[y]
                out["r0_comparable"] += 1
                v = verdict.get((a, b))
                if v is None:
                    out["involves_excluded_or_unparseable"] += 1
                    s = status[a] if status[a] not in ("usable", "bound") else status[b]
                    excluded_by[s.split(":")[0].replace("excluded(", "").replace(
                        "unparseable(", "unparseable:")] += 1
                    continue
                out["paired_by_p"] += 1
                if v[0] in ("not_comparable", "not_stated"):
                    out["refused"] += 1
                    by_reason[v[1]] += 1
                elif v[0] == "undecidable_bounds":
                    out["undecidable_bounds"] += 1
                else:
                    out["compared"] += 1
                    out[f"compared_{v[0]}"] += 1
    return {"r0_comparable_pairs": out["r0_comparable"],
            "pairs_paired_by_p": out["paired_by_p"],
            "refused": out["refused"],
            "refused_share_of_paired": share(out["refused"], out["paired_by_p"]),
            "refused_or_excluded_share_of_r0_comparable": share(
                out["refused"] + out["involves_excluded_or_unparseable"], out["r0_comparable"]),
            "refused_by_first_reason": dict(by_reason.most_common()),
            "involves_excluded_or_unparseable": out["involves_excluded_or_unparseable"],
            "involves_excluded_by_rule": dict(excluded_by.most_common()),
            "undecidable_bounds": out["undecidable_bounds"],
            "compared_within_class": out["compared"],
            "compared_verdicts": {k: out[f"compared_{k}"] for k in
                                  ("agree", "within_floor", "disagree")}}


# ------------------------------------------------------------------------- M2
def m2(rows: list) -> dict:
    rel = Counter()
    n = 0
    for r in rows:
        if r0_nm(r) is None:
            continue
        n += 1
        s = (r.get("standard_relation") or "").strip()
        rel[s if s else "(none)"] += 1
    bounds = sum(v for k, v in rel.items() if k not in ("=", "(none)"))
    return {"r0_values": n, "relations": dict(rel.most_common()),
            "bound_share": share(bounds, n),
            "no_relation_share": share(rel.get("(none)", 0), n)}


# ------------------------------------------------------------------------- M3
def _class_order(cid: str) -> int:
    return int(cid[1:])


def largest_valid(classes: list) -> dict:
    best = {}
    for c in classes:
        if c["consensus"] not in ("agree", "within_floor", "single") or c["pooled_value"] is None:
            continue
        k = c["key"]
        cur = best.get(k)
        if cur is None or (c["n_usable"], -_class_order(c["class"])) > \
                (cur["n_usable"], -_class_order(cur["class"])):
            best[k] = c
    return best


def m3(rows: list, res_mol) -> dict:
    r1 = r1_means(rows)
    best = largest_valid(res_mol.classes)
    by_mol = {k[0]: c for k, c in best.items()}
    shifts, non_molar = [], 0
    no_valid = Counter()
    cls_by_key = defaultdict(list)
    for c in res_mol.classes:
        cls_by_key[c["key"][0]].append(c["consensus"])
    for mol, r1v in r1.items():
        c = by_mol.get(mol)
        if c is None:
            cons = cls_by_key.get(mol)
            no_valid["no class (all records excluded)" if not cons else
                     "classes: " + "+".join(sorted(set(cons)))] += 1
            continue
        q = as_quantity(f"{c['pooled_value']!r} {c['pooled_unit']}")
        if str(q.dimensionality) != "[substance] / [length] ** 3":
            non_molar += 1
            continue
        p = -math.log10(q.to("molar").magnitude)
        shifts.append(abs(r1v - p))
    n = len(shifts)
    return {"groups_with_r1": len(r1), "groups_compared": n,
            "shift_gt_0_3": sum(1 for s in shifts if s > 0.3),
            "shift_gt_1_0": sum(1 for s in shifts if s > 1.0),
            "share_shift_gt_0_3": share(sum(1 for s in shifts if s > 0.3), n),
            "share_shift_gt_1_0": share(sum(1 for s in shifts if s > 1.0), n),
            "median_shift": statistics.median(shifts) if shifts else None,
            "r1_value_but_no_valid_p_class": dict(no_valid.most_common()),
            "skipped_non_molar_unit": non_molar}


# ------------------------------------------------------------------------- M4
def m4(rows: list, res) -> dict:
    status = {r["row"]: r["record_status"] for r in res.records}
    dup = {i: (r.get("potential_duplicate") or "").strip() == "1"
           for i, r in enumerate(rows, start=1)}
    allp, nodup = Counter(), Counter()
    for p in res.pairs:
        if p["a_class"] != p["b_class"]:
            continue
        if status[p["a"]] != "usable" or status[p["b"]] != "usable":
            continue
        if p["verdict"] not in ("agree", "within_floor", "disagree"):
            continue
        allp[p["verdict"]] += 1
        if not (dup[p["a"]] or dup[p["b"]]):
            nodup[p["verdict"]] += 1

    def pack(c):
        n = sum(c.values())
        return {"pairs": n, **{k: c[k] for k in ("agree", "within_floor", "disagree")},
                **{f"share_{k}": share(c[k], n) for k in ("agree", "within_floor", "disagree")}}
    return {"all_pairs": pack(allp), "without_potential_duplicates": pack(nodup)}


# ------------------------------------------------------------------------- M5
def m5(rows: list, res, target: str) -> dict:
    excl = Counter()
    for r in res.records:
        s = r["record_status"]
        if s.startswith("excluded("):
            excl[s[len("excluded("):].split(":")[0]] += 1
        elif s.startswith("unparseable("):
            excl["unparseable"] += 1
    out = {"records": len(rows), "excluded_by_rule": dict(excl.most_common())}
    f_rows = [r for r in rows if r.get("assay_type") == "F"]
    out["cell_based_F_records"] = len(f_rows)
    out["cell_based_with_cell_type"] = sum(1 for r in f_rows if r.get("assay_cell_type"))
    out["mutant_text_without_variant"] = sum(
        1 for r in rows if MUTANT_TEXT.search(r.get("assay_description") or "")
        and not (r.get("assay_variant_mutation") or "").strip())
    if target in KINASES:
        out["kinase"] = True
        out["atp_in_assay_parameters"] = sum(1 for r in rows if "ATP" in
                                             (r.get("assay_parameters") or ""))
        out["atp_in_description"] = sum(1 for r in rows if "ATP" in
                                        (r.get("assay_description") or ""))
    return out


# ----------------------------------------------------------------------- main
def run_target(t: str) -> dict:
    path = WORK / "input" / f"{t}.csv"
    rows = read_rows(path)
    outdir = WORK / "out" / "P" / t
    P = compare_table(path, map="chembl", pack="bioactivity", out=outdir)
    if t != "CHEMBL203":
        (outdir / "pairs.csv").unlink()   # space: verify re-runs from the input anyway
    Pa = compare_table(path, map="chembl", pack="bioactivity", assume=["ki_ic50_x2"])
    key_mol = ["molecule_chembl_id", "target_chembl_id"]
    Pm = compare_table(path, map="chembl", pack="bioactivity", key=key_mol)
    Pam = compare_table(path, map="chembl", pack="bioactivity", key=key_mol,
                        assume=["ki_ic50_x2"])
    res = {"target": t, "rows": len(rows), "receipt_sha256": P.receipt["sha256"],
           "p_summary": {k: v for k, v in P.summary.items() if k != "text"},
           "M1": m1(rows, P), "M1_assume_ki_ic50_x2": m1(rows, Pa), "M2": m2(rows),
           "M3": m3(rows, Pm), "M3_assume_ki_ic50_x2": m3(rows, Pam), "M4": m4(rows, P),
           "M5": m5(rows, P, t)}
    return res


def combine(results: list, key: str, sub: str = None) -> dict:
    """Panel totals: sums of counts; shares recomputed from the sums."""
    tot = Counter()
    reasons = Counter()
    for r in results:
        m = r[key] if sub is None else r[key][sub]
        for k, v in m.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and \
                    not k.startswith("share") and not k.endswith("_share") and \
                    k != "median_shift" and "share_of" not in k:
                tot[k] += v
            if k in ("refused_by_first_reason",):
                reasons.update(v)
    out = dict(tot)
    if key.startswith("M1"):
        out["refused_share_of_paired"] = share(tot["refused"], tot["pairs_paired_by_p"])
        out["refused_or_excluded_share_of_r0_comparable"] = share(
            tot["refused"] + tot["involves_excluded_or_unparseable"], tot["r0_comparable_pairs"])
        out["refused_by_first_reason"] = dict(reasons.most_common())
    return out


def main(argv) -> int:
    spec = json.loads((HERE / "targets.json").read_text(encoding="utf-8"))
    idx = json.loads((WORK / "INPUT.json").read_text(encoding="utf-8"))
    targets = [t for t in [spec["demonstration"]] + spec["panel"] if t in idx["files"]]
    if argv:
        targets = [t for t in targets if t in argv]
    RESULTS.mkdir(exist_ok=True)
    per = []
    for t in targets:
        r = run_target(t)
        per.append(r)
        m = r["M1"]
        print(f"{t}: rows {r['rows']}, M1 refused {m['refused']}/{m['pairs_paired_by_p']} "
              f"({(m['refused_share_of_paired'] or 0):.1%}), M2 bounds "
              f"{(r['M2']['bound_share'] or 0):.1%}, M3 >1 log "
              f"{(r['M3']['share_shift_gt_1_0'] or 0):.1%}", flush=True)
    panel = [r for r in per if r["target"] != spec["demonstration"]]
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                cwd=HERE).stdout.strip()
    except OSError:
        commit = None
    out = {"engine_version": ENGINE_VERSION, "engine_commit": commit,
           "chembl": {"db_version": idx["chembl_db_version"],
                      "release_date": idx["chembl_release_date"]},
           "missing_targets": idx["missing_targets"],
           "input_files": idx["files"],
           "per_target": per,
           "panel": {k: combine(panel, k) for k in ("M1", "M1_assume_ki_ic50_x2")}}
    # panel M3: pool the shifts' counts
    for k in ("M3", "M3_assume_ki_ic50_x2"):
        n = sum(r[k]["groups_compared"] for r in panel)
        out["panel"][k] = {
            "groups_compared": n,
            "share_shift_gt_0_3": share(sum(r[k]["shift_gt_0_3"] for r in panel), n),
            "share_shift_gt_1_0": share(sum(r[k]["shift_gt_1_0"] for r in panel), n),
            "note": "panel medians are per target (per_target[*].M3.median_shift)"}
    m2n = sum(r["M2"]["r0_values"] for r in panel)
    out["panel"]["M2"] = {"r0_values": m2n, "bound_share": share(sum(
        round((r["M2"]["bound_share"] or 0) * r["M2"]["r0_values"]) for r in panel), m2n)}
    for sub in ("all_pairs", "without_potential_duplicates"):
        tot = Counter()
        for r in panel:
            for k in ("pairs", "agree", "within_floor", "disagree"):
                tot[k] += r["M4"][sub][k]
        out["panel"].setdefault("M4", {})[sub] = dict(
            tot, **{f"share_{k}": share(tot[k], tot["pairs"]) for k in
                    ("agree", "within_floor", "disagree")})
    egfr = next((r for r in per if r["target"] == spec["demonstration"]), None)
    if egfr is not None:
        out["stop_rule"] = {"egfr_M1_refused_share": egfr["M1"]["refused_share_of_paired"],
                            "threshold": 0.02,
                            "passed": (egfr["M1"]["refused_share_of_paired"] or 0) >= 0.02}
    (RESULTS / "results.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    with (RESULTS / "per_target.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["target", "records", "M1_r0_comparable_pairs", "M1_paired_by_p",
                    "M1_refused", "M1_refused_share", "M1_involves_excluded",
                    "M2_r0_values", "M2_bound_share", "M3_groups_compared",
                    "M3_share_shift_gt_0_3", "M3_share_shift_gt_1_0", "M3_median_shift",
                    "M4_pairs", "M4_share_agree", "M4_share_disagree", "pool_valid_records"])
        for r in per:
            w.writerow([r["target"], r["rows"], r["M1"]["r0_comparable_pairs"],
                        r["M1"]["pairs_paired_by_p"], r["M1"]["refused"],
                        r["M1"]["refused_share_of_paired"],
                        r["M1"]["involves_excluded_or_unparseable"], r["M2"]["r0_values"],
                        r["M2"]["bound_share"], r["M3"]["groups_compared"],
                        r["M3"]["share_shift_gt_0_3"], r["M3"]["share_shift_gt_1_0"],
                        r["M3"]["median_shift"], r["M4"]["all_pairs"]["pairs"],
                        r["M4"]["all_pairs"]["share_agree"],
                        r["M4"]["all_pairs"]["share_disagree"],
                        r["p_summary"]["pool_valid_records"]])
    print(json.dumps(out.get("stop_rule"), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
