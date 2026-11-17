# Rule files

`consilience` reads two kinds of rule file. Both are YAML and follow one house format: a
`kind`, a `name`, a `version`, a `plain_english` line for the whole file and one for every
rule, and optionally a `rationale`, a `source` and a `licence`.

| `kind` | Used by | Says |
|---|---|---|
| `compare-pack` | `consilience compare --pack FILE` | which measurement conditions must match before two measurements may be compared, and how |
| `check-rules` | `consilience check DATA --rules FILE` | which columns of a table must respect which limits and bounds |

## Rules common to both

- **Unknown keys are refused.** A misspelt key (`maximum` for `max`) stops the load with
  an error naming the key. Nothing in a rule file is silently ignored.
- **Duplicate keys are refused**, and so are duplicate rule ids.
- **Quantities** are written as text with a unit, `0.02 V`, `0 K`, `500 mmol/L`, and read
  by the same strict parser as the data (see the README, "What is refused"). Units are
  [pint](https://pint.readthedocs.io/) names; case matters; `degC` is Celsius;
  `dimensionless` or `1` is a pure number; `fold`, `cell`, `event` and `sample` (and
  plurals) are pure numbers of their own kinds, never equal to each other or to `1`.
- **The hash.** After loading, the file is normalised (whitespace in text collapsed, keys
  sorted, defaults filled in) and hashed: SHA-256 over canonical JSON (sorted keys, no
  spaces, UTF-8). Comments and formatting do not change the hash; any change to a rule
  does. Every result prints the hash, and every receipt contains the whole normalised
  file, so `consilience verify` can re-run it.
- **Version.** Change `version` whenever you change a rule, so results made with the old
  and new rules are told apart by name as well as by hash.
- Plain-English lines should say the rule in one sentence a non-specialist can check.
  `source` should say where the rule comes from (a paper, a standard, a lab procedure).

## `compare-pack`

```yaml
kind: compare-pack
name: my-field
version: my-field-v1
plain_english: Two measurements in my field are comparable only when ...
source: Where these rules come from.        # optional
rationale: Why.                             # optional
licence: CC BY 4.0                          # optional
conditions:                                 # one rule per condition, at least one
  - id: C1                                  # unique
    field: temperature                      # the key in a measurement's "conditions"
    predicate: quantity_equal               # equal | quantity_equal | record
    tolerance: 0.5 K                        # predicate options (below)
    plain_english: Same temperature, to within 0.5 K.
    rationale: ...                          # optional
    source: ...                             # optional
```

Only the conditions a pack names are checked. A condition that a measurement gives but
the pack does not name is listed as "not checked". For each named condition:

- missing, `null` or `"unstated"` on either side: `not_stated(<field>)`;
- present on both sides but different by the predicate: `not_comparable(<field>)`;
- present but unreadable (`"1 200 degC"`, `"nan"`): `unparseable(<side>.conditions.<field>: <reason>)`.

### Predicates

**`equal`**: text, numbers or true/false must be the same.

| Option | Default | Meaning |
|---|---|---|
| `ignore_case` | `false` | compare text ignoring letter case |
| `aliases` | none | a map of spellings to one canonical name, e.g. `h2so4: sulfuric acid`. Both sides are mapped before comparing. With `ignore_case: true` the alias keys match ignoring case. |

Text is compared after collapsing runs of whitespace; otherwise exactly.

**`quantity_equal`**: both sides must be quantities with units (a string such as
`"25 degC"` or an object `{"value": 25, "unit": "degC", ...}`), compared after unit
conversion.

| Option | Default | Meaning |
|---|---|---|
| `tolerance` | `0` | the largest difference allowed, as a quantity (`0.5 K`). A difference in degC is a difference: `1 K` and `1 delta_degC` are the same tolerance. |
| `words` | none | words allowed instead of a number, which match only themselves, e.g. `room_temperature`. A word against a number is `not_comparable`. |
| `also_equal` | none | other keys of the object form that must also be stated and equal, e.g. `normalization` for a current density `{"value": 10, "unit": "mA/cm^2", "normalization": "geometric"}`. A missing one gives `not_stated(<field>.<key>)`. |

A bare number with no unit is refused here (`unparseable(...: missing_unit)`).

**`record`**: the condition is an object with named parts, each checked by its own
`equal` or `quantity_equal` rule.

```yaml
  - id: EC1
    field: electrolyte
    predicate: record
    parts:
      identity: {predicate: equal, ignore_case: true, aliases: {h2so4: sulfuric acid}}
      concentration: {predicate: quantity_equal, tolerance: 0}
    plain_english: Same electrolyte at the same concentration.
```

A missing part gives `not_stated(electrolyte.concentration)`; a differing part gives
`not_comparable(electrolyte.identity)`. Parts not listed are not checked.

### Without a pack

`consilience compare` without `--pack` checks every condition present on either side:
present on both, and equal. Text must match exactly (case and spelling count), numbers
exactly, quantities after unit conversion, objects key by key, lists item by item. A
condition present on only one side gives `not_stated(<condition>)`. This is the strict
default; a pack is how you say which differences in wording do not matter and which
conditions are irrelevant.

### The bundled electrochemistry pack

`electrochemistry` (`electrochemistry-v1`) has four rules, EC1 to EC4: electrolyte
(identity, with spellings of sulfuric and perchloric acid, and concentration), current
density (with its normalisation, which must be stated), temperature (with the word
`room_temperature`), and iR correction (true or false). Its source and what changed from
the rules it was ported from are in `PROVENANCE.md`. Print it with
`consilience examples DIR` (it is written as `electrochemistry.yaml`) and its hash with
`consilience packs`.

## `check-rules`

```yaml
kind: check-rules
name: my-checks
version: my-checks-v1
plain_english: What these checks are for.
id_column: sample_id            # optional: a column that labels rows in the report
columns:                        # every column a rule reads as a number
  reading:
    unit_column: reading_unit   # each row gives its own unit in this column
  limit_v:
    unit: V                     # or one unit for the whole column
  temperature_c:
    unit: degC
rules:
  - id: R1
    kind: limit
    column: reading
    limit_column: limit_v
    must_be: at_most
    margin: 0.02 V
    plain_english: A reading must not exceed its own recorded limit by more than 0.02 V.
  - id: R2
    kind: bound
    column: temperature_c
    min: 0 K
    plain_english: No temperature is below absolute zero.
```

### Columns

Each column a rule reads must be declared with exactly one of:

- `unit: <unit>`: every cell in the column is a plain number in this unit;
- `unit_column: <column>`: every row gives its own unit in that column (for tables that
  mix V and mV, say). A unit cell that is empty, unknown or ambiguous is reported as
  unreadable; a unit of the wrong kind (`mA` in a voltage column) is reported as
  `dimension_mismatch`.

Cells hold plain numbers only (`2.71`, not `2.71 V`): the unit comes from the
declaration. Every declared column, unit column and the `id_column` must be in the
table's header, or the check stops with exit code 64 before reading any row.

### `bound`

The value must lie within `min` and `max` (give one or both).

| Key | Default | Meaning |
|---|---|---|
| `min`, `max` | none | a quantity (`0 K`); for a column with a fixed `unit`, a bare number is in that unit |
| `min_inclusive`, `max_inclusive` | `true` | whether the bound itself is allowed |
| `if_empty` | `refuse` | `refuse`: an empty cell is reported as unreadable (`empty`). `skip`: an empty cell is skipped and counted under "skipped empty". |

### `limit`

The value must be at most (or at least) the value in another column of the same row.

| Key | Default | Meaning |
|---|---|---|
| `limit_column` | required | the column holding each row's limit |
| `must_be` | required | `at_most`: violation if value + offset > limit + margin. `at_least`: violation if value + offset < limit - margin. |
| `margin` | `0` | how far past the limit is still allowed (a difference, e.g. `0.02 V`) |
| `value_offset` | `0` | a constant added to the value before comparing, e.g. to move it to the same reference as the limit |
| `if_empty` | `refuse` | for an empty value cell, as for `bound` |
| `if_limit_empty` | `refuse` | for an empty limit cell: `refuse` (report as unreadable), `skip` (count as skipped), or a quantity to use as a fallback limit (the violation is then marked `fallback_limit`) |

The limit is converted to the value's unit before comparing.

### What a check reports

- **Violations**: line number, row id, rule, column, the value as written and its unit,
  the limit (in the value's unit), and a row receipt.
- **Cells that could not be read**: line, row id, column, the text, the reason, and the
  rules that needed the cell. A cell needed by two rules is counted once. A row with the
  wrong number of cells is refused whole and counted as one.
- **Summary**: rows, blank lines, violations, unreadable cells, skipped empty cells, and
  per rule: violations, could-not-check, skipped, passed.

Comparisons allow for rounding from unit conversion: differences smaller than one part in
10^9 of the values do not count. Lines that start with `#` before the header are
comments.

The row receipt is

```
sha256(canonical_json({"rules_sha256": <rule file hash>, "rule": <rule id>,
                       "line": <line number>, "cells": {<header>: <cell text>, ...}}))
```

where `canonical_json` is JSON with sorted keys, no spaces and UTF-8.
