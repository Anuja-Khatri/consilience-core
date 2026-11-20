# Preregistration: the evaluator-stress benchmark

**Status: FINAL, 20 Nov 2026.** This was committed **before any benchmark run**. The commit that adds this final version is recorded in `results/RESULTS.md`, and every run comes after it.

The product spec is cycle 4, spec v1.0 (locked 20 Nov 2026), §10 and §12.

## 1. What is measured

`consilience stress` is run with **budget `standard`, seed 0** on every contract under `contracts/` (all sets plus `LABELS/`). The engine version is the commit that adds this file.

The contracts, labels and sources are frozen by this commit:
- `SOURCES.yaml`: every set, commit and label SHA;
- `LABELS.yaml`: each labelled bug, its pre-fix and post-fix contracts, the finding kinds that count as a match, and the link to its issue;
- `contracts/*/COVERAGE*.md`: every scoring function considered, including those out of scope, unrunnable or skipped, with the reason and the authoring time;
- `CONTRACTS.sha256`: the SHA-256 of every contract, glue, vendored scorer and candidate file.

**At freeze:**
- 112 contract files: 111 validate; DM/sum_difference_problem_ii is unrunnable as published, because its numba code does not compile on numba 0.68.1.
- Coverage rows: 110 OK, 23 out of scope, 11 skipped, 4 unrunnable. The median authoring time is 10 minutes.
- All contracts were drafted by a model (`contract_author: model`) under `CONTRACT_AUTHORING.md`, with no stress runs and no attacks.

**Engine changes made during step 4, before this freeze** (each found while writing contracts; none after any result):
- `harness.extra_files` is hashed into the receipt;
- non-finite reject values give a named error;
- the worker registers the scorer in `sys.modules`, which numba's recursive functions need.

## 2. Measures (spec §10.3)

| # | Measure | Definition |
|---|---|---|
| M1 | Recall | The share of the 13 labelled bugs in `LABELS.yaml` whose pre-fix contract BLOCKs with a matching finding (by kind, and by rule where the label names one), confirmed by the independent check or, for kinds it does not re-implement, by `consilience verify` |
| M2 | False alarms | (a) The number of BLOCK findings the independent check does not confirm, after investigation. (b) The number of labelled post-fix contracts still BLOCKed **for the fixed bug**, i.e. a matching finding kind on the fixed rule. **Target 0.** Other BLOCKs on a post-fix version count toward M3 if confirmed |
| M3 | New confirmed BLOCKs | BLOCKs on unlabelled contracts (and non-matching BLOCKs on labelled ones), confirmed independently, that are not in any public issue listed in §5. Reported by class (gross input; type; exploitable invalid; C2 self-report; C4 integer invariance; C4 threshold flip; exceeds bound) and by set |
| M4 | Records against noise | C5 verdicts where `claimed_best` is given. **Sets OE, CE, SH and G only.** DM C5 results are internal: they are reported only after an exact independent re-check and Anu's approved wording |
| M5 | Reach and cost | Of all scoring functions considered: the share with a contract; the share with a conclusive verdict (PASS or BLOCK); the median contract lines and glue lines; the median authoring minutes; the number needing glue predicates |
| M6 | Runtime | Per contract at `standard`, by harness kind; and how many had their budget scaled |

## 3. The independent second way (spec §10.4)

`check_independent.py` imports nothing from `consilience`. For every BLOCK it:
- re-scores the stored candidate in a fresh process with its own calling code;
- re-checks the broken rule with its own exact arithmetic;
- re-checks the deciding inequality.

Kinds it does not re-implement (`exploitable_type_violation`, and the rules norm, sum, in_disk, in_box, pairwise_separation, collinear, coplanar and graph) are marked "N/A" and confirmed by `consilience verify` only. That is stated in the results.

**A disagreement voids the finding** until it is resolved and logged in `VERIFICATION_LOG.md`.

## 4. Stop rule and early-warning lines

**Stop rule** (spec §10.5). The headline is reported only if all three hold:
1. M2 = 0 after investigation and any engine fix, with the run repeated from scratch;
2. the independent check agrees on every counted finding;
3. M1 ≥ 0.8.

Otherwise the results are reported as they are, naming what the generic checks miss.

**Early-warning lines** (`HONEST_STATUS_AND_EXPECTATIONS.md` §5, in consilience-docs). Anu is told at once if any of these hold:
- M1 < 0.8;
- any surviving false alarm;
- M3 < 10;
- fewer than 3 new C2 findings;
- conclusive reach below 70%.

The forecast written before this benchmark is in the same file (§3). RESULTS.md compares against it row by row.

## 5. Known public issues (a finding that matches one of these is not "new")

These are not new either:
- findings on the contracts under `not_new` in `LABELS.yaml` (superseded scorer versions shown in the notebook itself);
- NaN/inf findings on the four DM scorers named in issue #16, in either the `DM/` or the `LABELS/` copy.


From the survey of 20 Nov 2026 (`deepmind/research/option_B_check_2026-11-20.md`):
- **DeepMind problems repository:**
  - #1 (C3 autocorrelation max vs max|·|);
  - #8 (3-D sofa NaN);
  - #12 (ring loading off-by-one);
  - #14 (t-designs);
  - #15 (difference bases);
  - #16 (NaN/inf in squares_in_square, no_5_on_a_sphere, furstenberg_sarkozy, no_isosceles_triangles);
  - #22 (3-D Kakeya Monte Carlo);
  - comment on #6 (float determinant in no_5_on_a_sphere).
- **Results repository:** #11 (negative radii), #12 (hexagon NaN), #6 (C3 abs).
- **OpenEvolve:** #514, #548, #549, #562, and any issue or PR that changed a scorer between their fixes and ac5f8f5.
- **packing-certify:** float64 overlap acceptance and the 1e−6 tolerance in circle packing verifiers.

## 6. Claim discipline

- Statements are about "the published code at commit X". Nothing is said about any group's internal systems or published results.
- No issues, PRs or posts. Drafts per finding go to Anu.

## 7. Known design choices (made before the run; see COVERAGE notes)

- **Contract fields:** each contract fixes problem sizes, chooses a direction where the scorer and its search loop disagree, and writes records exactly as published, with their sources.
- **Records omitted:** where no published value could be verified, the record is left out, and C2/C3 materiality falls back to the reference floor or 1e−9 relative.
- **The pilot's AM-GM `claimed_best`** (our own float counterexample) is not in the benchmark contract, because the notebook ships no construction. That claim check stays a pilot demonstration only.
- **Gaps the contract format cannot yet express** (named in the COVERAGE notes):
  - joint permutations of paired fields;
  - sequence reversal;
  - modular and group-label symmetries;
  - some float-geometry inequalities, written as glue predicates.

  Missing invariances make C4 test less. They cannot create false BLOCKs.

## 8. Deviations

Any deviation from this document after the run starts is written in `VERIFICATION_LOG.md` with its reason and time, and repeated in RESULTS.md.
