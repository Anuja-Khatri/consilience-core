# Verification log: evaluator-stress benchmark

## Run 1: stopped (20 Nov 2026)

- **Started** after the preregistration commit 6049a69: all 111 contracts, `standard` budget, seed 0, 3 jobs. Log: `results/first_run_stopped.log`.
- **Seen before stopping** (about 20 contracts, mostly CE and early DM): 3 BLOCKs in CE (circle_packing_square_26 and _32, second_autocorr_ineq: C1 `exploitable_invalid`, not yet independently checked); 13 PASS. The notebook's own superseded autocorrelation versions (v0, v1, v2) were among the PASSes.
- **Engine bugs (mine)** crashed 4 contracts:
  - an IndexError on scalar (0-d) construction fields in the C1 attack generator (CE hexagon_packing_11 and _12);
  - a reshape error in the `distinct` rule on an empty 2-D field (CE minimizing_max_min_dist_2d_16 and _3d_14).
- **Stopped** on Anu's instruction: run at most 45 contracts, then analyse whether to stop or continue. The crash bugs would have forced a re-run from scratch anyway (preregistration §4).

## Deviation 1 (Anu, 20 Nov 2026): a capped run of 45 contracts

- **Engine fixes:** both crash bugs fixed, with a regression test (`test_scalar_and_2d_fields_do_not_crash`).
- **Selection** (`SELECTION_45.txt`), fixed before the run by a rule, not by results:
  - **all 24 labelled cases:** the 13 pre-fix contracts (for M1) and the 11 post-fix contracts (for M2(b));
  - **21 unlabelled contracts:** a seeded random sample (`random.Random(0)`, sorted pools) stratified by set: DM 11, OE 5, CE 3, SH 1, G 1;
  - **excluded from the pool:** the `not_new` superseded versions and the one unrunnable scorer.
- **Selection bias, stated plainly:** the sample was drawn after 20 results from run 1 had been seen. It is a seeded random draw over all unlabelled contracts, so those results could not steer it. Three of the CE contracts seen in run 1 happen to be drawn.
- **Run:** from scratch, `standard` budget, seed 0.
- **Measures on the 45:**
  - M1 and M2(b): exactly as preregistered (all labels are included);
  - M3: on the 21-contract sample only, reported with that denominator (no extrapolation as a headline);
  - M5 and M6: on the 45.
- **Decision point:** after the 45, analyse against the forecast and the early-warning lines, and report to Anu with a recommendation to stop or continue.

## Run 2 (capped, 45 contracts): completed 20 Nov 2026

- **Engine crash bugs** found during the run (all fixed, with regression tests): float overflow in the in_disk and norm rules on ×1e300 attacks; mismatched counts between paired fields in pairwise_separation and in_box; empty inputs in geometric rules.
- **Re-runs:** the 7 contracts that crashed were re-run, 4 of them twice. The fixes touch only code paths that raised exceptions, so no completed contract executed them.
- **Independent check:** 113 findings; 102 re-implemented, all agree; 11 (`exploitable_type_violation`) checked by verify only.
- **Two decision-rule flaws found by hand.** They produce zero-gain BLOCKs, and the independent check cannot catch them because it re-checks the same inequality:
  1. "beats the record" compares with the record alone, not with the better of reference and record;
  2. `exploitable_type_violation` compares only with the projected equivalent, which for magnitude attacks is a different construction.

  Not fixed: a fix changes the locked decision rules, so it goes to Anu first.
- **Analysis and recommendation:** consilience-docs `deepmind/stress/RESULTS_45_ANALYSIS.md`.

## Deviation 2 (Anu approved, 20 Nov 2026): decision rules v1.1, then run 3 (45 contracts, from scratch)

- **Rule 1:** a candidate "beats the record" only if its worst case beats the better of the record and the valid base (the reference, or the valid-twin base) by more than m. This removes zero-gain BLOCKs.
- **Rule 2:** `exploitable_type_violation` requires the score to beat both the projected valid equivalent and the reference by more than m.
- **verify** and the independent check were updated to the same purpose. The independent check now also requires a gain over the valid reference: it challenges the rule's purpose, not only its arithmetic.
- **Run 3:** the same `SELECTION_45.txt`, from scratch, `standard` budget, seed 0. Run 2's results stay in history and are summarised in RESULTS_45_ANALYSIS.md (consilience-docs).
- **Note on run 3:** the version string was bumped to 0.3.0.dev0 (docs and plugin work) while run 3 was in progress, so some receipts say 0.2.0.dev0 and later ones 0.3.0.dev0. No engine code changed during the run: the last engine commit before it was 34350aa.

## Fresh-clone check (20 Nov 2026, after run 3)

- **Setup:** a clean clone of `stress-check` at f53af29 into a new Python 3.13 virtual environment.
- **Tests:** with `.[test]` installed, 999 passed and 16 skipped. The 2 skips beyond the local run are optional `pyarrow` and `pandas` tests.
- **Receipts:** `consilience verify` passed on 44 of the 47 stored receipts with the packages first listed in the external note. The other 3 (`G/circle_packing`, `DMR/dmr12_hexagon`, `LABELS/dmr12_hexagon_post`) failed because their scorers import `matplotlib` and `pydantic`.
- **Fix 1:** `requirements.txt` now pins every third-party package the scorers import, at the versions used for runs 1–3. With it installed, all 47 receipts verify.
- **Fix 2:** `verify` printed a raw traceback when a scorer could not run. It now fails with "could not run the scorer" and names the missing module (test `test_verify_reports_unrunnable_scorer_cleanly`).
- No verdict or number changed.
