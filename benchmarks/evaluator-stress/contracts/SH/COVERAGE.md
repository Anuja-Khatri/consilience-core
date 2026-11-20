# Coverage — SH (ShinkaEvolve @ 1bf7113e97dd89349f1a337babe48d98c92d7e10)

| slug | status | minutes | contract lines | glue lines | notes |
|---|---|---|---|---|---|
| circle_packing | OK | 22 | 78 | 7 | Harness: `cli_json`, `evaluate.py --program_path P --results_dir D` → `D/metrics.json` (`combined_score`), reject file `D/correct.json` with `correct == false`. `reported_sum` is a claimed field (recomputed sum of radii). The evaluator imports `shinka.core.run_shinka_eval`, but the published `shinka/__init__.py` and `shinka/core/__init__.py` import the whole LLM stack (`dotenv`, clients). The argv shim therefore registers empty `shinka`, `shinka.core` and `shinka.utils` packages and loads the vendored, unmodified `wrap_eval.py` and `eval_stop.py`. Format gap: these two files are not in the contract's file hashes (only evaluator, glue, template and npz are). Validity uses the closed library on split `centers`/`radii` (in_box with margin, pairwise_separation, radii ≥ 0). Invariance: dihedral on centres about (1/2, 1/2); joint permutation is not expressible across two fields. Record: AlphaEvolve B.12 2.635 (the Shinka README states no record). Reference: B.12 construction 1. |
| fortran_heat_diffusion | out_of_scope | 1 | – | – | Compiled-language candidate (Fortran) (spec §4.1). |
| go_collatz_steps | out_of_scope | 1 | – | – | Go program scored on fixed query lists: an algorithm on hidden inputs, in a compiled language. |
| julia_prime_counting | out_of_scope | 1 | – | – | Julia program scored on queries: an algorithm on hidden inputs. |
| wolfram_gcd_sum | out_of_scope | 1 | – | – | Wolfram program scored on speed for a fixed answer: an algorithm, not a construction. |
| rtllm | out_of_scope | 1 | – | – | Verilog PPA optimisation, scored by a hardware toolchain: an algorithm on hidden inputs. |
| game_2048 | out_of_scope | 1 | – | – | A 2048-playing policy scored in an environment: an algorithm on hidden inputs. |
| sine_approx_headless | out_of_scope | 1 | – | – | The input is a function approximating sin(x): a function input (spec §4.2). |
| novelty_generator | out_of_scope | 1 | – | – | Scored by LLM judges: a remote evaluator (spec §4.1). |

Total: 1 OK, 8 out_of_scope.
