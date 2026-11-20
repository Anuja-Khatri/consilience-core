# LABELS coverage

Pre/post-fix contracts for labelled bugs (commits in `benchmarks/evaluator-stress/SOURCES.yaml`,
`label_commits`). This file was started by the OpenEvolve-labels author; rows for other labelled sets (DM, DMR)
belong in their own section below.

## OpenEvolve labels (OE-514, OE-548, OE-549, OE-562)

Written 20 Nov 2026 by a model. No `consilience stress` run, no attack: the only scorer calls are
`validate_contract.py`'s. All rows below pass `validate_contract.py`. Minutes exclude the shared reading time
and the OE @ ac5f8f5 work these were derived from (see `contracts/OE/COVERAGE.md`).

| slug | status | minutes | contract lines | glue lines | notes |
|---|---|---|---|---|---|
| oe514_matmul_pre | OK | 5 | 46 | 83 | Evaluator @ a1e9d91 (pre-fix). Same contract, glue, adapter template and reference as `OE/matmul`. run() reports n, m, p, loss and rank; all are `claimed` fields recomputed from the factors (understood from issue #514 via tests/test_example_evaluator_integrity.py @ bc36680; no test run). |
| oe514_matmul_post | OK | 2 | 46 | 83 | Evaluator @ bc36680 (post-fix; identical to ac5f8f5). Same contract as pre. |
| oe514_funcmin_pre | OK | 5 | 33 | 22 | Evaluator, `openevolve/evaluation_result.py` and initial_program.py (as `program_template.py`) @ a1e9d91. `template` harness; construction (x, y); the reported `value` is `claimed`. Same contract as `OE/function_minimization`. No record. |
| oe514_funcmin_post | OK | 2 | 33 | 22 | Same files @ bc36680 (identical to ac5f8f5). |
| oe549_first_autocorr_pre | OK | 1 | 49 | 8 | Copied unchanged from `pilot/oe_c1_pre` (evaluator @ 23dc34b). |
| oe549_first_autocorr_post | OK | 1 | 49 | 8 | Copied unchanged from `pilot/oe_c1_post` (evaluator @ 464054d). |
| oe562_erdos_pre | OK | 1 | 49 | 22 | Copied unchanged from `pilot/oe_erdos_pre` (evaluator @ b6359e7). |
| oe562_erdos_post | OK | 1 | 49 | 22 | Copied unchanged from `pilot/oe_erdos_post` (evaluator @ da723ad). |
| oe548_cpr_pre | OK | 1 | 43 | 23 | Copied unchanged from `pilot/oe_cpr_pre` (evaluator @ 464054d). |
| oe548_cpr_post | OK | 1 | 43 | 23 | Copied unchanged from `pilot/oe_cpr_post` (evaluator @ 04270bd). |

Notes on the copies: they are identical to the pilot except for the added `contract_author: model` line, so they keep the pilot's conventions,
which differ from `CONTRACT_AUTHORING.md` in one place: the one-line provenance header without the file path.
After review, `contract_author: model` was added to all six; nothing else in them was changed. Their OE @ ac5f8f5
counterparts (`OE/first_autocorr_ineq`, `OE/erdos_min_overlap`, `OE/circle_packing_rect`) add
non-degeneracy predicates, invariances, and records in the published quantity with a glue map.

Licence: vendored files are from OpenEvolve (https://github.com/algorithmicsuperintelligence/openevolve),
Apache-2.0, unmodified below their provenance header.
