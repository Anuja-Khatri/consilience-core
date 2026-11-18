# Candidate nanopublications: prepared, NOT published

> **v1 format (16-17 Nov 2026), not rebuilt for v2.** These candidates were prepared with
> the v1 exporter: claims identified by GitHub line ranges, conditions as JSON strings, the
> v1 "testable disagreement" template. v2 (see [`PILOT.md`](PILOT.md), "Changes from v1")
> changed all three after Tobias Kuhn's review, so these files are kept only as a record of
> what was considered. `scripts/build_ledger_candidates.py` and
> `scripts/build_theory_candidates.py` were written against v1 and do not run against the
> v2 exporter: under v2 a refusal needs the claim IRIs of published claim cards
> (`pilot/claims.json`), so any rebuild publishes the claim cards first.

Nothing in `candidates/` has been signed or sent to any server, test or live. The TriG
files are unsigned and use the temporary nanopub namespace. They cite the templates and
the agent introduced on the Knowledge Pixels **test** registry; publishing on the live
network would first need the templates and the agent introduction published there, and
then a rebuild.

This branch (`kp-candidates`) prepares two of three candidate sets. The third (data-quality
findings on a public materials dataset) is held privately until the dataset's maintainers
have been told, and is not in this repository.

## 1. The claims ledger (`candidates/ledger/`)

Source: [consilience-ledger](https://github.com/Anuja-Khatri/consilience-ledger) at commit
`7c1f9235b582666403537dd929c844e4b2dfc8cf` (branch `wp1-public-truth`), the same pinned
commit as the pilot. Every record links to its exact lines at that commit and carries its
content hash; the build stops if the ledger hash does not reproduce. Built by
`scripts/build_ledger_candidates.py` (run with `PYTHONHASHSEED=0` for byte-identical
output). The ten pilot records come out identical to `pilot/records/`.

| Template | Prepared | Recommended (tier A) | Not recommended (tier B) |
|---|---|---|---|
| claim card | 33 | 33 | 0 |
| comparison refused | 561 | 87 | 474 |
| **total** | **594** | **120** | **474** |

One more claim card (`2609.30133__024`) cannot be exported: it states an uncertainty range
(0.3 to 0.7 umol/cm^2), and claim-card template v0 has no field for one. It is listed in
`candidates/ledger/excluded.json`. The ledger at this commit has no graded correspondences
and no disagreements (forks), so there are none to prepare. Its nine `verdicts.json`
records compare a claim with measured data, not two claims, so the refusal template does
not fit them.

How distinct they are:

- **Claim cards (33):** all distinct claims, from 24 distinct source sentences (some
  sentences state two numbers, e.g. two catalysts at once).
- **Refusals on the same quantity (46, tier A):** two claims about the same quantity that
  cannot be compared because a condition is missing or differs. 36 of them are about
  overpotential. 27 share one reason (electrolyte, temperature and iR correction not
  stated), so they read alike, but each is a different pair of claims. Three are the most
  informative: the current density differs (rule CR2).
- **Refusals on different quantities that share a unit (41, tier A):** for example, two
  numbers in hours that measure different things. A reader could easily line these up by
  mistake, which is why the refusal is worth stating.
- **Refusals on different quantities in different units (474, tier B):** true but
  obvious (for example, an overpotential in volts against a palladium retention in
  percent). They cover 153 different quantity pairings. Prepared for completeness; we
  recommend not publishing them.

Examples, as they would read:

- *Claim card:* "Claim card 2609.30133__005: InMnPdOx, Pd_retention 96.0 %", with the
  source sentence "From XRF results, InMnPdOx retains 96% of its Pd after 1,000 h, ..." and
  a link to arXiv:2609.30133.
- *Refused, same quantity:* "Comparison refused, ref40_peng2023__011 vs
  ref40_peng2023__021: current_density differs (rule CR2); not stated: electrolyte,
  temperature, ir_correction." Both claims give a durability for Pd-55 (more than 40 h at
  100 mA/cm^2; up to 500 h, which the claim card records at 10 mA/cm^2).
- *Refused, same unit, different quantity:* "Comparison refused, 2609.30133__006 vs
  ref40_peng2023__002: different quantity axes (stability_lifetime vs
  operational_stability_duration)." One is a screening lifetime under 4 h, the other 500 h
  of operation; both are hours, but they are not the same measurement.

A refusal records what the two claim cards, as extracted from their source sentences,
allow under the ledger's rule set `comparability-v0.1`. It is not a judgement of either
paper.

Files: `records/` (record envelopes, the input to `consilience export --nanopub`),
`trig/` (unsigned TriG), `index.json` (one row per candidate with its tier and grouping),
`excluded.json`.

## 2. Cross-theory comparisons, consciousness science (`candidates/theories/`)

> **Update (17 Nov 2026): published on the TEST registry.** The demo's results are now pinned
> in the public engine repository (theconsilience-engine, `results/demo/`, commit
> `96ba4e435bd13718d36435cc3436d938d2d1f894`, with a SHA-256 manifest). From those receipts
> the 8 testable disagreements were published as 8 records (the template takes one claim
> pair per record), together with 11 theory claim cards under a new *theory claim card*
> template. See the COGITATE section of `PILOT.md` and `pilot/theories/`. The text below is
> the preparation note as it was written before that; its blocker is resolved.

Source: the public demo at https://consilience-demo.netlify.app, whose results are JSON
files under `/results/`, retrieved 2026-11-17 (SHA-256 of each file in
`candidates/theories/index.json`). The demo was regenerated from its corpus by its
pipeline (`run_manifest.json`: corpus `ccc6db4ceb29`, holdout check PASS); it is not a
synthetic demo. Built by `scripts/build_theory_candidates.py`.

| Template | Candidates | Not eligible |
|---|---|---|
| this disagreement is testable now with instrument Y | 8 | 16 |
| claim A corresponds to claim B at grade X | 0 | 37 |

- **Testable disagreements, 8 candidates**, all IIT against GNWT, in three distinct
  disagreements: where consciousness is located (4 claim pairs, testable with regional
  decoding), its time course (3 pairs, ignition signature and temporal generalisation),
  and connectivity (1 pair, connectivity metrics).
- **Not eligible:** 4 IIT x GNWT disagreements the demo calls decidable now but names no
  shared observable for (the disagreement is about what to measure); 2 IIT x GNWT and 10
  IIT x Orch-OR disagreements the demo rules not decidable with current instruments.
- **Correspondences, 0 candidates.** The demo marks all 37 (23 IIT x GNWT, 14 IIT x
  Orch-OR) as drafts, and their grades ("generative", "partial") are not the four-rung
  ladder the template needs. Publishing them would present drafts as verdicts.
- The pairing matrix publishes only counts per pair; there are no per-pair records to
  prepare beyond the two pairs above.

Example, as it would read: "Disagreement iit_t002 vs gnwt_c003 is testable with shared
observable: regional decoding." IIT's claim places the substrate of consciousness in a
posterior cortical hot zone; GNWT's places it in a prefrontal-parietal network.

The COGITATE comparison is reported as: 2 of 3 preregistered disagreements recovered after
a disclosed re-review (originally 1 of 3); p = 0.075 against a 1,000-key permutation null,
suggestive only. No template fits a recovery score, so it is not a candidate record.

**These candidates cannot be exported yet.** The receipt each nanopub needs is a link to
the record at a pinned commit of a public repository, with a content hash. The demo
results are not in a public repository at a pinned commit, and the matcher that produced
them is not public. So `records/` holds the candidates in the template's fields, and
`preview/` holds only the assertion graph built by the exporter's own mapping, with
placeholder claim links. The claim statements are model-drafted, person-reviewed
paraphrases of the theory papers (with page locators), not quotations.

Before publishing: commit the demo results (without the extraction-model field) and the
matcher, or at least the results, to a public repository; rebuild with real receipts; and
decide whether to publish 8 claim-pair records or 3, one per disagreement.
