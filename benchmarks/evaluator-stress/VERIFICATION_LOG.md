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
