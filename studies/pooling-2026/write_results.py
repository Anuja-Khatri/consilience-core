"""Write results/RESULTS.md from results/results.json and results/independent_check.json.

    python studies/pooling-2026/write_results.py

Every number in RESULTS.md comes from those two files; nothing is typed by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"


def pct(x, d=1):
    return "n/a" if x is None else f"{100 * x:.{d}f}%"


def n(x):
    return "n/a" if x is None else f"{x:,}"


def main() -> int:
    res = json.loads((RES / "results.json").read_text(encoding="utf-8"))
    chk = json.loads((RES / "independent_check.json").read_text(encoding="utf-8"))
    from make_figures import NAMES
    per = {r["target"]: r for r in res["per_target"]}
    e = per["CHEMBL203"]
    p = res["panel"]
    p.setdefault("M4", {})
    L = []
    w = L.append
    w("# Results: how pooling choices change potency datasets\n")
    w(f"ChEMBL {res['chembl']['db_version']} ({res['chembl']['release_date']}), engine "
      f"consilience {res['engine_version']} (commit `{(res['engine_commit'] or '')[:12]}`). "
      "Preregistered in [PREREGISTRATION.md](../PREREGISTRATION.md). Every number below is "
      "computed by `run_study.py` and recomputed by an independent implementation "
      f"(`check_independent.py`, no engine import): **{len(chk['mismatches'])} mismatches**.\n")
    if res["missing_targets"]:
        w(f"Targets the API could not serve (reported, not replaced): "
          f"{', '.join(m['target'] for m in res['missing_targets'])}.\n")
    st = res["stop_rule"]
    w(f"Stop rule (M1 on EGFR ≥ 2%): **{'passed' if st['passed'] else 'NOT passed'}** "
      f"({pct(st['egfr_M1_refused_share'])}). As disclosed in the preregistration, EGFR "
      "counts had been looked at before, so this guards against implementation surprises.\n")
    m1 = e["M1"]
    w("## EGFR (CHEMBL203), the example in DeepMind's ChEMBL skill\n")
    w(f"- **Records:** {n(e['rows'])} IC50, Ki, Kd and EC50 records with a value.")
    w(f"- **M1:** unit conversion alone (R0) treats {n(m1['r0_comparable_pairs'])} pairs of "
      "records for the same parent molecule as comparable. Of the "
      f"{n(m1['pairs_paired_by_p'])} pairs where both records pass the record rules, the "
      f"pooling check refuses **{n(m1['refused'])} ({pct(m1['refused_share_of_paired'])})** "
      "because a named assay condition differs or is not stated. Counting also the pairs "
      "where a record is left out by a rule, "
      f"{pct(m1['refused_or_excluded_share_of_r0_comparable'])} of R0's comparable pairs are "
      "refused or excluded.")
    w(f"- **M2:** of the {n(e['M2']['r0_values'])} values R0 converts to nM, "
      f"**{pct(e['M2']['bound_share'])}** are bounds (>, <, >=, <=) that R0 treats as exact "
      f"numbers; {pct(e['M2']['other_relation_share'])} have another relation (such as ~) "
      f"and {pct(e['M2']['no_relation_share'])} have no relation at all.")
    m3 = e["M3"]
    w(f"- **M3:** for {n(m3['groups_compared'])} molecules, the average across measurement "
      "types (R1, chembl-downloader's default) and the pooled value of the largest valid "
      f"class differ by more than 0.3 log units for **{pct(m3['share_shift_gt_0_3'])}** and "
      f"by more than 1 log unit (10-fold) for **{pct(m3['share_shift_gt_1_0'])}**; median "
      f"shift {m3['median_shift']:.2f} log units." if m3["median_shift"] is not None else
      "- **M3:** no molecule had both an R1 value and a valid class.")
    m4 = e["M4"]
    w(f"- **M4 (sanity check):** of {n(m4['all_pairs']['pairs'])} pairs of exact values inside "
      f"a class, {pct(m4['all_pairs']['share_agree'])} agree within 0.3 log units, "
      f"{pct(m4['all_pairs']['share_within_floor'])} only within 1 log unit, "
      f"{pct(m4['all_pairs']['share_disagree'])} disagree. Without pairs flagged as possible "
      f"repeat citations: {pct(m4['without_potential_duplicates']['share_agree'])} / "
      f"{pct(m4['without_potential_duplicates']['share_within_floor'])} / "
      f"{pct(m4['without_potential_duplicates']['share_disagree'])} "
      f"({n(m4['without_potential_duplicates']['pairs'])} pairs).\n")
    w("Refused pairs by first named reason (EGFR):\n")
    w("| Reason | Pairs |\n|---|---:|")
    for k, v in list(m1["refused_by_first_reason"].items())[:10]:
        w(f"| `{k}` | {n(v)} |")
    w("")
    w("![Refused pairs by reason](fig2_egfr_reasons.png)\n")
    w("![Shift in pooled potency](fig3_egfr_shift.png)\n")
    w("## The panel: 29 MoleculeACE targets\n")
    pm1 = p["M1"]
    w(f"- **M1:** {n(pm1.get('r0_comparable_pairs'))} R0-comparable pairs; of "
      f"{n(pm1.get('pairs_paired_by_p'))} pairs of records passing the rules, "
      f"**{n(pm1.get('refused'))} ({pct(pm1.get('refused_share_of_paired'))})** refused.")
    w(f"- **M2:** {pct(p['M2']['bound_share'])} of R0's values are bounds.")
    w(f"- **M3:** {pct(p['M3']['share_shift_gt_0_3'])} of {n(p['M3']['groups_compared'])} "
      f"molecule–target pairs move by more than 0.3 log units, "
      f"{pct(p['M3']['share_shift_gt_1_0'])} by more than 1.")
    w(f"- **M4:** inside classes, {pct(p['M4'].get('all_pairs', {}).get('share_agree'))} agree, "
      f"{pct(p['M4'].get('all_pairs', {}).get('share_disagree'))} disagree "
      f"({n(p['M4'].get('all_pairs', {}).get('pairs'))} pairs).\n")
    w("![Refused by target](fig1_refused_by_target.png)\n")
    w("| Target | Records | M1 refused (of paired) | M2 bounds | M3 >0.3 | M3 >1.0 | "
      "pool_valid records |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for r in res["per_target"]:
        t = r["target"]
        w(f"| {NAMES.get(t, t)} ({t}) | {n(r['rows'])} | "
          f"{n(r['M1']['refused'])} ({pct(r['M1']['refused_share_of_paired'])}) | "
          f"{pct(r['M2']['bound_share'])} | {pct(r['M3']['share_shift_gt_0_3'])} | "
          f"{pct(r['M3']['share_shift_gt_1_0'])} | {n(r['p_summary']['pool_valid_records'])} |")
    w("")
    w("## With the opt-in assumption Ki × 2 = IC50 (`ki_ic50_x2`)\n")
    ea = e["M1_assume_ki_ic50_x2"]
    w(f"EGFR: refused {n(ea['refused'])} of {n(ea['pairs_paired_by_p'])} "
      f"({pct(ea['refused_share_of_paired'])}); panel: "
      f"{pct(p['M1_assume_ki_ic50_x2'].get('refused_share_of_paired'))}. M3 >1 log unit: EGFR "
      f"{pct(e['M3_assume_ki_ic50_x2']['share_shift_gt_1_0'])}, panel "
      f"{pct(p['M3_assume_ki_ic50_x2']['share_shift_gt_1_0'])}.\n")
    w("## M5: what was left out, and what cannot be checked\n")
    w("| Target | Excluded by rule | Cell-based (F) with cell type stated | Mutant text, "
      "no variant | ATP in assay parameters / description (kinases) |")
    w("|---|---|---:|---:|---:|")
    for r in res["per_target"]:
        m5 = r["M5"]
        ex = ", ".join(f"{k} {v:,}" for k, v in m5["excluded_by_rule"].items())
        atp = (f"{n(m5['atp_in_assay_parameters'])} / {n(m5['atp_in_description'])}"
               if m5.get("kinase") else "")
        f_ = (f"{n(m5['cell_based_with_cell_type'])} of {n(m5['cell_based_F_records'])}")
        w(f"| {r['target']} | {ex} | {f_} | {n(m5['mutant_text_without_variant'])} | {atp} |")
    w("")
    w("## What these numbers do and do not say\n")
    w("- R0 and R1 do what they document: R0 converts units, R1 averages pChEMBL. The "
      "numbers measure what an agent or a dataset builder would pool by following them "
      "without further curation; they are not errors in those tools.")
    w("- The conditions are those Landrum & Riniker (2024) match before combining assays; "
      "the 0.3 and 1.0 log-unit thresholds are those they report against, not a published "
      "agreement criterion.")
    w("- ATP or substrate concentration is not checked; repeat citations are kept (M4 shows "
      "their effect); the variant field follows ChEMBL's curation, which does not always "
      "distinguish variants.")
    w("- A refused pair is not a wrong value: it is a pair that should not be averaged "
      "without a stated assumption.")
    (RES / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("results/RESULTS.md written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
