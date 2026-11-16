# Knowledge Pixels pilot: Consilience records as nanopublications (TEST server)

Everything listed here is published on the Knowledge Pixels **test** registry only. Nothing is on the live nanopublication network. The `https://w3id.org/np/…` identifiers inside the files resolve only on the live network, so the links below go to the test registry (`https://test.registry.knowledgepixels.com/np/<id>`).

All records come from the public [consilience-ledger](https://github.com/Anuja-Khatri/consilience-ledger) at commit `7c1f9235b582666403537dd929c844e4b2dfc8cf` (branch `wp1-public-truth`). Each one links back to the exact lines of its source record at that commit, and carries that record's content hash; `pytest` checks that the hashes reproduce.

## The publishing agent

- **The Consilience engine**, declared as a software agent (`npx:SoftwareAgent`, `npx:SoftwareTool`): agent IRI `https://w3id.org/np/RASIkcye4-dV2TVAUvTeacEPqwkEZuy3oAwgp6Tn12OGc/consilience-engine`.
- Introduction (declares its public key; self-signed): [`RASIkcye4-dV…`](https://test.registry.knowledgepixels.com/np/RASIkcye4-dV2TVAUvTeacEPqwkEZuy3oAwgp6Tn12OGc)
- Responsible person: Anuja Khatri (name only for now; an ORCID iD is to be added before any live publication).

## Templates

| Template | Test-server link | Instances in this pilot |
|---|---|---|
| (a) claim A corresponds to claim B at grade X | [`RAliOt1I-l8M…`](https://test.registry.knowledgepixels.com/np/RAliOt1I-l8MmIehzK8wqRenfljWJk4SED3XyJmVCIftY) | 0 |
| (b) comparison refused: condition C differs or is not stated | [`RAr2wiuk3YGz…`](https://test.registry.knowledgepixels.com/np/RAr2wiuk3YGzyw123e9k0lc-c8Om_WRhv5zQEyP6Rz9Dw) | 7 |
| (c) this disagreement is testable now with instrument Y | [`RA_JMm5qvBGc…`](https://test.registry.knowledgepixels.com/np/RA_JMm5qvBGcYZ05pWiJualxOVTFNj6_qJiI_6oaAU9vE) | 0 |
| (d) data-quality finding | [`RAIVWy9da47n…`](https://test.registry.knowledgepixels.com/np/RAIVWy9da47nSVGrlPGhVsqyvFTkFgzrpw42l_t12iVPo) | 0 |
| claim card (used by the pilot's claim cards) | [`RAeUz0d9B-nQ…`](https://test.registry.knowledgepixels.com/np/RAeUz0d9B-nQjoyXJQwXNJKx5gyD6li8FOjfFcKBzq5f8) | 3 |
| provenance: the receipt (used by every record) | [`RAjkzVXYgeEW…`](https://test.registry.knowledgepixels.com/np/RAjkzVXYgeEW-ORY5ZYAa_l_mgd-3Ki7HFItomg2I8el4) | 10 |

Templates (a), (c) and (d) have no instance in this pilot. The public ledger at this commit holds no graded correspondence and no fork (disagreement), and data-quality findings are shared with the dataset's maintainers before anything about them is published. The exporter supports all four types and the tests check each against its template.

## Records

| # | Type | What it says | Test-server link | Source receipt |
|---|---|---|---|---|
| 01 | claim card | Claim card: Pd-55, operational stability duration 500 h, from `ref40_peng2023`. | [`RA4UmeZBdq6p…`](https://test.registry.knowledgepixels.com/np/RA4UmeZBdq6pNgWcg5zCH6yvBZeLDjwWnDwAjEGdeU1DQ) | [claims.json#L623-L668](https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235b582666403537dd929c844e4b2dfc8cf/ledger/claims.json#L623-L668) |
| 02 | claim card | Claim card: Pd-55, operational stability duration 40 h (lower bound), from `ref40_peng2023`. | [`RA1HAG4dZ9aJ…`](https://test.registry.knowledgepixels.com/np/RA1HAG4dZ9aJB5NCD-Ig6yATyHiCT9uRnTYwJ0Hm_7vKg) | [claims.json#L827-L866](https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235b582666403537dd929c844e4b2dfc8cf/ledger/claims.json#L827-L866) |
| 03 | claim card | Claim card: InMnPdOx, overpotential at current density 0.45 V, from `2609.30133`. | [`RA49qRFK9XtX…`](https://test.registry.knowledgepixels.com/np/RA49qRFK9XtXtIu5XcFvkTDIo-rzeFSGpfavK5oim8j58) | [claims.json#L80-L119](https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235b582666403537dd929c844e4b2dfc8cf/ledger/claims.json#L80-L119) |
| 04 | refused comparison | Comparison of `ref40_peng2023__002` with `ref40_peng2023__011` refused: current density differs (rule CR2); not stated in the claim cards: electrolyte, temperature, ir correction. | [`RAttErMNFCCm…`](https://test.registry.knowledgepixels.com/np/RAttErMNFCCmfeggou4vaaXQlqbePSCw3Rh_qigiFSpa4) | [rejections.json#L9794-L9828](https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235b582666403537dd929c844e4b2dfc8cf/ledger/rejections.json#L9794-L9828) |
| 05 | refused comparison | Comparison of `ref40_peng2023__009` with `ref40_peng2023__010` refused: current density differs (rule CR2); not stated in the claim cards: electrolyte, ir correction. | [`RA1YUVPAWY0w…`](https://test.registry.knowledgepixels.com/np/RA1YUVPAWY0wyjK4NI69E-2mCu-QkmOl-bNIpOm20qepA) | [rejections.json#L10822-L10852](https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235b582666403537dd929c844e4b2dfc8cf/ledger/rejections.json#L10822-L10852) |
| 06 | refused comparison | Comparison of `2609.30133__001` with `ref40_peng2023__002` refused: the two claims are on different quantity axes (hours to threshold vs operational stability duration). | [`RAFkap6esujd…`](https://test.registry.knowledgepixels.com/np/RAFkap6esujdqU5MzB9D-4NMJCPZLqKP2zw7xCpOoodYU) | [rejections.json#L359-L381](https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235b582666403537dd929c844e4b2dfc8cf/ledger/rejections.json#L359-L381) |
| 07 | refused comparison | Comparison of `2609.30133__003` with `2609.30133__004` refused: not stated in the claim cards: electrolyte, temperature. | [`RAOVEJAJRvh0…`](https://test.registry.knowledgepixels.com/np/RAOVEJAJRvh0R3SCGpHwEezvZdaNNwAdVv3pPe6cce1IM) | [rejections.json#L1509-L1535](https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235b582666403537dd929c844e4b2dfc8cf/ledger/rejections.json#L1509-L1535) |
| 08 | refused comparison | Comparison of `2609.30133__003` with `ref40_peng2023__013` refused: not stated in the claim cards: electrolyte, current density, temperature, ir correction. | [`RA4MUUChBFMo…`](https://test.registry.knowledgepixels.com/np/RA4MUUChBFMojXEEwFAhOF11T0KxKzSXMgMeAmkiaSFII) | [rejections.json#L1974-L2008](https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235b582666403537dd929c844e4b2dfc8cf/ledger/rejections.json#L1974-L2008) |
| 09 | refused comparison | Comparison of `2609.30133__001` with `2609.30133__002` refused: not stated in the claim cards: electrolyte, current density, temperature, ir correction. | [`RAaUcr_sQOgJ…`](https://test.registry.knowledgepixels.com/np/RAaUcr_sQOgJec-CSehaIidZWW59jhKoMfgIUTpdAPYMk) | [rejections.json#L2-L36](https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235b582666403537dd929c844e4b2dfc8cf/ledger/rejections.json#L2-L36) |
| 10 | refused comparison | Comparison of `ref40_peng2023__026` with `ref40_peng2023__044` refused: not stated in the claim cards: electrolyte, current density, temperature, ir correction. | [`RAhDd4aPFDsK…`](https://test.registry.knowledgepixels.com/np/RAhDd4aPFDsKjIZcXLH1lx8K-MDc24ls3kA3JweZsOH6s) | [rejections.json#L13033-L13067](https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235b582666403537dd929c844e4b2dfc8cf/ledger/rejections.json#L13033-L13067) |

Source documents: `2609.30133` is arXiv:2609.30133; `ref40_peng2023` is Peng et al., National Science Review 10, nwac108 (2023), doi:10.1093/nsr/nwac108. A refused comparison records what the two claim cards, as extracted from their source sentences, allow under the ledger's rule set (`comparability-v0.1`); it is not a judgement of either paper.

Record 04 refers to the claim cards published as 01 and 02, record 06 to 01, and records 07 and 08 to 03: a refusal names its two claims by the same links (the claim cards' lines at the pinned commit) that the claim-card nanopubs describe.

## Checking a record yourself

```bash
consilience verify pilot/records/04-refusal-ref40_peng2023__002--ref40_peng2023__011.json
curl -H 'Accept: application/trig' https://test.registry.knowledgepixels.com/np/RAttErMNFCCmfeggou4vaaXQlqbePSCw3Rh_qigiFSpa4
```

The first command recomputes the content hash from the record; the nanopub's provenance carries the same hash and the link to the record at the pinned commit.
