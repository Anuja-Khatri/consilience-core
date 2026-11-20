# Coverage log, DM set, part A (problems <= 36)

Written 20 Nov 2026 under CONTRACT_AUTHORING.md. Every `OK` row passes `validate_contract.py`. All contracts have `contract_author: model`.
No `consilience stress` run, no attack and no bug hunting was done. The only scorer calls were:
- the extraction test on shipped constructions;
- the validation calls on reference, initial and claimed_best.

Source: google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8. Cell numbers are code-cell indices (0-based, markdown cells not counted).

## Contracts

| slug | status | minutes | contract lines | glue lines | notes |
|---|---|---|---|---|---|
| finite_field_kakeya_problem | OK | 20 | 43 | 34 | Problem 1, 3-D cell 3 `calculate_score`, fixed p=7, d=3. Kakeya property is a glue predicate. The record (-128) is the size of the shipped cell-0 construction; the page gives no number. Only `permute` declared: affine maps mod p leave [0,p) and cannot be expressed. |
| finite_field_nikodym_problem | OK | 15 | 48 | 33 | Problem 1, 3-D cell 9, fixed p=5. At p=5 the initial program (cell 7, size 70) beats AlphaEvolve's program (cell 8, size 82, tuned for p>10). So reference = initial = 70, and claimed_best = AE's 82. Record -70. |
| autocorrelation_problems_first | OK | 15 | 47 | 17 | Problem 2, final `evaluate_sequence` (cell 6). Reference = shipped 1.5032 construction (cell 24). Record 1.5029 (page, Yuksekgonul et al.). Proven bound 1.2748. Reversing the sequence is a true invariance but cannot be declared (see the report). |
| autocorrelation_problems_first_v0 | OK | 3 | 49 | 17 | Cell 0: the notebook's first, naive version, which the notebook text itself supersedes. Same contract as `_first`. |
| autocorrelation_problems_first_v1 | OK | 3 | 48 | 17 | Cell 2 `evaluate_sequence_1` (second version, superseded). |
| autocorrelation_problems_first_v2 | OK | 3 | 48 | 17 | Cell 4 `evaluate_sequence_2` (third version, superseded). |
| autocorrelation_problems_problem6 | OK | 8 | 42 | 15 | `problem_6.ipynb` in the same folder, cell 2 `evaluate_autocorrelation`. Validity comes from that notebook's prompt (non-negative heights; unit L1 treated as normalisation). Scorer and search loop agree on maximize (the score is negated). No shipped construction: the reference is uniform 1/5 heights. No record. |
| difference_bases | OK | 8 | 43 | 10 | Re-vendored with the rule header; body identical to pilot/dm_diffbases. Reference is now the shipped L (cell 0, \|L\|=360). **Direction disagreement:** the problem minimises C(n), but the search loops in cells 1 and 2 keep the larger `get_score`. Chose minimize, following the problem statement and the shipped construction. The record 2.6390 is the shipped construction's score (the problem page states no number, contrary to the pilot's source note). |
| sendov_conjecture | OK | 12 | 50 | 7 | `evaluate_sendov_conjecture_h`, the function `evaluate()` scores with. Threshold 1. The shipped best_roots have 11 roots up to 5.4e-5 outside the disk: reference = those roots scaled onto the circle, claimed_best = raw shipped. |
| schmeisser_conjecture | OK | 5 | 44 | 7 | `evaluate_construction_h` (used by `evaluate()`). Threshold 1. Reference = initial program's roots. |
| borcea_conjecture | OK | 6 | 43 | 18 | `evaluate_sendov_conjecture_h` in the Borcea notebook (used by `evaluate()`), p=1. Mean-modulus predicate. Threshold 1: Borcea's conjecture, not stated on the page. Reference = initial roots. |
| smale_problem | OK | 6 | 36 | 8 | `evaluate_smale_conjecture_h(roots, 91)` as in `evaluate()`. No record; proven bound 4 (Smale 1981). Reference = initial roots. |
| de_bruijn_sharma_problem | OK | 12 | 50 | 27 | `calculate_area_score`, n fixed to 5. Zero-sum is an equality predicate (tolerance 1e-12). Reference = {z^5-1, z^5-z}. No record. |
| crouzeix_conjecture | OK | 12 | 59 | 23 | `evaluate_construction(A, p, 10000)` as in `evaluate()`. Threshold 2; proven bound 1+sqrt2. Reference = evolved program's block-nilpotent start (ratio exactly 2); initial = (I_15, 1+2z+(3-i)z^2). About 4 s per call. |
| sidorenko_conjecture | OK | 10 | 50 | 18 | `score_weighted_h` (used by `evaluate()`). 30x30 from the prompt. Threshold 0. Vertex relabelling (simultaneous row/column permutation) is a true invariance but cannot be declared. Reference = fixed random symmetric 0/1 matrix. |
| prime_number_theorem | OK | 15 | 60 | 43 | `evaluate_partial_function(f, 10_000_000)`. Unseeded sampling, so non-deterministic. The validity predicate checks the floor-sum condition exactly over one period lcm(keys). It raises (= cannot judge = invalid) when the period is above 1e7. Reference = Chebyshev's {1,2,3,5,30} function. Bound 1. No record. Keys and values are separate fields, so no permutation invariance. |
| flat_polynomials_c_plus | OK | 8 | 42 | 6 | `get_c_plus_score`, n=50 (caller-enforced length). Record = stored score for n=50. |
| flat_polynomials_c_minus | OK | 7 | 42 | 6 | `get_c_minus_score`, n=50. Record = stored score for n=50. |
| block_stacking_problem | OK | 15 | 57 | 39 | `get_positions_score`, n=20, caller-enforced length (`get_score_of_algorithm` checks it). The problem's strict inequalities are checked exactly. Reference = AE formula x (1-1e-9); claimed_best = exact formula, which meets the inequalities with equality, so it is invalid. Record and bound = H_20/2. |
| furstenberg_sarkozy_problem | OK | 15 | 65 | 42 | `get_score` (k=2). Construction (A, m). The record is "12 elements mod 205" via a glue map. No list is shipped, so the reference is a 12-element square-difference-free subset of Z/205 found by exact max-clique search. |
| spherical_t_designs | OK | 12 | 56 | 8 | (d,t,N)=(2,15,120), shipped design. Threshold = the notebook's "error < 1e-8" criterion; the cell writes the test as `score < 1e-8`. Proven bound 0. |
| thomson_problem | OK | 8 | 48 | 6 | N=282 (caller-enforced). Reference = shipped points renormalised; claimed_best = raw shipped (8-decimal print, off the sphere by up to 7e-9). No record: none stated. |
| tammes_problem | OK | 8 | 57 | 6 | N=12 (caller-enforced). Record and bound = icosahedron (proven optimal). |
| packing_unit_cubes | OK | 18 | 49 | 57 | Cell 2 `calculate_packing_score_cubes_3d(P, 11, return_adjusted_coordinates=False)`. The scorer first moves the first 8 cubes to the bounding-box corners. Disjoint interiors is a glue SAT predicate (float, tolerance 0). `permute` is declared because the true score of the given placement is order-free. Record -2.894531 (cell 0 prints 6 decimals; no stored output). |
| packing_circles_max_sum_of_radii_square | OK | 12 | 63 | 8 | n=26. The shipped radii_26 has 3 pairs overlapping by ulps in exact arithmetic. Reference = radii x (1-1e-12); claimed_best = shipped. Record 2.635 from the notebook text (recomputed 2.63598). |
| packing_circles_max_sum_of_radii_rectangle | OK | 10 | 74 | 32 | n=21, perimeter 4 (equality predicate, 1e-12). Shipped construction is valid exactly. Record 2.365 (text). |
| sphere_packing_uncertainty_principles_uncertainty | OK | 12 | 62 | 24 | Cell 5 (problem 11). Record C=0.3102 via map score = -sqrt(C). Bound -0.45 (C >= 0.2025). Reference z_6 (about 1 s per call; z_8 takes about 6 s). |
| sphere_packing_uncertainty_principles_lp | OK | 10 | 51 | 18 | Cell 1, (m,n)=(6,25). Scorer, search loop and prompt all maximise r ("largest possible value of r"). Problem 13 asks for upper bounds on a quantity that grows with r; we followed the scorer, prompt and search, and flag this here. No record. |
| kakeya_needle_2d_triangles | OK | 12 | 40 | 11 | Cell 2 `get_score_shapely`. The glue builds the triangles exactly as the problem (and `get_all_triangle_vertices`) define them. n=32 is caller-enforced. Reference = AE `suggested_positions_32`; initial = Keich. No record: the notebook states only Keich's areas. |
| kakeya_needle_2d_parallelograms | OK | 6 | 40 | 18 | As triangles, with parallelograms. The shipped `ae_para_32` has a larger area (0.2884) than Keich's (0.2746); it may have been optimised for S^P rather than area. Kept as reference because it is the shipped construction. No record. |

## Scoring functions without a contract

| slug | status | minutes | contract lines | glue lines | notes |
|---|---|---|---|---|---|
| autocorrelation_problems_second (problem 3) | skipped | 3 | 0 | 0 | Cell 43 computes the C2 bound in top-level script code; there is no scoring function to call. |
| autocorrelation_problems toy `get_score(number)` (cells 26-41) | out_of_scope | 3 | 0 | 0 | Toy -abs(5-x). The notebook uses these cells to show code injection into the evolve block. The attack is on the program, not on a construction. |
| autocorrelation_difference_bases | out_of_scope | 3 | 0 | 0 | Callable input: `score_all_function_shifts(f)` over `list_of_functions()` (scipy quad). |
| classical_inequalities | out_of_scope | 3 | 0 | 0 | Callable input: `get_candidate_score(f, r1, r2, j, p)` takes a function f (problems 14-18). |
| arithmetic_kakeya_conjecture | unrunnable | 3 | 0 | 0 | Confirmed: verification cell 0 fails to parse. Line 242 `) -> tuple[...]` has no `def evaluate(` (SyntaxError: unmatched ')'). |
| kakeya_needle_3d | unrunnable | 3 | 0 | 0 | `get_score` (cell 3) needs jax (not installed) and runs 5000 Monte Carlo trials of 5e6 points per call. Cell 0 is `!pip install` shell magic. |
| ovals_problem | unrunnable | 4 | 0 | 0 | Scoring cell 1 (`get_score(x1, x2, phi)`) imports jax, which is not installed. `evaluate_curve` itself uses only numpy and scipy. Cell 0 (initial-program examples) has a syntax error (`if curr_score  best_score:`). A contract is feasible if jax becomes available. |
| finite_field_kakeya_problem 4-D/5-D (cells 8, 12) | skipped | 1 | 0 | 0 | Same scorer family as cell 3; only 3-D contracted (time-box). |
| finite_field_nikodym_problem 2-D (cells 0, 6) | skipped | 1 | 0 | 0 | F_{q^2}^2 scorer with pair encoding; not contracted (time-box). |
| sendov / schmeisser / borcea visible scorers | skipped | 1 | 0 | 0 | `evaluate_sendov_conjecture` and `evaluate_construction` are the prompt-facing twins of the `_h` functions `evaluate()` uses (e.g. n<15 returns 0). Not contracted separately. |
| smale_problem `evaluate_smale_conjecture` (numba, grid 10) | skipped | 1 | 0 | 0 | Search-loop twin of the contracted `_h` (grid 91). |
| crouzeix_conjecture `evaluate_construction_h` | skipped | 1 | 0 | 0 | Hidden variant; `evaluate()` uses `evaluate_construction`. |
| sidorenko_conjecture `score_weighted` | skipped | 1 | 0 | 0 | Prompt-facing twin of the contracted `score_weighted_h`. |
| kakeya_needle_2d `get_score_no_shapely`, `get_positions_area` | skipped | 1 | 0 | 0 | Grid-sampling variant, and the cell-7 helper; the shapely scorer is contracted. |
| packing_unit_cubes `analyze_cube_packing` (cell 0) | out_of_scope | 1 | 0 | 0 | Prints a report and returns None. |
| block_stacking_problem `get_score_of_algorithm` | out_of_scope | 1 | 0 | 0 | Callable input (`solve_fn`). |

Totals: 30 OK, 0 failing validation; 1 skipped no-function; 5 out_of_scope; 3 unrunnable; 7 skipped variant rows.
