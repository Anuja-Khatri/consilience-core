# consilience

Compare two measurements with their units and conditions, and check a table of data
against written limits. When something cannot be read exactly, `consilience` says so and
names the reason instead of guessing. Every result comes with a receipt that anyone can
re-run to confirm it.

- `consilience compare a.json b.json` answers: do these two measurements agree, and are
  they even comparable? It converts units, applies your tolerances, and checks that the
  measurement conditions match.
- `consilience check data.csv --rules rules.yaml` lists every row that breaks a rule (a
  value above its own recorded limit, a value outside physical bounds), and every cell it
  could not read.
- `consilience compare-table table.csv --key ... --pack ...` answers, for a whole table of
  measurements gathered from many sources: which records may be pooled, why the others
  may not, and whether the poolable ones agree. For potency values from ChEMBL:
  `consilience compare-table activities.json --map chembl --pack bioactivity`.
- `consilience verify receipt.json` re-runs any of these results and confirms its hash.

Verdicts come from plain, deterministic code. No AI model is called anywhere in this
package.

**Who it is for:** anyone who compares numbers from different labs, papers or runs, or
who receives tables of measurements and wants to know which rows to distrust before
using them: researchers, data stewards, people building automated or AI-assisted analysis
who want a check that refuses rather than guesses.

## Install

Needs Python 3.10 or newer.

```
pip install consilience
```

This installs the command `consilience` and two dependencies (pint for units, PyYAML for
rule files).

## Five-minute quickstart: compare

Write the made-up example files into a new folder and go there:

```console
$ consilience examples try
wrote try/measurement_a.json
wrote try/measurement_b.json
wrote try/measurement_c.json
wrote try/measurement_d.json
wrote try/measurement_e.json
wrote try/readings.csv
wrote try/readings_rules.yaml
wrote try/electrochemistry.yaml
These examples are MADE UP for trying the tool; they are not real data.
$ cd try
```

A measurement file holds a value, a unit, an optional uncertainty and the conditions it
was measured under. `measurement_a.json`:

```json
{
  "note": "MADE-UP EXAMPLE for the consilience quickstart. Not a real measurement.",
  "label": "Example lab A, overpotential at 10 mA/cm^2",
  "value": 0.320,
  "unit": "V",
  "uncertainty": "4 mV",
  "conditions": {
    "electrolyte": {"identity": "H2SO4", "concentration": "0.5 mol/L"},
    "current_density": {"value": 10, "unit": "mA/cm^2", "normalization": "geometric"},
    "temperature": "25 degC",
    "ir_correction": true
  }
}
```

`measurement_b.json` reports 331 mV ± 3 mV under the same conditions, written
differently ("sulfuric acid", "500 mmol/L", "0.01 A/cm^2", "298.15 K"). Compare them with
the bundled electrochemistry pack, which knows which conditions matter:

```console
$ consilience compare measurement_a.json measurement_b.json --pack electrochemistry
verdict:    disagree
a:          0.32 V ± 0.004 V   (as given: 0.32 V ± 4 mV)   [Example lab A, overpotential at 10 mA/cm^2]
b:          0.331 V ± 0.003 V   (as given: 331 mV ± 3 mV)   [Example lab B, overpotential at 10 mA/cm^2]
difference: 0.011 V
tolerance:  0 V   (larger of --abs-tol and --rel-tol x the larger value)
floor:      0.004 V   (largest of --floor and the two uncertainties)
conditions: checked with pack electrochemistry (electrochemistry-v1): electrolyte, current_density, temperature, ir_correction
pack hash:  cbf7aea81b7f7eb070538e6049b2b2bd4ebcb00ae409c9ecfde9737d3ef1f97c
receipt:    sha256 ...
$ echo $?
1
```

The units were converted and the conditions matched, so the two values could be
compared; they differ by 11 mV, more than either stated uncertainty. If you know that
labs typically spread by 13 mV on this measurement, say so with `--floor`:

```console
$ consilience compare measurement_a.json measurement_b.json --pack electrochemistry --floor "13 mV"
verdict:    within_floor
a:          0.32 V ± 0.004 V   (as given: 0.32 V ± 4 mV)   [Example lab A, overpotential at 10 mA/cm^2]
b:          0.331 V ± 0.003 V   (as given: 331 mV ± 3 mV)   [Example lab B, overpotential at 10 mA/cm^2]
difference: 0.011 V
tolerance:  0 V   (larger of --abs-tol and --rel-tol x the larger value)
floor:      0.013 V   (largest of --floor and the two uncertainties)
conditions: checked with pack electrochemistry (electrochemistry-v1): electrolyte, current_density, temperature, ir_correction
pack hash:  cbf7aea81b7f7eb070538e6049b2b2bd4ebcb00ae409c9ecfde9737d3ef1f97c
receipt:    sha256 ...
$ echo $?
0
```

(The 13 mV here is an example number, not a measured spread.)

Measurement C was taken at 100 mA/cm^2 instead of 10, so it is refused, and the rule that
refused it is named:

```console
$ consilience compare measurement_a.json measurement_c.json --pack electrochemistry
verdict:    not_comparable(current_density)
a:          0.32 V ± 0.004 V   (as given: 0.32 V ± 4 mV)   [Example lab A, overpotential at 10 mA/cm^2]
b:          0.41 V   [Example lab C, overpotential at 100 mA/cm^2]
  not_comparable  current_density ({"normalization": "geometric", "unit": "mA/cm^2", "value": 10} vs {"normalization": "geometric", "unit": "mA/cm^2", "value": 100})
                  rule EC2: Overpotentials are comparable only at the same current density and the same normalisation (geometric or ECSA).
conditions: checked with pack electrochemistry (electrochemistry-v1): electrolyte, current_density, temperature, ir_correction
pack hash:  cbf7aea81b7f7eb070538e6049b2b2bd4ebcb00ae409c9ecfde9737d3ef1f97c
receipt:    sha256 ...
$ echo $?
2
```

Measurement D does not say its temperature, so the comparison is refused rather than
assumed:

```console
$ consilience compare measurement_a.json measurement_d.json --pack electrochemistry
verdict:    not_stated(temperature)
a:          0.32 V ± 0.004 V   (as given: 0.32 V ± 4 mV)   [Example lab A, overpotential at 10 mA/cm^2]
b:          0.318 V   [Example lab D, temperature not reported]
  not_stated      temperature (not stated on b)
                  rule EC3: Measurements are comparable only at the same temperature; room_temperature matches room_temperature only, never a number.
conditions: checked with pack electrochemistry (electrochemistry-v1): electrolyte, current_density, temperature, ir_correction
pack hash:  cbf7aea81b7f7eb070538e6049b2b2bd4ebcb00ae409c9ecfde9737d3ef1f97c
receipt:    sha256 ...
$ echo $?
2
```

Measurement E writes its value as `"0,32"`. A comma can be a decimal point or a
thousands separator, so it is refused:

```console
$ consilience compare measurement_a.json measurement_e.json --pack electrochemistry
verdict:    unparseable(b.value: ambiguous_separator)
a:          0.32 V ± 0.004 V   (as given: 0.32 V ± 4 mV)   [Example lab A, overpotential at 10 mA/cm^2]
b:          0,32 V   [Example lab E, value written as 0,32]
  unparseable     b.value: ambiguous_separator (a comma may be a decimal or a thousands separator)
conditions: checked with pack electrochemistry (electrochemistry-v1): electrolyte, current_density, temperature, ir_correction
pack hash:  cbf7aea81b7f7eb070538e6049b2b2bd4ebcb00ae409c9ecfde9737d3ef1f97c
receipt:    sha256 ...
$ echo $?
3
```

Without a pack, every condition on either side must match exactly, so the different
spelling of the electrolyte is enough to refuse. That is what a pack is for:

```console
$ consilience compare measurement_a.json measurement_b.json
verdict:    not_comparable(electrolyte.identity)
a:          0.32 V ± 0.004 V   (as given: 0.32 V ± 4 mV)   [Example lab A, overpotential at 10 mA/cm^2]
b:          0.331 V ± 0.003 V   (as given: 331 mV ± 3 mV)   [Example lab B, overpotential at 10 mA/cm^2]
  not_comparable  electrolyte.identity ("H2SO4" vs "sulfuric acid")
conditions: no pack: every condition on either side must match (current_density, electrolyte, ir_correction, temperature)
receipt:    sha256 ...
$ echo $?
2
```

Save a receipt and re-run it:

```console
$ consilience compare measurement_a.json measurement_b.json --pack electrochemistry --abs-tol "15 mV" --receipt compare-receipt.json
verdict:    agree
a:          0.32 V ± 0.004 V   (as given: 0.32 V ± 4 mV)   [Example lab A, overpotential at 10 mA/cm^2]
b:          0.331 V ± 0.003 V   (as given: 331 mV ± 3 mV)   [Example lab B, overpotential at 10 mA/cm^2]
difference: 0.011 V
tolerance:  0.015 V   (larger of --abs-tol and --rel-tol x the larger value)
floor:      0.004 V   (largest of --floor and the two uncertainties)
conditions: checked with pack electrochemistry (electrochemistry-v1): electrolyte, current_density, temperature, ir_correction
pack hash:  cbf7aea81b7f7eb070538e6049b2b2bd4ebcb00ae409c9ecfde9737d3ef1f97c
receipt:    sha256 ...
wrote:      compare-receipt.json
$ consilience verify compare-receipt.json
ok: compare-receipt.json (compare)
  ok  receipt hash: matches its contents
  ok  rule hash: electrochemistry (electrochemistry-v1) matches
  ok  re-run: same result
  recorded sha256   ...
$ echo $?
0
```

### Values as a paper writes them

A paper says `0.777`; the run that produced it logged `0.776943`. A value written with k
decimal places carries an implied half-unit in its last place, so `0.777` means 0.7765
to 0.7775, and the two agree. The output says how much was implied, and why:

```console
$ echo '{"value": "0.777", "unit": "1"}' > paper.json
$ echo '{"value": 0.776943, "unit": "1"}' > run.json
$ consilience compare paper.json run.json
verdict:    agree
a:          0.777 dimensionless   (as given: 0.777 1)
b:          0.776943 dimensionless   (as given: 0.776943 1)
difference: 5.7e-05 dimensionless
tolerance:  0 dimensionless   (larger of --abs-tol and --rel-tol x the larger value)
floor:      0 dimensionless   (largest of --floor and the two uncertainties)
precision:  ±0.0005005 dimensionless implied by stated precision (added to the tolerance and the floor; --exact turns this off)
            a 0.777: 3 decimal places, ±0.0005 dimensionless
            b 0.776943: 6 decimal places, ±5e-07 dimensionless
conditions: no pack: every condition on either side must match (none given)
receipt:    sha256 ...
$ consilience compare paper.json run.json --exact
verdict:    disagree
...
precision:  exact (--exact): no tolerance is implied by how the values are written
...
```

The rules: only a value without a stated uncertainty gets an implied precision (an
uncertainty, when given, is used instead). A number without a decimal point (`1200`,
`17`, `1e-6`) is exact, because trailing zeros are ambiguous; write `1200.` to mean
"to the nearest unit". In scientific notation the mantissa counts: `1.23e-5` means
±5e-8. The two half-units are added to the tolerance and to the floor. A number in a
JSON file keeps the digits written in the file (`1.50` is two places); a Python float
passed to `compare()` has no written form and is exact. Stated precision applies to
the two values compared, not to conditions; `check` compares cells exactly.

Papers also report bounds, such as `p < 1e-6` or `≤ 0.30 V`. A value may be a one-sided
bound (`<`, `<=`, `≤`, `>`, `>=`, `≥`), and the run's value is checked against it:

```console
$ echo '{"value": "<1e-6", "unit": "1"}' > bound.json
$ echo '{"value": 2.3e-7, "unit": "1"}' > p_value.json
$ consilience compare bound.json p_value.json
verdict:    agree
a:          < 1e-06 dimensionless   (as given: <1e-6 1)
b:          2.3e-07 dimensionless   (as given: 2.3e-07 1)
beyond:     0 dimensionless   (how far b lies past a's bound; 0 means it satisfies it)
tolerance:  0 dimensionless   (larger of --abs-tol and --rel-tol x the larger value)
floor:      0 dimensionless   (largest of --floor and the two uncertainties)
precision:  ±5e-09 dimensionless implied by stated precision (added to the tolerance and the floor; --exact turns this off)
            a 1e-6: no decimal point: exact
            b 2.3e-7: 1 decimal place in the mantissa, exponent -7, ±5e-09 dimensionless
conditions: no pack: every condition on either side must match (none given)
receipt:    sha256 ...
$ echo '{"value": "< 1e-5", "unit": "1"}' > other_bound.json
$ consilience compare bound.json other_bound.json
verdict:    undecidable_bounds
a:          < 1e-06 dimensionless   (as given: <1e-6 1)
b:          < 1e-05 dimensionless   (as given: < 1e-5 1)
bounds:     a < 1e-06 dimensionless and b < 1e-05 dimensionless can both hold, so there is no single value to compare
...
$ echo $?
2
```

A value against a bound: `agree` if it satisfies the bound within the tolerance plus
the implied precision; `within_floor` if it does so only within the floor (which
includes the value's own uncertainty) plus the implied precision; `disagree` if it
lies past it by more. With no tolerance at all, `<` needs the value strictly below the
bound and `<=` allows it to equal the bound. Two bounds: `disagree` if no value can
satisfy both (`< 1` against `> 2`), otherwise `undecidable_bounds` (exit 2), because
there is no single value to compare. A bound cannot carry an uncertainty
(`unparseable(a.uncertainty: uncertainty_on_bound)`), and a malformed one is refused:
`"<<1"` is `malformed_bound`, `"< nan"` is `non_finite`. Bounds are read in a
measurement's `value` only, not in conditions or `check` cells.

Add `--json` to any `compare` or `check` to get the full result as JSON (the same content
as the receipt).

## Five-minute quickstart: check a table

`readings.csv` is a small made-up table of bench readings. Each row has a reading, the
unit of that reading, the limit recorded for it, a temperature and a humidity. Some rows
are wrong on purpose. `readings_rules.yaml` holds three rules:

- **R1** (limit): a reading must not exceed its own recorded limit by more than 0.02 V;
- **R2** (bound): no temperature below absolute zero (`min: 0 K`);
- **R3** (bound): relative humidity between 0 and 100 percent.

```console
$ consilience check readings.csv --rules readings_rules.yaml --html report.html --receipt check-receipt.json
data:        readings.csv (20 rows; sha256 ce1f95d5ff15ebab30b57e7d37d1e3793d88c2bbedc0e8f42f59d3a6f1d2e84f)
rules:       example-bench-readings-v1 (readings_rules.yaml)
rule hash:   b6a64e8fab26a07da5ca9fbcc0c50a3460781ba722f224bd0a27221fb80bbcff
violations:  5
  line 7    S-004  R1  reading 2.71 V > limit_v 2.5 V + margin 0.02 V   row receipt f6ebb38ff21a
  line 10   S-007  R2  temperature_c -280 degC < min -273.15 degC   row receipt bda89ad69f3a
  line 14   S-011  R1  reading 850 mV > limit_v 800 mV + margin 20 mV   row receipt 511d51f9d275
  line 18   S-015  R3  humidity_pct 104 percent > max 100 percent   row receipt be633f7a4560
  line 21   S-018  R3  humidity_pct -3 percent < min 0 percent   row receipt 3a7f9477333a
could not read: 2 cells (not checked; nothing was guessed)
  line 12   S-009  limit_v "n/a": not_a_number (needed by R1)
  line 16   S-013  temperature_c "21,5": ambiguous_separator (needed by R2)
skipped empty: 0
result:      exit 3: some cells could not be read, so the check is incomplete
receipt:     sha256 ...
wrote:       report.html
wrote:       check-receipt.json
$ echo $?
3
$ consilience verify check-receipt.json
ok: check-receipt.json (check)
  ok  receipt hash: matches its contents
  ok  rule hash: example-bench-readings (example-bench-readings-v1) matches
  ok  data hash: readings.csv matches
  ok  re-run: same result
  recorded sha256   ...
$ echo $?
0
```

Row S-011 was recorded in mV; it was converted before comparing with its limit in V. The
two cells that could not be read are listed and counted, not skipped: fix them and run
the check again. Open `report.html` in a browser for the same report as a page. The
full report, including every violating row's receipt, is in `check-receipt.json`.

## Pooling check: a whole table (new in 0.2)

Converting units is not enough to make values comparable. `compare-table` groups a table
by a key (for bioactivity: molecule and target), splits each group into condition classes
(records that may be pooled together), compares every pair with exactly the rules of
`compare`, and marks each record `pool_valid` or names why not.

```
consilience compare-table egfr_activities.json --map chembl --pack bioactivity --out egfr/
consilience verify egfr/receipt.json
```

- The `bioactivity` pack: the assay conditions Landrum & Riniker (2024) match before
  combining ChEMBL assays, ChEMBL's own validity warnings, bounds kept as bounds, and
  agreement within 0.3 / 1.0 log units. See [docs/packs/bioactivity.md](docs/packs/bioactivity.md).
- A second domain: the `pka` pack for measured pKa values ([docs/packs/pka.md](docs/packs/pka.md),
  `examples/pka_pooling.py`).
- An agent plugin runs the check after an AI agent fetches ChEMBL data:
  [integrations/agent-plugin/consilience-pooling](integrations/agent-plugin/consilience-pooling/).
- A preregistered study on 30 targets: [studies/pooling-2026](studies/pooling-2026/).

Full description, definitions and limits: [docs/compare-table.md](docs/compare-table.md).

## Stress-check scoring code before you optimise against it (new in 0.3)

`pip install 'consilience[stress]'`, then `consilience stress contract.yaml --out receipts/`.

Program search (AlphaEvolve, OpenEvolve, ShinkaEvolve, CodeEvolve), reinforcement learning and any other optimiser will exploit a scorer that:
- accepts invalid answers;
- trusts numbers a candidate reports about itself;
- changes its verdict under transformations that should not matter.

`stress` reads a short contract (what a valid answer is, written from the problem statement) and attacks the scorer *before* the costly run.

| Verdict | Meaning |
|---|---|
| **BLOCK** | A counterexample anyone can re-run, saved with the receipt |
| **PASS** | No counterexample found within the stated budget (not a proof) |
| **ABSTAIN** | The check could not run; a named reason is given |

`consilience verify` re-checks the receipt.

Also included:
- an agent plugin that runs the check after a scoring file is edited (`integrations/agent-plugin/consilience-stress`);
- a public benchmark of about 110 contracts across five evaluator collections (`benchmarks/evaluator-stress`).

What it is good at, who it is for, the full contract reference and its limits: **docs/stress.md**.

## Python

The same four functions, from Python:

```python
from consilience import check, compare, load_rules, verify

r = compare("measurement_a.json", "measurement_b.json", pack="electrochemistry")
print(r.verdict, r.exit_code)                # disagree 1
print(round(r.difference, 6), r.unit)        # 0.011 V

c = check("readings.csv", "readings_rules.yaml")
print(c.summary["violations"], c.summary["unparseable_cells"])   # 5 2
print([v["id"] for v in c.violations])       # ['S-004', 'S-007', 'S-011', 'S-015', 'S-018']

print(verify(r.receipt).ok)                  # True
print(load_rules("electrochemistry").version)   # electrochemistry-v1
```

Run it from the `try` folder. Inputs can be file paths or dicts. Problems with the inputs
themselves (a missing file, an unknown field, a bad option) raise `InputError`; a bad rule
file raises `RuleFileError`. Anything that can be read but not compared is a verdict, not
an exception. `c.to_html()` gives the HTML report.

## What the verdicts mean

| Verdict | Meaning | Exit code |
|---|---|---|
| `agree` | The difference is within the tolerance: the larger of `--abs-tol` and `--rel-tol` times the larger value (both 0 by default), plus the precision implied by how the values are written (none with `--exact`). | 0 |
| `within_floor` | Not within the tolerance, but within the floor: the largest of `--floor` and the two stated uncertainties, plus the implied precision. A difference this small is not evidence of disagreement. | 0 |
| `disagree` | The difference is larger than both. | 1 |
| `not_comparable(<what>)` | A condition differs (`not_comparable(temperature)`), or the two values measure different things (`not_comparable(unit)`: millivolts against milliamps). | 2 |
| `not_stated(<what>)` | A value, unit or condition is missing on one or both sides, so the comparison cannot be made. | 2 |
| `undecidable_bounds` | Both values are one-sided bounds (`< 1e-6` and `< 1e-5`) that can both hold, so there is no single value to compare. | 2 |
| `unparseable(<what>: <why>)` | Something could not be read exactly. The reason is named, e.g. `ambiguous_separator`, `non_finite`, `unknown_unit`. | 3 |

When there are several problems, all are listed and the verdict is the first by rank:
`unparseable`, then `not_comparable`, then `not_stated`. Differences smaller than one
part in 10^9 of the values are treated as rounding from unit conversion.

Exit codes of `check`: 0 no violations and every needed cell read; 1 violations; 3 some
cells could not be read (the check is incomplete; the violations it did find are still
listed). `verify`: 0 the re-run reproduces the receipt, 1 it does not. Every command: 64
for a usage or input error (missing file, unknown field, unreadable rule file); 141 if
the output was piped into a reader that stopped early (e.g. `| head -1`), as with other
command-line tools.

## What is refused, and why

Numbers are read by a fixed grammar (a sign, digits, one decimal point, an optional
exponent), never evaluated as arithmetic. These are refused with a named reason:

| Input | Reason | Why |
|---|---|---|
| `"1 200"` | `space_separated_digits` | one number or two? |
| `"3,14"`, `"1,200"` | `ambiguous_separator` | decimal comma or thousands separator? |
| `"1.2.3"` | `second_decimal_point` | not a number |
| `"nan"`, `"inf"`, `NaN`, `1e400` | `non_finite` | not a measurement |
| `"(1,234)"` | `parenthesised_number` | accounting negative? |
| `"5-10"`, `"1/2"` | `malformed_number` | a range or arithmetic, not a value |
| `"1 h 30 min"` | `compound_quantity` | more than one number |
| `"5M"`, `"5k"` | `ambiguous_scale_suffix` | molar or million? |
| `"25 C"` | `ambiguous_unit` | Celsius or coulomb? Write `degC`. |
| `"10 mA/cm2"` | `unit_contains_number` | write `cm^2` |
| `"5 banana"`, `"5 kcells"` | `unknown_unit` | |
| `"<<1"`, `"=<1"`, `"<"` | `malformed_bound` | not a one-sided bound |
| empty | `empty` / `missing_unit` | |

Units are [pint](https://pint.readthedocs.io/) unit names, and case matters (`m` is
metre, `M` is molar, `K` is kelvin). Write `degC` for Celsius and `dimensionless` (or
`1`, as SI writes it) for a pure number. `%` and `percent` work, so `90 %` equals `0.9`.

Four count and ratio words are units as well: `fold`, `cell`, `event` and `sample` (and
their plurals, `cells`, `events`, ...). Each is a pure number of its own kind, so
`3 fold` equals `3 folds` but is not comparable with `3 cells` or with a bare `3`
(`not_comparable(unit)`). They combine with other units (`cells/mL`) but take no prefix
(`kcells` is `unknown_unit`). Any other word that pint does not know is `unknown_unit`.

## Conditions and domain packs

**Without a pack**, every condition present on either side must be present on both and
equal: text exactly (case and spelling count, because `Co` is cobalt and `CO` is carbon
monoxide), numbers exactly, quantities after unit conversion, nested objects key by key.
A condition present on only one side gives `not_stated(<condition>)`. A value of `null`
or `"unstated"` is treated as not stated.

**With a pack** (`--pack electrochemistry` or `--pack my_pack.yaml`), only the conditions
the pack names are checked, by the pack's rules; other conditions are listed as "not
checked". A pack can say that some spellings mean the same thing, that a quantity must
match within a tolerance, that a word like `room_temperature` matches only itself, and
that a part such as `normalization` must also match.

The bundled **electrochemistry** pack (`electrochemistry-v1`) checks electrolyte identity
and concentration, current density and its normalisation, temperature, and iR correction.
Each rule has a plain-English line, a rationale and a source. List bundled packs with
`consilience packs`. `consilience examples` writes a copy, `electrochemistry.yaml`, that
you can edit.

## Writing rules

Both kinds of rule file are YAML with a `kind`, a `name`, a `version`, and a
`plain_english` line for the file and for every rule. A check rule file:

```yaml
kind: check-rules
name: my-rules
version: my-rules-v1
plain_english: What these rules are for.
id_column: sample_id             # optional: labels rows in the report
columns:                         # every column a rule reads, with its unit
  reading: {unit_column: reading_unit}   # each row says its own unit
  limit_v: {unit: V}                     # one unit for the whole column
  temperature_c: {unit: degC}
rules:
  - id: R1
    kind: limit                  # value against another column of the same row
    column: reading
    limit_column: limit_v
    must_be: at_most             # or at_least
    margin: 0.02 V
    plain_english: A reading must not exceed its own recorded limit by more than 0.02 V.
  - id: R2
    kind: bound                  # value against fixed bounds
    column: temperature_c
    min: 0 K
    plain_english: No temperature is below absolute zero.
```

Unknown keys are refused, so a misspelt key is an error rather than silently ignored.
The full format for both kinds (and options such as `if_empty`, `if_limit_empty`,
`value_offset`, exclusive bounds, and every pack predicate) is in
[docs/RULES.md](https://github.com/Anuja-Khatri/consilience-core/blob/v0.1.1/docs/RULES.md).

## Receipts

A receipt is a JSON file holding the inputs (for `check`, the data file's path and
SHA-256), the options, the complete rule file used, the consilience and pint versions,
and the result, plus a SHA-256 over all of that. `consilience verify` checks the hash,
checks the data file still has the same SHA-256, re-runs the comparison or check, and
confirms the fresh result hashes the same. It re-runs by the rules of the version that
wrote the receipt, so a receipt made with 0.1.0 still verifies under 0.1.1, even where
0.1.1 reads the same input differently. For a check receipt it looks for the data file
where it was, then beside the receipt; `--data` tells it where the file is now. A
violation's row receipt is `sha256` over `{"rules_sha256", "rule", "line", "cells"}` in
canonical JSON (the rule file's hash, the rule id, the line number and the row as text).

## What it does not do

- **It does not read prose.** It does not find numbers or conditions in papers, reports
  or model output. You give it structured files.
- **It checks only the conditions you give it.** If a condition that matters is missing
  from both files, and no pack names it, nothing will notice.
- **The electrochemistry pack covers one field**, and only the four conditions it names.
  For other fields, write a pack; without one, every condition must match exactly.
- **The example data is made up.** It shows how the tool works; it describes no real
  instrument, sample or experiment. The 13 mV floor in the quickstart is an example too.
- **It does not know whether your rules are right.** A check reports rows that break the
  rules you wrote, nothing more.
- **There is no hosted service.** `compare`, `check` and `verify` run on your computer
  and send nothing anywhere.
- It reads CSV only (UTF-8, comma-separated, a header row).

## Also in this package: nanopublication export

From a source checkout, the package can also export Consilience records as
nanopublications (signed, citable RDF statements) to the Knowledge Pixels test registry.
This needs `pip install "consilience[nanopub]"` (Python 3.12 or newer, which the
nanopub library requires) and is described in
[docs/NANOPUB.md](https://github.com/Anuja-Khatri/consilience-core/blob/v0.1.1/docs/NANOPUB.md)
and [PILOT.md](https://github.com/Anuja-Khatri/consilience-core/blob/v0.1.1/PILOT.md).

## Develop

```
git clone -b v0.1.1 https://github.com/Anuja-Khatri/consilience-core.git
cd consilience-core
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
python -m pytest -q
bash scripts/check_release.sh      # build, install the wheel in a clean venv, run this README
```

## Licence and provenance

Code: MIT ([LICENSE](https://github.com/Anuja-Khatri/consilience-core/blob/v0.1.1/LICENSE)).
Rule packs, examples, records and vocabulary: CC BY 4.0
([LICENSE-DATA](https://github.com/Anuja-Khatri/consilience-core/blob/v0.1.1/LICENSE-DATA)).
What was adapted from other Consilience repositories, and from which commit, is in
[PROVENANCE.md](https://github.com/Anuja-Khatri/consilience-core/blob/v0.1.1/PROVENANCE.md).
Changes: [CHANGELOG.md](https://github.com/Anuja-Khatri/consilience-core/blob/v0.1.1/CHANGELOG.md).
