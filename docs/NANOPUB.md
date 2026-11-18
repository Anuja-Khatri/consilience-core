# The nanopublication exporter (optional part of `consilience`)

This is a secondary feature of the `consilience` package, used from a source checkout of
consilience-core. It needs the optional dependencies: `pip install -e ".[nanopub]"`.
(Until version 0.1.0 this text was the repository README; the main README now covers
`compare`, `check` and `verify`.)

It exports Consilience records (claim cards and comparison verdicts, each with a
content hash) as **nanopublications**, small signed RDF statements with provenance that
anyone can cite.

**This is a pilot on the Knowledge Pixels test server.** Nothing has been published to the
live nanopublication network. The list of what was published, with links, is in
[`PILOT.md`](../PILOT.md). This page describes v2 (18 Nov 2026), regenerated after Tobias
Kuhn's review; v1's files are in `archive/v1/`.

## What it does

- Reads a *record envelope*: one record exactly as it appears in a public Consilience
  repository, plus the pinned commit and lines it came from (`pilot/records/*.json`).
- Checks the record against its receipt: the content hash must reproduce from the record
  itself. Anything that does not verify is refused with a named reason.
- Maps the record to the three graphs of a nanopublication:
  - **assertion**: the statement (for example, "the comparison of claim A with claim B is
    refused: current density differs, 10 vs 100 mA/cm² under rule CR2; claim B does not
    state the electrolyte"). Claim cards *introduce* a claim IRI (`<nanopub>/claim`), and
    every other record names its claims by those IRIs; conditions, axes, units and
    techniques are IRIs;
  - **provenance**: the receipt: source repository, commit, a link to the record at that
    commit, the content hash and how to reproduce it, and the code, rule and map versions
    that produced the record;
  - **publication info**: the publishing software agent, the CC BY 4.0 licence, a label,
    and the template it follows.
- Signs it with the engine's own key, as a declared software agent ("The Consilience
  engine"), and publishes it to the **test** registry. There is no code path to the live
  network.

Six assertion templates and one provenance template, in the Knowledge Pixels (Nanodash)
template format, describe the record types:

| Template | Record type |
|---|---|
| (a) claim A corresponds to claim B at grade X | graded correspondence |
| (b) comparison refused | refused comparison: which condition, which claim, which values |
| (c) claims A and B disagree on a dimension; testability and reason | disagreement (testable now, under a stated assumption, or not yet testable) |
| (d) data-quality finding | finding over a dataset |
| measured claim (claim card) | one measured claim with its source sentence; introduces the claim IRI |
| theory claim (claim card) | one claim of a theory; introduces the claim IRI |
| receipt (provenance) | where a record comes from and how to check it |

The vocabulary is described in [`VOCABULARY.md`](VOCABULARY.md).

## Run it

Needs Python 3.12 or later (the `nanopub` library needs it).

```bash
git clone -b nanopub-v2 https://github.com/Anuja-Khatri/consilience-core.git
cd consilience-core
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"        # includes the nanopub extra

# check one record against its receipt
consilience verify pilot/records/04-refusal-ref40_peng2023__002--ref40_peng2023__011.json

# write the nanopublication as TriG without publishing (unsigned unless you have the key)
consilience export --nanopub pilot/records/04-refusal-ref40_peng2023__002--ref40_peng2023__011.json \
    --dry-run --unsigned --out /tmp/04.trig

# tests: mapping, hashes against the public ledger, TriG validity, no keys in the tree
python -m pytest -q
```

The hash tests fetch the public ledger at the pinned commit from GitHub. To run them
offline against a local clone, set `CONSILIENCE_LEDGER_DIR=/path/to/consilience-ledger`;
`CONSILIENCE_OFFLINE=1` skips everything that needs the network.

Publishing (only the key holder can do this, and only to the test registry):

```bash
consilience agent keygen          # key goes to ~/.consilience-nanopub/, never into the repo
consilience agent introduce       # declares the engine's public key, owner = the ORCID iD in config/agent.json
consilience templates publish     # attributed to that ORCID iD, signed by the engine
consilience export --nanopub pilot/records/<claim card>.json     # claim cards first
consilience export --nanopub pilot/records/<refusal>.json        # then the records naming them
consilience export --nanopub pilot/examples/<example>.json --example
consilience export --nanopub <corrected card>.json --supersedes <old nanopub> --dry-run
```

Every publication is recorded in `pilot/publications.json`, and every published claim card's
claim IRI in `pilot/claims.json`; the signed files are kept in `agent/`, `templates/`,
`pilot/trig/`, `pilot/theories/trig/` and `pilot/examples/trig/`.

## Where the records come from

The pilot records are copied unchanged from the public
[consilience-ledger](https://github.com/Anuja-Khatri/consilience-ledger) at commit
`7c1f9235b582666403537dd929c844e4b2dfc8cf` by `scripts/select_pilot_records.py`; see
[`PROVENANCE.md`](../PROVENANCE.md).

## What it does not do

- It does not publish to the live network.
- It does not compute verdicts. It exports verdicts that the ledger's code computed and
  committed; their hashes are checked, not re-derived from the source papers.
- A claim-card nanopub carries the fields a reader needs (sentence, source, subject,
  quantity, conditions). The full card, including fields not mapped, is at its receipt
  link and is covered by the content hash.
- It does not guess an IRI. A string with no IRI in `src/consilience/export/mapping.py` is
  refused with a named reason.

## Licence

Code: MIT (`LICENSE`). Records, templates and vocabulary: CC BY 4.0 (`LICENSE-DATA`).
