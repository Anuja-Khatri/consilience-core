# Third-party code in `pilot/` (Apache License 2.0)

- `oe_*/evaluator.py`: from OpenEvolve (https://github.com/algorithmicsuperintelligence/openevolve), Apache-2.0.
  - The commit is in each file's header.
  - Unmodified below the header.
- `dm_*/scorer.py`: scoring functions copied verbatim from https://github.com/google-deepmind/alphaevolve_repository_of_problems at 8f447457957deac61e28bf1676746f0753b3b2f8.
  - Code is Apache-2.0; other material is CC-BY-4.0.
  - Only the scoring cells were copied; imports were added.
- `dm_equidistant/{reference,claimed_best}.npz`: AlphaEvolve's shipped construction (`myarr4`) from the equidistant notebook (CC-BY-4.0, attributed to Google DeepMind).

The full licence texts are in the source repositories. The Apache-2.0 text is at https://www.apache.org/licenses/LICENSE-2.0.

The rest of consilience-core is MIT. These folders keep their own licences.

**Claims about these files.** Any statement concerns the published code at the stated commit only. It says nothing about the authors' internal systems or results.
