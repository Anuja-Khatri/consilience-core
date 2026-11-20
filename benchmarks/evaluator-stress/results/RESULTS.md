# Evaluator-stress benchmark: results (run 3, 45 contracts, 20 Nov 2026)

**Setup:**
- **Preregistration:** `../PREREGISTRATION.md`, committed at 6049a69 before any run.
- **Deviations:** `../VERIFICATION_LOG.md`. In short: the run was capped at 45 contracts by a seeded rule; there were engine robustness fixes; decision rules v1.1 apply.
- **Run:** budget `standard`, seed 0; engine as of commit 34350aa.
- **Raw results:** `results.json`, `per_evaluator.csv` and `receipts/`.
- **Independent check:** `independent_check.json`.

Every statement below concerns **the published code at the commit named in `../SOURCES.yaml`**. Nothing is claimed about any team's internal systems or published results.

## 1. Limits first

- **Only 45 of the 111 runnable contracts were run.** The 21 unlabelled contracts are a seeded random sample (`../SELECTION_45.txt`), and the M3 numbers below are on that sample.
- **The run shows where the checks are weak:**
  - in the random sample, the checks for self-reports (C2) and for invariance (C4) found **nothing**;
  - the naive search (C3) needed the `large` budget for the one case it is known to catch (equidistant points, §4).
- **Two decision-rule flaws** were found in run 2 and fixed before this run (v1.1). The independent check could not have caught them, because it recomputes the same inequality. A human review of the findings did.
- **Engine robustness bugs** (scalar fields, empty arrays, mismatched paired fields, float overflow) crashed 11 contracts in runs 1–2. They were fixed with tests; run 3 had no crash.
- **Budget:** 20 of the 45 contracts had slow scorers, so their search budget was scaled down; 3 ABSTAINed with `budget_exhausted`.

## 2. Measures against the forecast written before the run

| Measure | Forecast | Run 3 | |
|---|---|---|---|
| **M1 recall** (13 labelled known bugs) | 0.7–0.9 | **11/13 = 0.85** as preregistered. 10/13 = 0.77 if the DM-15 hit (not specific to the labelled bug) is not counted | Missed: OpenEvolve #514 matmul (self-reported rank and dimensions) and DeepMind results #11 (negative radii) |
| **M2(a)** findings not confirmed independently | 0 | **0 of 76** | |
| **M2(b)** a fixed version still BLOCKed for its fixed bug | 0 | **1 (DM-15)** | The PR #17 version is still not translation-invariant: the scorer adds 0 to the set. A real defect, not the labelled sort bug |
| **M3** new findings, 21-contract random sample | — | **3 of 21** | 2 in the easy invalid-input class |
| — C2 self-report (sample) | 2–5 over about 90 | **0** | Below forecast |
| — C4 invariance (sample) | 0–2 over about 90 | **0** | |
| **M5 reach** | 60–80% | 89 unlabelled + 22 labelled contracts; about 86% of in-scope functions; median 10 minutes each; 1 scorer unrunnable as published | |
| **M6 runtime** | seconds to minutes | median 16 s, max 714 s per contract | |

## 3. What the checks reliably catch (labelled known bugs, confirmed independently)

- **Non-finite input accepted:**
  - DeepMind problems #16, all four verifiers;
  - OpenEvolve #548 (circle packing in a rectangle);
  - OpenEvolve #549 (first autocorrelation);
  - DeepMind results #12 (hexagon packing).
- **Self-reported values trusted:**
  - OpenEvolve #514 (function minimisation);
  - OpenEvolve #562 (Erdős minimum overlap).
- **A score beyond a proven bound:** DeepMind problems #14 (t-designs).
- **Translation invariance broken on integer data:** DeepMind problems #15 (difference bases).
- **After the fixes:** every post-fix version PASSes for its fixed bug, except DM-15 (above).

## 4. New findings, confirmed independently (published code at the stated commit)

| Scorer | Finding | Class |
|---|---|---|
| DeepMind problems, `flat_polynomials` C⁻ and C⁺ (the C⁺ result is a separately labelled extra run, `extra/`) | Coefficients are not checked to be ±1. Scaling them moves the score in the optimiser's favour without limit (e.g. C⁺ scaled by (1−0.01) scores 1.3395 against 1.3531) | Type: `exploitable_type_violation` |
| DeepMind problems, `kakeya_needle_2d` (triangles) | An infinite parameter is accepted and gives a better (smaller) area | Invalid input |
| DeepMind problems, `hypergraph_turan_tetrahedron` | NaN weights or one extra entry accepted at an equal score | Invalid input (no gain) |
| DeepMind results, hexagon `verify_construction` (at 4226acb, and still after PR #13) | With extreme coordinates (about 1e150), the containment check degenerates. The pre-fix version accepts 11 unit hexagons in an outer hexagon of negative side; the post-fix version accepts side 0.0034. Published record: 3.931 | Exploitable invalid input (absurd magnitudes) |
| DeepMind problems, `squares_in_square` (after PR #19) | One extra square accepted at an equal score | Invalid input (no gain) |
| DeepMind problems, `difference_bases` (after PR #17) | Still not translation-invariant: 0 is added to the set | C4 integer invariance |
| DeepMind problems, `equidistant_points` (extra run, `large` budget) | A wrong vertex count returns +1e9, the best possible score under maximise. A naive search finds non-convex 15-point sets scoring −0.244 against −0.490 for AlphaEvolve's construction (not found at `standard`) | Sentinel; exploitable invalid |

**Found in the pre-lock pilot** (`../pilot/`), all reproduced through the shipped command:
- OpenEvolve `third_autocorr_ineq` @ ac5f8f5 trusts the self-reported C3 within a 0.001 slack (`C2 trusts_self_report`). That slack is about 40% of a record margin.
- A float "counterexample" to the matrix AM-GM inequality, scored +1.9e−6 by the published `get_score`, is −2.9e−9 at 60 digits. As a claim, C5 rates it `claim_within_rounding`; the tool did not find it by its own search.

**Contract writing also turned up notebook values the extracted code does not reproduce** (recorded in `../contracts/DM/EXTRACTION_*.yaml`):
- the equidistant notebook's printed −0.48898, which was produced after out-of-order cell execution;
- the stored flat-polynomial scores for n=80 (C⁺) and n=38 (C⁻);
- the autocorrelation cell titles.

## 5. Reading these results

The capability works as designed:
- deterministic for a given seed and search sizes (a re-run with `--steps-from` reproduces each receipt's content exactly, §6);
- receipted;
- confirmed by an independent second way (76/76, plus 9/9 on the extra runs);
- no confirmed false alarm after the v1.1 rule fixes.

It reliably finds the **common classes** of scorer loopholes: invalid input, self-reports, missing type checks, integer invariance. On a random sample of public scorers it found few problems, and none in the self-report or invariance classes. It is a useful pre-run checker. It is not a discovery engine for deep loopholes.

## 6. Reproducing

```bash
pip install -e '.[stress]' -r benchmarks/evaluator-stress/requirements.txt
for r in $(find benchmarks/evaluator-stress/results -name receipt.json); do consilience verify "$r" > /dev/null && echo "ok  $r" || echo "BAD $r"; done
```

On a fresh clone (20 Nov 2026, Python 3.13), all 47 stored receipts verify once `requirements.txt` is installed. The first fresh-clone attempt, using only the packages listed earlier in the external note, failed on 3 receipts: their scorers import `matplotlib` and `pydantic`. Those two are now in `requirements.txt`.

**Determinism.** On the same fresh clone, 17 labelled contracts (all under 100 s) were run again:
- **Unpinned:** all 17 gave the same verdicts and the same blocking findings. But 8 receipts differed in detail (the depth of the naive search and the values it reported), because their search sizes were scaled by measured call time.
- **Pinned** to the recorded sizes (`--steps-from`) and written to the original location: **17 of 17 receipt hashes are identical** to the stored ones, on Python 3.13 against 3.12 for the original run. Written elsewhere, only the stored contract path differs, because it is relative to `--out` (checked on `DM/flat_polynomials_c_minus`).

```bash
consilience stress benchmarks/evaluator-stress/contracts/LABELS/oe562_erdos_pre/contract.yaml \
  --steps-from benchmarks/evaluator-stress/results/receipts/LABELS/oe562_erdos_pre/receipt.json --out /tmp/rerun
```

