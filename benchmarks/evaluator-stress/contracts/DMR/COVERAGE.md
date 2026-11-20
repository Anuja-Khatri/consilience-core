# Coverage — DMR (alphaevolve_results @ 4226acbf237ff9ad10ba7673a2af127a2d8a5971)

Scope (spec §10.1): the results-repo verifiers named in issues #11 and #12. Both scorers are whole notebook cells copied verbatim. The verifiers raise `AssertionError` on failure and return None otherwise, so glue `compose` gives the score as the notebook's next cell computes it (sum of radii; outer side length).

| slug | status | minutes | contract lines | glue lines | notes |
|---|---|---|---|---|---|
| dmr11_circles | OK | 14 | 46 | 9 | Label DMR-11 (pre; no fix known). `verify_circles` (cell 116, B.12 unit square, n = 26). Fields `centers`/`radii` (glue stacks them into the notebook's (n, 3) array). Validity uses the closed library (radii ≥ 0, in_box with margin, pairwise_separation), from the B.12 text (cell 115). Invariance: dihedral about (1/2, 1/2). Record 2.635. Reference: construction 1 (cell 118). The issue's follow-up comment also names `verify_circles_disjoint` (B.13, cell 126); it is not contracted here. |
| dmr12_hexagon | OK | 16 | 42 | 65 | Label DMR-12 pre. `verify_construction` and its helpers (cell 86, B.7, n = 11). Fields `inner` (11, 3), `center`, `side`, `angle`. mpmath predicate as in CE hexagon. Direction minimise (outer side). Record 3.931 (B.7 text). Reference: construction 1 (cell 88). The post version is `LABELS/dmr12_hexagon_post`. |

Total: 2 OK.
