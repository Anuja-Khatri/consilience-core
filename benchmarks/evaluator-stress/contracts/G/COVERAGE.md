# Coverage — G (alphaevolve-on-googlecloud @ 019a2d2688b260a8e8a5ff62ad85b92710a0e497)

| slug | status | minutes | contract lines | glue lines | notes |
|---|---|---|---|---|---|
| circle_packing | OK | 25 | 60 | 7 (+16 adapter) | Harness `template`: `program_template` = the example's `program.py`, markers `# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END`. The validity code outside the block (`_circles_overlap`, `evaluate`) is kept. `evaluate.py` `exec`s the file and calls its `evaluate({"n": 26})`. Score key `scores.scores[metric=sum_of_radii].score`; reject value −1e12 (the evaluator's failure sentinel; −inf is rejected as non-finite anyway). Format gap: the `template` kind calls `entry(path)`, but the scorer takes the SDK envelope (`sdk_dict`). The contract's evaluator is therefore a 16-line unvendored `sdk_adapter.py` that builds the envelope and calls the vendored, unmodified `circle_packing_evaluation`; the vendored `evaluate.py` and `alpha_evolve/models.py` are listed in `harness.extra_files`, so they are hashed. `reported_sum` is a claimed field: the template ignores it, but the candidate reports it. Validity is taken from `instructions.md` and is the same as SH. Record: AlphaEvolve B.12 2.635. Reference: B.12 construction 1. |
| tsp | out_of_scope | 1 | – | – | Tour-construction heuristic scored on random instances: an algorithm on hidden inputs. |
| signal_processing | out_of_scope | 1 | – | – | Filter algorithm scored on test signals: an algorithm on hidden inputs. |
| adaptive_sort | out_of_scope | 1 | – | – | Rust sort compiled and timed in a Cloud Function: compiled language and remote evaluator. |
| adaptive_sort_cpp | out_of_scope | 1 | – | – | C++ variant of adaptive_sort: compiled language and remote evaluator. |
| llm_fine_tuning | out_of_scope | 1 | – | – | Hyperparameters scored by remote fine-tuning runs: a remote evaluator. |
| skills/alpha_evolve_experiment_design/examples/circle_packing | skipped | 1 | – | – | A documentation example inside the skills folder. It is not in the spec §10.1 G set (`examples/circle_packing`). |

Total: 1 OK, 5 out_of_scope, 1 skipped.
