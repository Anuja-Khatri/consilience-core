# Third-party code in `contracts/CE/` (Apache License 2.0)

- `*/evaluate.py`: from CodeEvolve (https://github.com/inter-co/science-codeevolve) @ a43fd88270e5a38f1e0dda1e7d834f7d7b58f85b, Apache-2.0. Path in each file's header; unmodified below the header.
- `*/reference.npz`: AlphaEvolve's published constructions from https://github.com/google-deepmind/alphaevolve_results @ 4226acbf237ff9ad10ba7673a2af127a2d8a5971 (`mathematical_results.ipynb`), attributed to Google DeepMind (code Apache-2.0, other material CC-BY-4.0). The cell is named in each contract's header comment. `heilbronn_triangle_11/reference.npz` moves single coordinates by one ulp (see its contract).
- `contract.yaml` and `glue.py` are written for this benchmark (MIT, as the rest of consilience-core).

Statements about these files concern the published code at the stated commit only.
