# Provenance

What this branch copies from other repositories, and from which commit.

| What | From | Commit | How |
|---|---|---|---|
| Ten records in `pilot/records/` (three claim cards from `ledger/claims.json`, seven refused comparisons from `ledger/rejections.json`), copied unchanged inside record envelopes | [consilience-ledger](https://github.com/Anuja-Khatri/consilience-ledger), branch `wp1-public-truth` | `7c1f9235b582666403537dd929c844e4b2dfc8cf` | `scripts/select_pilot_records.py`, which reads the ledger with `git show` (read only) and checks every hash before writing |
| The verdict hash method (`compute_verdict_hash`: SHA-256 over sorted-key JSON) and the ledger-hash recipe, re-implemented in `src/consilience/receipts.py` | consilience-ledger, `vendor/engine/judge/hash/determinism_check.py` and `labext/ledger.py` | same | re-implemented, no code copied |
| Condition rule names (CR1–CR4 and their fields), used only for readable labels | consilience-ledger, `rules/comparability_rules.yaml` | same | read by the selection script into each envelope's `context` |
| Source document links | consilience-ledger, `corpus/MANIFEST.yaml` | same | copied into `scripts/select_pilot_records.py` |
| Nanopublication structure, the agent-introduction pattern, template shapes and the default provenance and pubinfo templates | [knowledgepixels/nanopub-skill](https://github.com/knowledgepixels/nanopub-skill) (documentation) and the templates it mirrors | read 16 Nov 2026 | followed, no code copied |
| Signing and trusty URIs | [`nanopub`](https://pypi.org/project/nanopub/) 2.2.2 from PyPI (Nanopublication/nanopub-py) | release 2.2.2 | used as a dependency |

No record was taken from a non-public repository.
