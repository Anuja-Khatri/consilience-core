# Coverage — CE (CodeEvolve @ a43fd88270e5a38f1e0dda1e7d834f7d7b58f85b)

Harness for every OK row: `cli_json`, `python evaluate.py {program} {outdir}/results.json` (CodeEvolve's own call), score key `benchmark_ratio` (the `fitness_key` in `configs/templates/*.yaml`). No reject keys or values: a failure raises, so no result file is written. Records are the README's "Benchmark" line (the problem page), mapped by glue into `benchmark_ratio`, except where noted. Directions: the scorer outputs `benchmark_ratio`, which CodeEvolve maximises; every contract says `maximize`, and the scorer and search loop agree.

| slug | status | minutes | contract lines | glue lines | notes |
|---|---|---|---|---|---|
| first_autocorr_ineq | OK | 14 | 49 | 15 | The evaluator requires a Python `list`. The argv is an inline shim that converts the returned ndarray with `[float(x) ...]` before running the unmodified evaluator (format gap: `cli_json` has no to-program conversion). The validity range [0, 1000] is taken from the README Interface ("heights are clamped to [0, 1000]"). Its "sum > 0.01" is not a validity rule; only f ≠ 0 is required. Bound from C1 ≥ 1.28. Reference: AlphaEvolve B.1 (600 steps). |
| second_autocorr_ineq | OK | 8 | 30 | 15 | The record is the README's 0.962 as published. AlphaEvolve's B.2 text states 0.8962, so the reference (B.2) scores 0.93. The bound C2 ≤ 1 (Hölder) is rounded up in score units. |
| heilbronn_triangle_11 | OK | 12 | 40 | 27 | "Inside" means the closed triangle (README inequalities, problem B.9 "on or inside"). The check is exact, using squared comparisons for √3. reference = B.9 points with x moved by one ulp where a point is outside in exact arithmetic. claimed_best = B.9 as shipped. Invariances: permute, and reflect about x = 1/2. |
| heilbronn_convex_13 | OK | 6 | 37 | 22 | Validity: finite, shape, and a hull of positive area (README). Invariances: permute, translate, rotate, scale^0, reflect (the README states scale and translation invariance). Reference: B.10 construction 1. |
| heilbronn_convex_14 | OK | 3 | 37 | 22 | As for n=13. Reference: B.10 construction 2. |
| kissing_number_11 | OK | 8 | 29 | 37 | Exact integer predicate (README conditions 1–2; dimension 11 checked in the predicate, because the number of rows m is free). Invariances: permute, negate. Record 593 → ratio 1 (r = 0). Reference: B.11 (593 vectors). Timeout 180 s. |
| minimizing_max_min_dist_2d_16 | OK | 8 | 40 | 5 | The README's text writes the benchmark as 1/x², but the evaluator's BENCHMARK = 1/x and its metric is (d_min/d_max)². The record is AlphaEvolve's published ratio² 12.889266112 (B.8), mapped by glue. Validity requires distinct points. Reference: B.8 construction 1. |
| minimizing_max_min_dist_3d_14 | OK | 3 | 40 | 5 | As for 2d. Record 4.165849767. Reference: B.8 construction 2. |
| circle_packing_rect_21 | OK | 6 | 33 | 28 | Exact predicate: r ≥ 0, disjoint, bounding-box w + h ≤ 2. Only `permute` is declared, because transforms act on all columns of the (21, 3) field and the radius column must not move. Reference: B.13. |
| circle_packing_square_26 | OK | 5 | 33 | 25 | Exact predicate for the unit square. Only `permute` is declared (same reason). Reference: B.12 construction 1. |
| circle_packing_square_32 | OK | 2 | 33 | 25 | As for 26. Reference: B.12 construction 2. |
| hexagon_packing_11 | OK | 14 | 47 | 64 | Fields `inner` (11, 3), `outer` (cx, cy, angle), `side`. The predicate checks disjoint interiors (separating axes) and containment in the closed outer hexagon, with mpmath at 60 digits: rotation by degrees is not rational, so this check is not exact. Record README 1/3.930092 → s = 3.930092. Reference: B.7 construction 1. |
| hexagon_packing_12 | OK | 3 | 47 | 64 | As for 11. Reference: B.7 construction 2. |
| eoh-problems/bp_online | out_of_scope | 1 | – | – | Online bin-packing heuristic scored on generated instances: an algorithm on hidden inputs (spec §4.1). |
| eoh-problems/fssp_gls | out_of_scope | 1 | – | – | Flow-shop guided local search heuristic: an algorithm on hidden inputs (spec §4.1). |
| eoh-problems/tsp_gls | out_of_scope | 1 | – | – | TSP guided local search heuristic: an algorithm on hidden inputs (spec §4.1). |
| templates/python | skipped | 1 | – | – | Project template, not a problem. |

Total: 13 OK, 3 out_of_scope, 1 skipped.
