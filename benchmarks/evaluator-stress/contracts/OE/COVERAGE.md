# OE coverage (OpenEvolve @ ac5f8f5e39b7bffb707def97039076bb2135e992)

Written 20 Nov 2026 by a model (`contract_author: model` on every contract). No `consilience stress` run, no
attack, no bug hunting: the only scorer calls are `validate_contract.py`'s (reference and `initial`).
All `OK` rows pass `python benchmarks/evaluator-stress/validate_contract.py contracts/OE/*/contract.yaml`.

Scope: the 16 `examples/alphaevolve_math_problems/*` evaluators (heilbronn_convex, hexagon_packing and
minimizing_max_min_dist each ship two sizes in separate folders, so one contract each), plus
`examples/circle_packing`, `examples/circle_packing_with_artifacts`, `examples/function_minimization`.

Minutes are honest estimates of authoring time per row (the record revision after review took about 15 more minutes in total, not spread over the rows); about 25 further minutes went into reading the
rules, the spec, the loader and the pilot, shared by all rows. Glue lines include adapter templates and the
`openevolve/__init__.py` stub where present (vendored files are not counted).

| slug | status | minutes | contract lines | glue lines | notes |
|---|---|---|---|---|---|
| circle_packing_rect | OK | 5 | 35 | 27 | Glue and reference from pilot `oe_cpr_post` (same evaluator file). Predicate uses the axis-parallel bounding rectangle, as in the pilot. Invariances: permute, reflect (x -> -x). `initial` = initial program output (all zeros, score 0). Record: sum of radii 2.365 as published in the notebook (B.13; truncated, BENCHMARK 2.36583 would round to 2.366), so the mapped record (0.99965 +- 2.1e-4) sits just below score 1. |
| erdos_min_overlap | OK | 5 | 35 | 26 | Glue and reference from pilot `oe_erdos_post` (same evaluator file). Record: c5 = 0.380924 via map (the pilot copy keeps "1.0000"). |
| first_autocorr_ineq | OK | 6 | 38 | 25 | Pilot glue/reference (`oe_c1_post`, same evaluator file) plus a `positive_integral` predicate (C1 is undefined for f = 0). Invariance: scale (exponent 0). |
| second_autocorr_ineq | OK | 10 | 38 | 32 | c2 is reported by the candidate but not used by this scorer; still a claimed field. Glue integrates the piecewise-linear f*f exactly. Record: c2 = 0.8962 via map. Reference: a simple quadratic bump, 50 steps. |
| third_autocorr_ineq | OK | 5 | 38 | 25 | Pilot glue/reference (`oe_c3_post`, same evaluator file) plus `nonzero_integral`. Invariances: scale (0), negate. |
| uncertainty_ineq | OK | 25 | 39 | 111 | Claimed c4_bound and r_max recomputed independently (exact rationals, Hermite recursion, bisection). Predicate: P/x^2 has a positive sign change. m (number of coefficients) is not fixed by the problem. Reference: 3 coefficients from a short Nelder-Mead on the glue's own c4 (C4 = 0.35214, scorer accepted the claimed values). Record: c4 = 0.3216 (notebook; Laguerre formulation; the Hermite formulation this evaluator uses is published at 0.3521; DM page 11 gives 0.321591), via map to BENCHMARK 0.3215872.../c4. Initial program needs jax: no `initial`. timeout_s 120 (sympy root isolation). |
| heilbronn_triangle | OK | 12 | 36 | 41 | Exact containment in the triangle with vertices (0,0), (1,0), (1/2, sqrt 3/2) (sqrt 3 handled by squaring). Invariances: permute, reflect about x = 1/2. Reference: 11 points on a circle around the centroid. `initial` = initial program (all zeros; valid, score 0). Record: 0.0365 via map. |
| heilbronn_convex_13 | OK | 8 | 38 | 27 | Valid = 13 finite points, not all collinear (hull area > 0). Affine-invariant score: permute, translate, rotate, scale (0), reflect. Reference: regular 13-gon. `initial` = initial program (seeded random). Record: 0.0309 via map. |
| heilbronn_convex_14 | OK | 2 | 38 | 27 | As 13. Record: 0.0278 via map. |
| hexagon_packing_11 | OK | 20 | 41 | 75 | Fields inner [11,3], outer [3], side. Predicate in 60-digit mpmath (vertices are irrational); gaps below 1e-50 count as touching. Invariance: permute (inner). Reference = `initial` = initial program output (valid, side 8). Record: outer side 3.931 via map. |
| hexagon_packing_12 | OK | 3 | 41 | 75 | As 11; record: outer side 3.942 via map. |
| kissing_number | OK | 12 | 34 | 32 | Points in Z^11, 0 excluded, max norm <= min distance; exact integers. Predicate judged on rounded points so fractional entries are only an `integral` (type) violation. Invariances: permute, negate. Reference: the 220 D11 roots; `initial` = initial program (2 points). Record "1" (593 points, exact). |
| matmul | OK | 20 | 46 | 83 | `template` harness with an adapter template: run() must return a nested ((U, V, W), n, m, p, loss, rank), which a flat loader cannot. n, m, p, loss, rank are claimed (recomputed from the factors). Exact-decomposition predicate in rationals, tolerance 0 (the problem demands exact equality). Factors typed real (the problem allows complex). Reference: rank-40 standard algorithm. Record "1" (rank 32). Initial program needs jax. |
| minimizing_max_min_dist_2 | OK | 8 | 38 | 4 | 16 distinct points in R^2; closed rules only. Invariances: permute, translate, rotate, scale (0), reflect. Reference: 4x4 grid; `initial` = initial program (seed 42). Record: ratio^2 = 12.889266112 via map (glue holds only the map). |
| minimizing_max_min_dist_3 | OK | 2 | 38 | 4 | As 2, 14 points in R^3. Reference: cube vertices plus 6 face points. Record: ratio^2 = 4.165849767 via map. |
| sums_diffs_finite_sets | OK | 8 | 38 | 33 | U typed int_set: integral, distinct, >= 0, contains 0 and a positive element (predicate). Claimed c6 recomputed with Python sets. Reference {0,1,3,7,12,20}. Initial program needs jax. |
| circle_packing | OK | 15 | 41 | 27 | Evaluator runs the candidate in a subprocess (timeout_s 120). Rejection is `validity == 0.0` with combined_score 0.0, but 0.0 is also a legitimate score, so `glue.compose` adds an `error` key on validity 0.0 (format gap: no key-equals reject for in-process kinds). Closed rules (in_box with margins, pairwise_separation); invariance: dihedral order 4 about (1/2, 1/2) on centers (permute not declared: centers and radii are separate fields). Reference: 5x5 grid r = 0.0999 plus one r = 0.04. Record: sum of radii 2.635 via map. The initial program's output overlaps by ~1e-17 in exact arithmetic, so it is not a strictly valid `initial`; `best_program.py` is a ~23 s scipy optimisation run, not executed, no `claimed_best`. TARGET_VALUE env override assumed unset. |
| circle_packing_with_artifacts | OK | 5 | 41 | 31 | As circle_packing; the evaluator returns an EvaluationResult: vendored `openevolve/evaluation_result.py` plus a stub `openevolve/__init__.py`, and `compose` unwraps `.metrics`. |
| function_minimization | OK | 15 | 33 | 22 | `template` harness over the vendored initial_program.py (search_algorithm() replaced; the fixed run_search() outside the block is kept). Construction = point (x, y), finite; claimed `value` = f(x, y). EvaluationResult handled as above. No invariances. No record (the README gives only an approximate minimum); direction maximize. Reference: the README's approximate minimiser (-1.704, 0.678). Initial program is unseeded random search: no `initial`. |

## Choices worth stating

- **Direction.** Every scorer outputs `combined_score`, larger is better (the README states all problems
  were turned into maximisation); the search loops maximise it too. `direction: maximize` everywhere.
- **Records** (revised after review). Each record is the value exactly as published, in its own quantity,
  with a glue `maps` entry giving the scorer's combined_score for a construction with that quantity
  (`{quantity, value, map}`, spec 6.4), so the published resolution is carried through the map. Values are
  from the google-deepmind/alphaevolve_results mathematical_results.ipynb markdown (B.1-B.13) as cited in each
  `source`. The `quantity` key is a label (the engine does not look it up in glue). Integer records (kissing
  593 points, matmul rank 32) keep the plain form "1" (exact). function_minimization has no record.
- **Claimed fields.** Every number the candidate reports about itself is `claimed` with a glue
  recomputation, even where the current scorer ignores or recomputes it (second_autocorr c2, erdos c5,
  circle_packing sum_radii, matmul loss). `n`/`n_points` remain `derived: len(...)` as in the pilot.

## Licence

Vendored files (`evaluator.py`, `openevolve/evaluation_result.py`, `function_minimization/program_template.py`)
are from OpenEvolve (https://github.com/algorithmicsuperintelligence/openevolve), Apache-2.0, unmodified below
their provenance header. Glue files, adapter templates, the `openevolve/__init__.py` stubs and the .npz
references were written for these contracts.
