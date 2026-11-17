# Changelog

## [0.1.1] - unreleased

Closes the gaps found when 0.1.0 was used in a real study (the WP5 run audit).

### Added
- The unit `"1"` is read as `dimensionless` (the SI way of writing a pure number). No
  other digit may stand in a unit except as an exponent (`cm^2`, `s^-1`).

### Fixed
- `verify` re-runs a receipt by the rules of the consilience version that wrote it, so
  receipts made by 0.1.0 keep verifying even where 0.1.1 reads an input differently.

## [0.1.0] - 2026-11-17

First public release on PyPI.

### Added
- `consilience compare A.json B.json`: compares two measurements (value, unit, optional
  uncertainty, conditions). Verdicts `agree`, `within_floor`, `disagree`,
  `not_comparable(<what>)`, `not_stated(<what>)`, `unparseable(<what>: <why>)`.
  Absolute and relative tolerance, an optional floor, unit conversion with pint.
  Exit codes 0 / 1 / 2 / 3, and 64 for usage or input errors.
- Domain packs (`--pack`): YAML files that say which conditions must match and how
  (`equal` with aliases, `quantity_equal` with tolerance, words and extra keys, `record`
  with parts). Without a pack, every condition on either side must match exactly.
- The `electrochemistry` pack (`electrochemistry-v1`), ported from the comparability
  rules CR1-CR4 of consilience-ledger (see PROVENANCE.md).
- `consilience check DATA.csv --rules RULES.yaml`: checks a table against `limit` rules
  (a value against a limit recorded in the same row, with a margin and an optional
  offset) and `bound` rules (physical bounds). Reports every violating row with the rule,
  the value, the limit and a row receipt, and every cell it could not read, as text,
  JSON (`--json`, `--receipt`) and HTML (`--html`). Exit codes 0 / 1 / 3, and 64.
- `consilience verify RECEIPT.json`: re-runs a compare or check result from its receipt
  and confirms the hash. Still checks nanopublication record envelopes as before.
- One strict number-and-unit module (`consilience.units`) used everywhere: refuses
  spaces, commas and a second decimal point inside numbers, NaN and infinity in any
  form, glued scale suffixes, ambiguous and unknown units, and empty values, each with a
  named reason.
- `consilience examples DIR` (made-up example files), `consilience packs`,
  `consilience version`.
- Python API: `compare()`, `check()`, `verify()`, `load_rules()`.
- `scripts/check_release.sh` and `.github/workflows/publish.yml` (runs only on a
  published release or a manual run).

### Changed
- The nanopublication exporter (`export`, `agent`, `templates`) is now an optional extra:
  `pip install "consilience[nanopub]"` (Python 3.12+). Its behaviour is unchanged; its
  commands moved to `consilience/nanopub_cli.py`. The old README is now
  `docs/NANOPUB.md`.
- `requires-python` stays `>=3.10`; the core needs only pint and PyYAML.
