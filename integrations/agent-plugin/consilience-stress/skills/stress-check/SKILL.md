---
name: stress-check
description: Use before running AlphaEvolve-style program search (AlphaEvolve on Google Cloud, OpenEvolve, ShinkaEvolve, CodeEvolve) or any optimiser against a scoring function, and whenever you write or change such a scoring function or a reward function with structured answers. Writes a short contract describing what a valid answer is, then runs `consilience stress` to find invalid answers the scorer accepts, self-reported numbers it trusts, and transformations that change its verdict, each with a re-runnable counterexample.
---

# Stress-test a scoring function before optimising against it

An optimiser will find any loophole in the scoring code. This skill checks the scorer **before** a costly run. It finds:
- invalid answers it accepts;
- numbers it trusts from the candidate;
- verdicts that change under transformations that should not matter.

## When to use

- You are about to launch program search or any optimiser against a scoring function.
- You wrote or changed a scoring/evaluator/reward function whose candidate *returns a construction*: numbers, vectors, point sets, integer sets, matrices, coefficient lists, graphs.
- Someone claims a record from such a scorer, and you want to know whether the improvement is larger than the scorer's own numerical noise (`claimed_best`, check C5).

**Do not use it for:**
- algorithms tested on hidden inputs (speed or correctness tasks);
- LLM-judged scores;
- scorers whose input is a function.

Those are out of scope.

## Steps

1. `pip install 'consilience[stress]'`.
2. **Write `contract.yaml` next to the scorer** (full reference: `docs/stress.md`). Contracts are model-drafted, so mark them with `contract_author: model`. Write what a valid answer is **from the problem statement, not from the scorer's own checks**:
   - **harness:** how to call the scorer (`function`, `py_path`, `cli_json`, `sdk_dict`, `template`), the score key, and how it signals rejection;
   - **fields:** the construction, plus any self-reported numbers (`role: claimed`, recomputed by a glue function);
   - **validity:** strict rules (finite, range, shape, count, integral, alphabet, convex_polygon_ordered, pairwise_separation, …). Equalities on real numbers need a stated `tolerance`;
   - **invariances:** only transformations that truly leave the true score unchanged;
   - **score:** the direction, and the record **as published** (a string, with its source);
   - **reference:** a known-valid candidate, saved as `.npz`.
3. **Run** `consilience stress contract.yaml --out receipts/` (or `/stress-check contract.yaml`).
4. **Read the result:**

| Result | Meaning |
|---|---|
| **BLOCK** | A counterexample exists. Each finding names the rule broken and stores the candidate under `receipts/candidates/`. Fix the scorer, then re-run until it no longer BLOCKs |
| **PASS** | "No counterexample found within the budget". **Not a proof** |
| **ABSTAIN** | The check could not run. The reason is given (e.g. `reference_invalid` means the contract is wrong, not the scorer) |

5. **Anyone can re-check a result:** `consilience verify receipts/receipt.json`.

**Before trusting a PASS, a human must read the contract.** A missing validity rule means that rule is never tested.

## What the checks do

| Check | What it does |
|---|---|
| C1 | Invalid answers (NaN/inf, wrong count, out of range, wrong type, duplicates, extreme magnitudes, slight scaling). Do they score as well as a valid one? |
| C2 | Self-reports. Does changing only a reported number raise the score? |
| C3 | A naive search knowing nothing about the problem. Does it end on invalid answers that beat the best valid one? |
| C4 | Does the score change under declared invariances on integer data? Does a yes/no threshold flip under them? |
| C5 | Is a claimed record better than the record by more than the scorer's own noise and the record's precision? |
