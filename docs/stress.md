# `consilience stress`: check scoring code before you optimise against it

```bash
pip install 'consilience[stress]'
consilience stress contract.yaml --out receipts/
consilience verify receipts/receipt.json
```

## 1. What it is, in one paragraph

Optimisers find loopholes. When you run AI program search (AlphaEvolve, OpenEvolve, ShinkaEvolve, CodeEvolve), reinforcement learning, or any automated search against a scoring function, the search does not care what you *meant*. It optimises what the code *rewards*. If the scorer:
- accepts a NaN;
- trusts a number the candidate reports about itself;
- forgets a constraint;
- flips its yes/no answer because of float rounding,

then the search will find it, and you get a fake record. DeepMind's own AlphaEvolve notebooks say it plainly: *"AlphaEvolve will cheat by any means possible"*.

`consilience stress` reads a short **contract** that says what a valid answer is, written from the problem statement and independently of the scorer. It then attacks the scorer **before** you spend compute on a search. It returns one of three verdicts:
- **BLOCK**, with a counterexample anyone can re-run;
- **PASS**, which means no counterexample was found within the stated budget (*not* a proof);
- **ABSTAIN**, with a named reason.

Every run writes a receipt that `consilience verify` re-checks.

## 2. When to use it, and when not to

**Use it when:**

| Situation | What you get |
|---|---|
| You are about to launch program search or any optimiser against a scoring function | The common loopholes found first, on your own CPU, in seconds to minutes, instead of after a costly run |
| You wrote or changed a scorer, evaluator or reward function whose candidate *returns a construction*: numbers, vectors, point sets, integer sets, matrices, coefficient lists, graphs | A regression check you can rerun on every change (CI, or the agent plugin's hook) |
| Your scorer accepts numbers the candidate reports about itself (`c3`, `reported_sum`, `rank`) | Check C2 finds how far a lie can move the score |
| Someone claims a record from such a scorer | Check C5 says whether the claimed improvement is larger than the record's stated precision and the scorer's own numerical noise |
| You maintain a benchmark of scoring functions | A shared, versioned contract per scorer, and receipts others can re-check |

**Do not use it (out of scope) for:**
- **algorithms tested on hidden inputs:** speed or correctness tasks, sorting, TSP solvers, image filters. They need behavioural attacks (constant outputs, cached answers, reading fixtures), which this tool does not do;
- **LLM-judged scores;**
- **scorers whose input is a function or a program** rather than a construction;
- **sandboxing.** `stress` runs the scorer's code with your permissions, in a subprocess with a time limit. It is not a security boundary;
- **proving a scorer correct.** PASS is evidence at a budget, never a proof.

## 3. Who it is for, and what each can do

| Who | What they do with it |
|---|---|
| **An evaluator author** (AlphaEvolve on Google Cloud: *"you supply the seed program and the evaluator"*; or OpenEvolve, ShinkaEvolve, CodeEvolve users) | Write a contract once (median 10 minutes in our benchmark), run `stress` before every search, fix what BLOCKs, and keep the contract in the repository so regressions are caught |
| **An AI coding agent** | With the agent plugin (`integrations/agent-plugin/consilience-stress`), the check runs automatically after the agent edits a scoring file that has a contract, and the verdict appears in the agent's context |
| **A researcher claiming a record** | Attach a receipt that shows the claim survives the scorer's noise and the record's precision (C5), and that the scorer was stress-checked |
| **A reviewer, or a leaderboard maintainer** | Re-run `consilience verify` on a submitted receipt. Run `stress` on the evaluator behind a leaderboard |
| **A benchmark or RL-verifier author** | Treat contracts as a test suite for the verifier: invalid inputs, self-reports and invariances become regression tests |

## 4. Five-minute start

**1. Install** with `pip install 'consilience[stress]'`. You need Python ≥ 3.10 and numpy.

**2. Write `contract.yaml`** next to your scorer. Example: a scorer that sums four numbers that must lie in [0, 1]:

```yaml
kind: evaluator-contract
name: toy/sum_in_unit_box
contract_author: human            # or "model" if an AI drafted it
harness:
  kind: function                  # call score(x) directly
  evaluator: scorer.py
  entry: score
fields:
  - {name: x, type: real_array, shape: [4], role: construction}
validity:                          # what a valid answer IS (from the problem, not from the scorer)
  - {rule: finite, field: x}
  - {rule: range, field: x, min: "0", max: "1"}
score:
  direction: maximize
  record: {value: "4.0", source: "toy: the maximum is 4"}
reference: {file: ref.npz}         # a known-valid candidate, e.g. np.savez("ref.npz", x=[0.5]*4)
```

**3. Run:**

```bash
consilience stress contract.yaml --out receipts/
```

**4. Read the result:**
- `BLOCK C1 accepts_gross_invalid [finite]: attack=x:nonfinite[0]=nan`: your scorer accepted a NaN at a score at least as good as the valid reference. The candidate is saved in `receipts/candidates/`.
- `PASS: no counterexample found within the 'standard' budget (seed 0). Not a proof.`

**5. Anyone can re-check:** `consilience verify receipts/receipt.json`. It re-scores every stored counterexample and re-checks the inequality that decided each BLOCK.

**Exit codes:** 0 PASS, 1 BLOCK, 2 ABSTAIN, 64 usage error. A BLOCK always wins over an ABSTAIN elsewhere, so a reproducible problem is never hidden.

## 5. The five checks, in plain words

All checks are deterministic for a given seed. No language model takes part in any verdict.

| Check | Question | How |
|---|---|---|
| **C1** Invalid answers | Does the scorer accept an answer the contract rules out, and does it gain from it? | It attacks the reference with NaN/±inf (at distinct positions), wrong counts, empty input, extreme magnitudes, slight scaling, values just past each range bound, fractional values, duplicates and off-alphabet values. Accepted candidates that did not gain are searched further ("escalation") to see if the invalidity can be exploited |
| **C2** Self-reports | Does the scorer trust a number the candidate reports about itself? | It keeps the construction and changes only the reported value, by stepped and then bisected amounts. If the score rises by more than the margin m, it BLOCKs |
| **C3** Naive search | Where does a dumb optimiser end up? | A seeded random local search, knowing nothing about the problem, maximises the scorer. Ends that break the contract are compared with a **valid twin** search held to valid answers with the same budget |
| **C4** Invariance and noise | Does the score change under transformations that must not change the true score? | Integer data: any change BLOCKs (integers leave no rounding excuse). Threshold scorers (e.g. "positive = counterexample"): a yes/no answer that flips under the invariances BLOCKs. Real data: deviations are reported, and BLOCK only if the contract states an `invariance_tolerance` |
| **C5** Claimed record | Is a claimed best really better than the record? | Over the claim's invariance orbit: `beats_record` / `within_resolution` / `below_record`, or for thresholds `beats_threshold` / `claim_within_rounding` / `below_threshold`. C5 never changes the scorer's verdict |

**The margin m** (printed in every result) is the largest of three things:
- the record's stated precision: half a unit in its last written digit, carried through a unit map if needed;
- the scorer's noise on the reference: the spread of its score under the declared invariances;
- 1e−9 relative.

A finding needs a gain larger than m. **An exploit has to beat the better of the record and the best valid answer known.** That prevents BLOCKs that gain nothing.

## 6. Contract reference (every key)

### 6.1 Top level

| Key | Required | Meaning |
|---|---|---|
| `kind` | yes | Always `evaluator-contract` |
| `name` | yes | A label |
| `harness` | yes | How to call the scorer (§6.2) |
| `dims` | no | Named sizes for shape expressions, e.g. `{n: 600}`; shapes may use `+`, `*` and parentheses |
| `fields` | yes | The candidate's fields (§6.3) |
| `returns` | no | The order of fields returned by the generated program, or passed to the function (default: the field order) |
| `validity` | yes in practice | Rules for a valid answer (§6.4). A construction field without a rule makes the run ABSTAIN (`no_validity_rules`) |
| `caller_enforced` | no | Rules the scorer's caller guarantees (e.g. a size not passed to the scorer). Candidates breaking them are never sent, and the receipt states the assumption |
| `invariances` | no | Transformations that must not change the true score (§6.5) |
| `score` | yes | `direction`, optional `record` and `bound` (§6.6) |
| `noise` | no | `{probe_repeats: 3}`: the reference is scored this many times; differing scores mark the scorer as non-deterministic, and medians are used |
| `reference` | yes | `{file: ref.npz}`: a known-valid candidate. Use the best known valid construction where one exists |
| `initial` | no | `{file: init.npz}`: where an optimiser would start. Used as a C3 start |
| `claimed_best` | no | `{file: best.npz}`: the claim C5 judges |
| `glue` | no | A small Python file with helper functions (§6.7). It **must not import the scorer**; the loader checks this |
| `contract_author` | no | `human` (default) or `model`. Shown in every result: read a model-drafted contract before trusting a PASS |
| `description` | no | Free text |

Unknown keys, rules or transforms give a named error. Nothing is guessed.

### 6.2 `harness`

| Key | Meaning |
|---|---|
| `kind` | One of:<br>• `function`: call `entry(*args)`, for an extracted scoring function;<br>• `py_path`: generate a program file whose `program_function` returns the candidate, then call `entry(path)` (OpenEvolve style);<br>• `cli_json`: run a command (`argv`) and read `result_file` (ShinkaEvolve, CodeEvolve style);<br>• `sdk_dict`: call `entry({"content": {"files": [...]}})`;<br>• `template`: like `py_path`, but the program is your `program_template` with the code between `block_start` and `block_end` replaced. This keeps code outside the evolve block, such as validity code that lives in the candidate file |
| `evaluator` | The scorer file, relative to the contract |
| `entry` | The function to call (all kinds except `cli_json`) |
| `program_function` | The function the generated program defines (`py_path`, `cli_json`, `sdk_dict`, `template`) |
| `argv`, `result_file` | `cli_json` only. Placeholders: `{python}`, `{evaluator}`, `{program}`, `{outdir}` |
| `program_template`, `block_start`, `block_end` | `template` only |
| `score_key` | Key path into a returned dict, e.g. `combined_score` or `scores.scores[metric=sum_of_radii].score` |
| `reject` | How the scorer says no:<br>• `keys_present: [error]`;<br>• `values: [-1e9]` (finite numbers only; list `0.0` only if 0 is never a legitimate score);<br>• `file: {path, key, equals}`.<br>Exceptions, non-numeric and non-finite outputs always count as rejections |
| `timeout_s` | Seconds per call (default 30). A timeout is never stored as a score |
| `call_args` | Keyword arguments for `function` |
| `extra_files` | Every other file the scorer loads. They are hashed into the receipt, so `verify` notices an edit |

### 6.3 `fields`

Each field has a `name`, a `type` and a `role`.
- **Types:** `real`, `int`, `real_array`, `int_array`, `complex_array`, `int_set`, `graph` (an edge list), `ragged` (declared, not implemented in 0.3).
- **Roles:**

| Role | Meaning |
|---|---|
| `construction` | Attacked and searched |
| `claimed` | A self-reported number. Give `quantity: <name>`, recomputed by `glue.quantities[name]`, independently of the scorer. Generated candidates report the true recomputed value; C1 also sends a "plausible lie" that keeps the reference's value |
| `fixed` | `value: ...` |
| `derived` | `from: "len(x)"`, `from: "x.shape[1]"` or `from: "glue:<fn>"` |

### 6.4 Validity rules (exact rational arithmetic on the candidate's floats)

| Rule | Parameters | Class of a violation |
|---|---|---|
| `finite` | — | gross |
| `shape` | `shape: [n, 2]` | gross |
| `count` | `equals` / `min` / `max` | gross |
| `integral` | — | type |
| `distinct` | — | type |
| `alphabet` | `values: ["-1", "1"]` | type |
| `range` | `min`, `max` (strings); optional `tolerance` | small or large |
| `sum` | `equals`, `tolerance` (**required**), optional `axis` | small or large |
| `norm` | `equals`, `tolerance` (**required**), optional `axis` | small or large |
| `in_disk` | `radius`, `center` (for complex values) | small or large |
| `in_box` | `box: [[lo, hi], ...]`, optional `margin_from` (radii) | small or large |
| `pairwise_separation` | `radii_from` and/or `min_distance` | small or large |
| `convex_position` | — (strict, unordered) | large |
| `convex_polygon_ordered` | — (strictly convex in the given cyclic order) | large |
| `no_k_collinear` | `k` (default 3) | large |
| `no_k_coplanar` | `k` (default 4) | large |
| `graph_simple` | — | large |
| `predicate` | `call: <glue predicates key>`, `name`, `tolerance`, `equality: true` for equalities (a tolerance is then required) | small or large |

**The classes decide how a violation is judged:**
- **gross:** BLOCK if the score is at least the reference's;
- **type:** BLOCK if the score beats both the projected valid equivalent (rounded, snapped, de-duplicated) and the reference by more than m;
- **small** (≤ 1e−6 relative): BLOCK only if it beats the better of the record and the valid base;
- **large:** BLOCK if it beats that, or its paired gain over the valid base exceeds m.

### 6.5 `invariances`

| Transform | Meaning | Parameters |
|---|---|---|
| `permute` | Shuffle the rows or elements of one field | — |
| `cyclic_shift` | Change the start vertex of an ordered polygon | — |
| `translate` | Add a random vector (reals) or a random integer (integer types) | — |
| `rotate` | A random rotation | `dims: 2\|3`, optional `center` |
| `dihedral` | A discrete symmetry (exact quarter turns when `order: 4`) | `order`, optional `center` |
| `reflect` | A mirror image | optional `center` |
| `negate` | x → −x | — |
| `conjugate` | Q·M·Qᵀ on each matrix, Q a random orthogonal matrix | — |
| `scale` | Multiply by 2^k (exact in floating point); the score is divided by 2^(k·`score_exponent`) | `score_exponent` |
| `relabel` | Relabel graph vertices | — |

Optional `invariance_tolerance` on real fields: a deviation above it BLOCKs.

**Declare only true invariances.** A wrong one creates false findings. A missing one only means less is tested. Each transform acts on one field; joint transforms of paired fields are not supported in 0.3.

### 6.6 `score`

```yaml
score:
  direction: maximize                 # of the scorer's output
  record: {value: "1.4557", source: "AlphaEvolve 2025, B.3", quantity: c3, map: c3_to_score}
  # threshold form: {value: "0", kind: threshold, success: ">", margin: "0", source: "..."}
  bound: {value: "2", kind: proven, source: "..."}
```

- **`record.kind`:** `best_known` (the default: an optimisation record) or `threshold` (a decision boundary, such as "positive = counterexample").
- **`record.value`:** always a string, copied as published. Its last written digit sets its precision.
- **`quantity` + `map`:** use these when the record is published in another quantity than the scorer's output (e.g. the scorer outputs BENCHMARK/C3). The map, a glue function, converts it, and the precision is carried through.
- **`bound`:** a proven bound. Any accepted candidate beyond it means the scorer is wrong (`exceeds_bound`).

### 6.7 Glue (optional, small, independent of the scorer)

| Name | Purpose |
|---|---|
| `to_scorer(candidate) -> args` | Convert the candidate into the scorer's arguments (`function` kind) |
| `compose(output, candidate)` | Turn the scorer's output into a number or a dict (e.g. `len(S) if verify(S) else 0`) |
| `quantities = {name: fn}` | Recompute claimed values |
| `predicates = {name: fn -> (ok, magnitude)}` | Problem-specific validity. Use exact arithmetic where you can |
| `project(candidate)` | Map onto the valid set. Needed to judge search findings when there is an equality rule |
| `maps = {name: fn}` | Record unit maps |

## 7. Findings: every kind, and what to do

| Finding | BLOCK? | Meaning | Usual fix |
|---|---|---|---|
| `accepts_gross_invalid` | yes | NaN/inf, a wrong count or shape, accepted at a score ≥ the reference | Validate shape and finiteness first |
| `sentinel_is_best` | yes | The scorer's failure value is better than a real score (e.g. +1e9 "error" under maximise) | Return the worst possible value on failure |
| `exceeds_bound` | yes | An accepted candidate beats a proven bound | The scorer computes the wrong quantity, or misses a constraint |
| `exploitable_type_violation` | yes | Off-alphabet, fractional or duplicate values score better than both their valid equivalent and the reference | Check the type (±1, integers, distinctness) |
| `exploitable_invalid` | yes | An answer breaking a rule beats the record, or the valid twin, by more than m | Enforce the missing constraint, with no tolerance beyond the problem's |
| `trusts_self_report` | yes | Changing only a reported number raises the score | Score the recomputed value; never the reported one |
| `invariance_broken_integer` | yes | A transform that cannot change the true score changes it, on integer data | A bug in how the scorer reads its input (order, offset) |
| `decision_flips_under_invariance` | yes | The yes/no answer depends on rounding | Add a decision margin larger than the observed spread, or use exact arithmetic |
| `invariance_violated` | yes | A deviation above your stated `invariance_tolerance` | — |
| `accepts_invalid_low_score` | reported | Accepted, but no gain | Usually worth validating anyway |
| `tolerance_headroom` | reported | A small violation accepted with a gain below what would matter | Know your tolerance |
| `self_report_headroom` | reported | A reported number accepted within a slack that buys less than m | — |
| `type_violation_harmless` | reported | The scorer rounds or snaps by itself | — |
| `unpaired_gain` | reported | Search ended invalid with a gain, but no valid base exists (equality rule without `project`) | Add `project` to the glue |
| `invariance_suspect` | reported | A real-valued deviation larger than 1e−9 relative | Look at the distribution |
| `nan_score`, `timeouts` | reported | — | — |

**ABSTAIN reasons:**
- `reference_invalid`: your contract and reference disagree;
- `reference_rejected`: the scorer rejects your valid reference;
- `no_validity_rules`;
- `harness_failed`: the scorer does not import or run (stderr is kept);
- `timeout`;
- `budget_exhausted`: a cap was hit with nothing found.

## 8. Budgets and runtime

| Budget | C3 restarts × steps | Escalation | Orbit size | Cap per check |
|---|---|---|---|---|
| `small` | 4 × 400 | 1 × 300 | 40 | 2 min |
| `standard` (default) | 8 × 800 | 3 × 500 | 100 | 10 min |
| `large` | 32 × 2000 | 6 × 1000 | 400 | 60 min |

- **Scorers slower than 0.05 s per call** have their search budget scaled down, and the scaled budget is printed and stored.
- **In our benchmark at `standard`,** most contracts took 6 seconds to 10 minutes.
- **Use `large`** before a big search, or when C3 matters. In one case, the equidistant-points scorer, C3 found the loophole only at `large`.

## 9. Receipts and `verify`

A receipt (`consilience-stress-receipt/v1`) holds:
- the normalised contract and its hash;
- the hashes of every file the run reads (scorer, `extra_files`, glue, candidates);
- the seed and budget;
- every BLOCK's counterexample, stored as exact JSON;
- the verdict, m and its source, and the stated limits.

Two runs with the same contract and seed give byte-identical receipts, apart from `created` and `environment`.

`consilience verify receipt.json`:
1. checks every hash;
2. re-scores every stored counterexample;
3. re-checks the inequality that decided each BLOCK, plus exact validity.

It exits 0 if every verdict reproduces and 1 if not. Use `--input` to point to the contract if it has moved.

## 10. Agent plugin

`integrations/agent-plugin/consilience-stress`, for Claude Code; the Antigravity layout is included but not runtime-tested.
- **The hook:** after the agent writes or edits a file that a neighbouring contract uses (its evaluator, glue or `extra_files`), it runs `stress --budget small` and puts the verdict in the agent's context. It always exits 0; it never blocks the agent or changes the scorer.
- **The skill `stress-check`** and **the command `/stress-check <contract>`.**
- A recorded live session is in `LIVE_RUN.md`.

## 11. Limits: read before relying on it

1. **PASS is not a proof.** C3 is a naive search standing in for an optimiser. In our benchmark it missed loopholes that were found at a larger budget, or that needed problem-specific insight.
2. **It is only as good as the contract.** A missing validity rule is never tested. A wrong invariance creates false findings. Contracts drafted by a model must be read by a person.
3. **It finds common classes of loopholes, not deep ones.** In our 45-contract benchmark it reliably caught invalid input (NaN/inf, wrong counts) and self-reported values. It did not catch a matrix-multiplication self-report exploit that needs a dimension change (OpenEvolve #514), or a negative-radius exploit (DeepMind results #11).
4. **On real-valued data, rounding noise and real bugs cannot be told apart automatically,** so C4 only reports them unless you declare a tolerance. For floating-point verdicts, the stronger answer is an exact or rational-arithmetic verifier, which some teams already use.
5. **Not a sandbox.**
6. **Out of scope:** algorithms on hidden inputs, LLM judges, function inputs, joint invariances of paired fields, and the `ragged` type.

## 12. The public benchmark

`benchmarks/evaluator-stress/` holds contracts for 89 public scoring functions, with vendored code kept under its own Apache-2.0 licence:
- 53 from Google DeepMind's AlphaEvolve problem notebooks;
- 2 from its results repository;
- 19 from OpenEvolve;
- 13 from CodeEvolve;
- 1 each from ShinkaEvolve and Google Cloud's AlphaEvolve samples;
- 22 pre-fix and post-fix versions of 13 known bugs.

It also holds the preregistration, the labels, the runner, an independent second-way checker and the results (`results/RESULTS.md`). Findings concern **the published code at the stated commit** only, never anyone's internal systems or published results.
