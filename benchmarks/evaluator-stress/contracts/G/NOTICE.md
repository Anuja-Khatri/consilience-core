# Third-party code in `contracts/G/` (Apache License 2.0)

- `circle_packing/evaluate.py`, `circle_packing/program.py`, `circle_packing/alpha_evolve/models.py`: from https://github.com/Google-Cloud-AI/alphaevolve-on-googlecloud @ 019a2d2688b260a8e8a5ff62ad85b92710a0e497 (`examples/circle_packing/src/evaluate.py`, `examples/circle_packing/src/program.py`, `src/alpha_evolve/models.py`), Apache-2.0, unmodified below the header.
- `circle_packing/sdk_adapter.py` is NOT vendored: it is contract glue written for this benchmark (it wraps the candidate file in the SDK envelope).
- `circle_packing/reference.npz`: AlphaEvolve's n=26 packing from https://github.com/google-deepmind/alphaevolve_results @ 4226acb (B.12, cell 118), attributed to Google DeepMind.
