# Writing the benchmark contracts (build step 4)

These are the rules every contract in `contracts/` follows. The format is spec v1.0 §6 (`consilience.stress.contract`). Worked examples are in `pilot/*/` (contract.yaml, glue.py, .npz files).

## 1. What is forbidden before preregistration

- **No benchmark results before preregistration.** Do NOT run `consilience stress`, `run_checks`, or any attack on a scorer. Do not hunt for bugs. Write *correct* contracts, nothing more.
- The only scorer calls allowed are those made by `validate_contract.py`: one call on the reference (and on `initial` / `claimed_best`).
- Never edit the vendored scorer code below its provenance header.
- Never commit; never touch git; never post or contact anyone.

## 2. Layout

```
contracts/<SET>/<slug>/
  contract.yaml        # the contract
  scorer.py | evaluator.py   # vendored scoring code with a provenance header (see §3)
  glue.py              # only if needed (conversion, quantities, predicates, project, maps)
  reference.npz        # a known-VALID candidate; where one exists, the best known valid construction
  initial.npz          # optional: what an optimiser would start from (the initial program's output)
  claimed_best.npz     # optional: the shipped best construction, if it is not already the reference
```

`<SET>` is one of `DM`, `DMR`, `OE`, `CE`, `SH`, `G`, or `LABELS` (pre/post-fix versions of labelled bugs).

## 3. Vendoring and provenance (Rule F)

- **Header,** first lines of every vendored file:
  `# Vendored from <repo URL> @ <full commit SHA>, <path>[, notebook code cells N,M] (Apache-2.0).`
  `# Unmodified below this header` (or, for DeepMind notebooks: `# Scoring cells copied verbatim; only imports added`).
- **DeepMind notebooks:** copy only the cells that define the scoring function and the helpers it calls, in the order the notebook defines them. Where a notebook has several versions of a helper, use the one the scorer's own cell defines, and say which in the header.
- **Extraction test (DeepMind only).** Run the extracted scorer once on the notebook's own shipped construction and compare with the score printed in the notebook output. Record the result in `contracts/DM/EXTRACTION.yaml`:
  `{slug, printed, recomputed, match: true|false, cause}`.
  A mismatch is not fixed by editing code; it is recorded. Example: equidistant printed −0.48898, which came from cell 8's 3-point helper after out-of-order execution.

## 4. Contract content

- **Validity comes from the PROBLEM STATEMENT,** not from the scorer.
  - Sources: the problem page (`problems/<n>.html` in the DM repo), the notebook prompt, or the docstring or README of the example.
  - Write what a valid answer *is* (strict; tolerance 0). Do not copy the scorer's tolerances.
  - Equalities on reals need a `tolerance`: use "1e-12" unless the problem states one.
  - Prefer the closed rule library; use a glue `predicates` function only when no rule fits. Glue must not import the scorer.
- **Every construction field needs at least one validity rule.**
- **Claimed fields:**
  - any number the candidate reports about itself that the scorer could recompute (e.g. `c3`, `reported_sum`, `rank`) is a `claimed` field;
  - give a glue `quantities` function that recomputes it from the construction, independently of the scorer.
- **Invariances:** declare only transformations that mathematically leave the TRUE score unchanged for the stated problem. Examples: permuting interchangeable items, translating where position is irrelevant, rotating a point set when no box is involved, `dihedral` with `center` for a square box, `scale` with the right `score_exponent`. When unsure, leave it out.
- **Record:**
  - written as a string **as published**, with `source`: paper, problem page, or the evaluator's own BENCHMARK constant with how many digits the paper states;
  - in the scorer's output units, or with a glue `maps` function plus `quantity`.
  - For counterexample searches (a positive score means a counterexample), use `kind: threshold` with `success` and `margin`.
  - If no record is known, omit it and say so in COVERAGE.md.
- **Direction:** of the scorer's output (`maximize` / `minimize`). Check the scorer and its search loop agree; if they disagree, write down which you chose and why in COVERAGE.md.
- **Reject:**
  - `keys_present` (e.g. `[error]`);
  - `values`, listing failure sentinels such as `-1e9`, `1e9` or `-1000000.0`. List `0.0` only if 0 can never be a legitimate score.
- **Reference:**
  - the shipped best construction where the notebook or example has one (load it from the notebook or example file);
  - otherwise the initial program's output, or a simple valid construction you build;
  - it must pass the contract's own rules and be accepted by the scorer.
- **`initial`:** the initial program's output, when it is cheap to get (no jax, no long optimisation). Optional.
- **`contract_author: model`** must be set on every contract you write, because they are drafted by a model.

## 5. Coverage log (M5): `contracts/<SET>/COVERAGE.md`

One row per scoring function in the set, including the ones you could not do:

| slug | status | minutes | contract lines | glue lines | notes |
|---|---|---|---|---|---|

- **status** is one of:
  - `OK` (validate_contract passes);
  - `out_of_scope` (callable input, not a construction, algorithm on hidden inputs: spec §4);
  - `unrunnable` (the scorer does not import or run as published: say why);
  - `skipped` (with the reason).
- **minutes:** your honest estimate of the authoring time.

## 6. Validate

```
python benchmarks/evaluator-stress/validate_contract.py contracts/<SET>/*/contract.yaml
```

Every `OK` row in COVERAGE.md must pass this.
