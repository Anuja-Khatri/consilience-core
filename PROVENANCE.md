# Provenance

What this repository copies or adapts from other repositories, and from which commit.

## The `compare`, `check` and `verify` package (WP4, version 0.1.0)

| What | From | Commit | How |
|---|---|---|---|
| Strict number grammar and the refusal reasons (`space_separated_digits`, `ambiguous_separator`, `non_finite`, `parenthesised_number`, `ambiguous_scale_suffix`, `compound_quantity`, …) in `src/consilience/units.py` | [consilience-ledger](https://github.com/Anuja-Khatri/consilience-ledger) `labext/units.py`, branch `wp1-public-truth` | `7c1f9235b582666403537dd929c844e4b2dfc8cf` | adapted (MIT); the ledger's alias table, which rewrote spellings such as `C` to degC and `M` to mol/L, is not copied: a general library refuses `C` as ambiguous and uses pint's case-exact names |
| Unit-part checks (digits only as exponents; the unit read on its own by pint) | [lab-gate](https://github.com/Anuja-Khatri/lab-gate) `gate/boundary/units.py`, branch `wp2-release` | `47a92b997ab31c74dbd1d42f0f215b0675a6645b` | adapted (MIT) |
| Refusal test cases in `tests/test_units.py`, `tests/test_compare.py` | lab-gate `tests/test_malformed_numbers.py` (same commit); consilience-ledger `tests/test_input_hardening.py`, `tests/test_units.py` (same commit as above) | as above | cases ported, tests rewritten for this package |
| Comparison logic: an unstated condition refuses before a predicate runs; difference against the larger of a floor and the two uncertainties | consilience-ledger `labext/comparability.py` (`evaluate_comparability`) and `labext/judge.py` (`compare_pair`, step 3) | `7c1f923…` | re-implemented for a general conditions dictionary; no claim card is needed. Relative tolerance is new |
| The `electrochemistry` pack (`src/consilience/data/packs/electrochemistry.yaml`), rules EC1-EC4 with their plain-English lines, rationales and sources | consilience-ledger `rules/comparability_rules.yaml`, version comparability-v0.1, `rules/rules.lock` sha256 `ba3db7c1b7803c4391fb82d32440b2085e30c3cd6eea4dcb725b7ccc1adf92b7`, rules CR1-CR4 | `7c1f923…` | ported (CC BY 4.0) into the pack format; see differences below |
| Rule-file house style (plain-English line, rationale, source, version, SHA-256 over canonical JSON) | lab-gate `gate/registry/invariants.yaml` and `gate/registry/lock.py` | `47a92b9…` | followed, no code copied |
| Packaging and release pattern (`scripts/check_release.sh`, `.github/workflows/publish.yml`, `docs/RELEASE.md`, exit code 64 for usage errors) | lab-gate `pyproject.toml`, `lab_gate/cli.py`, `scripts/check_release.sh`, `.github/workflows/publish.yml`, `docs/RELEASE.md` | `47a92b9…` | the workflow is lab-gate's reviewed file with the project name changed; the script and docs adapted |
| The data-check rule kinds (`limit`: a value against a limit recorded in the same row, with a margin and a constant offset, and a fallback for rows with no limit; `bound`: physical bounds) | the project owner's private repository consilience-operator-v4 (no licence), with her approval to publish a generic version | read at `dd4ded7` | **no code copied.** The idea of the check was generalised and the code written fresh. Nothing specific to any dataset (column names, adapters, constants, counts, notes) was taken |

Differences between the electrochemistry pack and the ledger's rules CR1-CR4:

- An unstated current-density normalisation is `not_stated(current_density.normalization)`.
  In the ledger, two unstated normalisations compared equal. This pack is stricter.
- A stated electrolyte with an unstated concentration is
  `not_stated(electrolyte.concentration)`; in the ledger it was a mismatch of CR1. Both
  refuse the comparison.
- Electrolyte names match ignoring case through the same alias list (sulfuric and
  perchloric acid), as in the ledger.
- The ledger's overpotential floor of 13 mV is **not** in the pack: a floor is a property
  of a measured spread, which the user supplies with `--floor`.

The made-up example files in `src/consilience/data/examples/` were written for this
package and describe no real instrument, sample or experiment.

## The nanopublication pilot (WP3)

| What | From | Commit | How |
|---|---|---|---|
| Ten records in `pilot/records/` (three claim cards from `ledger/claims.json`, seven refused comparisons from `ledger/rejections.json`), copied unchanged inside record envelopes | [consilience-ledger](https://github.com/Anuja-Khatri/consilience-ledger), branch `wp1-public-truth` | `7c1f9235b582666403537dd929c844e4b2dfc8cf` | `scripts/select_pilot_records.py`, which reads the ledger with `git show` (read only) and checks every hash before writing |
| The verdict hash method (`compute_verdict_hash`: SHA-256 over sorted-key JSON) and the ledger-hash recipe, re-implemented in `src/consilience/receipts.py` | consilience-ledger, `vendor/engine/judge/hash/determinism_check.py` and `labext/ledger.py` | same | re-implemented, no code copied |
| Condition rule names (CR1–CR4 and their fields), used only for readable labels | consilience-ledger, `rules/comparability_rules.yaml` | same | read by the selection script into each envelope's `context` |
| Source document links | consilience-ledger, `corpus/MANIFEST.yaml` | same | copied into `scripts/select_pilot_records.py` |
| Nineteen records in `pilot/theories/records/` (eleven theory claim cards and eight testable disagreements), copied unchanged inside record envelopes | [theconsilience-engine](https://github.com/Anuja-Khatri/theconsilience-engine), branch `claude/practical-newton-8fmocf`, `results/demo/files/iitxgnwt_judge.json` (the cross-theory demo's results, pinned there with a SHA-256 manifest) | `96ba4e435bd13718d36435cc3436d938d2d1f894` | `scripts/build_theory_records.py`, which reads the file at that commit, checks it against the manifest and writes each record with its line range and content hash |
| Nanopublication structure, the agent-introduction pattern, template shapes and the default provenance and pubinfo templates | [knowledgepixels/nanopub-skill](https://github.com/knowledgepixels/nanopub-skill) (documentation) and the templates it mirrors | read 16 Nov 2026 | followed, no code copied |
| Signing and trusty URIs | [`nanopub`](https://pypi.org/project/nanopub/) 2.2.2 from PyPI (Nanopublication/nanopub-py) | release 2.2.2 | used as a dependency |

No record was taken from a non-public repository.
