# Changelog

## [0.1.1] - unreleased

Closes the gaps found when 0.1.0 was used in a real study (the WP5 run audit).

### Added
- The unit `"1"` is read as `dimensionless` (the SI way of writing a pure number). No
  other digit may stand in a unit except as an exponent (`cm^2`, `s^-1`).
- Count and ratio units `fold`, `cell`, `event`, `sample` (and plurals). Each is a
  dimensionless kind of its own: `3 fold` vs `3 cells`, or vs a bare `3`, is
  `not_comparable(unit)`. They combine (`cells/mL`) but take no SI prefix. Every other
  unknown word is still `unparseable(unknown_unit)`; pint's `count` stays a plain pure
  number, as in 0.1.0.
- One-sided bounds as values: `"<1e-6"`, `"<= 0.30 V"`, `"≤ 0.30 V"`, `"> 5"`,
  `">= 5 mV"`, `"≥ 5 mV"`. A value against a bound is `agree` if it satisfies the bound
  within tolerance + implied precision, `within_floor` if only within floor + implied
  precision, else `disagree`. Two bounds are `disagree` if they cannot both hold,
  otherwise the new verdict `undecidable_bounds` (exit 2). A bound cannot carry an
  uncertainty (`uncertainty_on_bound`); `"<<1"` is `unparseable(malformed_bound)` and
  `"< nan"` is `unparseable(non_finite)`. The receipt records `result.comparison` (`values`,
  `value_vs_bound`, `bounds`) and the bound sign of each side.
- `compare --exact` (Python: `compare(..., precision="exact")`) compares the numbers
  exactly, as 0.1.0 did.
- `read_json` keeps the digits of a JSON number as written (`WrittenFloat`), so `1.50`
  in a measurement file is two decimal places, not one.

### Changed
- **Stated precision is on by default.** A value with no stated uncertainty, written
  with k decimal places, carries an implied half-unit in its last place: `"0.777"`
  means 0.7765 to 0.7775, so `"0.777"` against 0.776943 is now `agree` (0.1.0 said
  `disagree` unless `--abs-tol 0.0005` was given). The two half-units are added to the
  tolerance and to the floor. Numbers without a decimal point (`1200`, `1e-6`) are
  exact; in scientific notation the mantissa's places count (`1.23e-5` means ±5e-8). The
  output prints a `precision:` line and the receipt records, per side, the digits as
  written, the implied half-unit and the rule (`result.precision`), and the mode
  (`options.precision`). `--exact` restores the 0.1.0 behaviour. `check` is unchanged.
- Inputs that 0.1.0 refused are now read: the unit `"1"` (was
  `unparseable(unit_contains_number)`), `fold`, `cell`, `event`, `sample` (were
  `unparseable(unknown_unit)`), and bounds such as `"<1e-6"` (were
  `unparseable(not_a_number)`).
- `compare` receipts gain `options.precision`, `result.precision` and
  `result.comparison`, and a bound side carries `"bound"`. The schema name stays
  `consilience-receipt/v1`; `check` receipts are unchanged.

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
