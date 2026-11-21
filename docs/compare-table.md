# `compare-table`: which records may be pooled, and do they agree

**For:**
- anyone, person or AI agent, who gathers measurements of "the same" quantity from many studies and is about to average, rank or train on them;
- first of all, potency values (IC50, Ki, Kd, EC50) from ChEMBL;
- and any other table of measurements, with a pack that says which conditions must match.

**What it solves.** Converting units is not enough to make two values comparable. An IC50 from a cell-based assay and one from a purified protein, a mutant and a wild-type target, a Ki and an IC50, or a ">10 µM" bound and an exact value may all carry the same unit and still must not be averaged. `compare-table` says, for every record:
- whether it may be pooled;
- if not, the named reason;
- for those that may, whether they agree within a cited noise level.

Every run has a receipt that anyone can re-run with `consilience verify`.

**What it is not.**
- It does not judge whether a paper is right, and it does not fix data.
- It does not guess a missing condition. A condition that is not stated is reported as not stated.

## Quick start

```bash
pip install "consilience>=0.2"

# ChEMBL activity records: the web API's JSON, or a CSV with the same columns
consilience compare-table egfr_activities.json --map chembl --pack bioactivity --out egfr/

# check the result from its receipt (needs the input file)
consilience verify egfr/receipt.json
```

```python
from consilience import compare_table

r = compare_table("egfr_activities.json", map="chembl", pack="bioactivity", out="egfr/")
print(r.text)                       # plain-language summary
r.records[0]["pool_valid"], r.records[0]["pool_reason"]
r.classes[0]["pooled_value"], r.classes[0]["pooled_unit"]
```

A pandas DataFrame or a list of dicts works too. With `out=`, the table is saved as `input.json` so that the receipt can be re-run.

## What it does, exactly

**1. Groups.** Records are grouped by `--key`, for example parent molecule and target. Only records in the same group are ever compared.

**2. Record status**, decided first:
- `excluded(<rule>: <reason>)`: a record rule of the pack fails, or the key is not stated;
- `unparseable(<what>: <why>)`: the value, unit, uncertainty or a condition cannot be read exactly;
- `bound`: the value is one-sided (`>`, `<`, `>=`, `<=`);
- `usable`: otherwise.

**3. Condition classes.**
- Inside a group, the records that are not excluded or unparseable are split by their condition values: the pack's conditions, after aliases, case rules and unit conversion. The kind of unit (molar, mass concentration…) is part of the class.
- A condition left empty on both records counts as equal only when the pack says `absent_on_both: equal`. The word "unstated" (or a map lookup to it) is never equal to anything.

**4. Pairs.**
- **Inside a class:** every pair is compared numerically, with exactly the rules of `consilience compare` (tolerance, floor, stated precision, bounds). A class with a condition that is not stated gives `not_stated` pairs.
- **Across classes:** every pair gets the refusal `compare` would give, for example `not_comparable(assay_type)`.
- A randomised test checks that every pair verdict equals `compare()`'s.

**5. Class consensus:**
- `single`: one record;
- `not_stated`: a condition is not stated;
- `bounds_only`: no exact value;
- `disagree`: any pair disagrees, including a value that breaks a bound;
- `within_floor`: any pair only within the floor;
- `agree`: otherwise.

`undecidable_bounds` pairs (two bounds that can both hold) do not change it.

**6. Pooled value.** For `single`, `agree` and `within_floor` classes: the median of the exact values, in the first exact value's unit.
- On the log scale, it is the geometric median: an odd count returns the middle value itself, an even count the geometric mean of the two middle values.
- Bounds are never averaged. `bounds_consistent` says whether every bound of the class holds against the pooled value.

**7. `pool_valid`** is true when all of these hold:
- the record is `usable`;
- every condition of its class is stated;
- the class consensus is `single`, `agree` or `within_floor`.

It means the record may be pooled **with the other records of its condition class**. It never means it may be pooled across classes: a group can have several valid classes, and choosing between them is the user's decision.

`pool_reason` says why it is false:
- `excluded(<rule>)`;
- `unparseable(...)`;
- `bound`;
- `condition_not_stated(<fields>)`;
- `class_disagrees`.

## Inputs

| Input | How cells are read |
|---|---|
| CSV (`.csv`, `.tsv`, `.txt`) | Every cell as text. `0.30` keeps its written digits, which stated precision depends on |
| JSON | A list of records, or the list under the map's `records` key (the ChEMBL API's `activities`). Numbers keep their written digits |
| JSONL, Parquet | Parquet numbers have no written form and are exact (`pip install pyarrow`) |
| DataFrame or list of dicts | Numbers are exact. NaN, None and blank cells are not stated |

**Empty, blank and NaN cells** are not stated, never an error.

**A pack field whose column is absent from the whole table** is not checked. The summary lists it under "Not checked (column absent from the table)", and the receipt records it.

## Column maps (`--map`)

A map renames columns and translates values, nothing else:
- `id`, `value`, `relation`, `unit` (or `fixed_unit`), `uncertainty`, `method`;
- `fields` (renames, dotted paths into nested JSON);
- `lookups` (for example ChEMBL's "UNDEFINED MUTATION" → `unstated`);
- `units` (the unit of a field's bare numbers, for example `temperature: degC`).

Bundled maps:
- `chembl`: ChEMBL activity records, key parent molecule + target;
- `iupac_pka`: the IUPAC Digitized pKa Dataset, key InChI + dissociation step.

## Packs

Bundled packs:
- **`bioactivity`:** 11 assay conditions from Landrum & Riniker 2024, 4 record rules, the opt-in assumption `ki_ic50_x2`, and defaults of 0.3 / 1.0 log units. See `docs/packs/bioactivity.md`.
- **`pka`:** temperature, cosolvent and pressure, IUPAC's own grades, no defaults. See `docs/packs/pka.md`.
- **`electrochemistry`:** unchanged.

The pack format is in `docs/RULES.md`. The options added in 0.2 are written into a pack's hash only when used, so older packs and receipts are unchanged:
- `absent_on_both`;
- `as_text` (read a value as text even when it starts with a digit, e.g. "1% ethanol");
- `record_rules` (`empty`, `present`, `in` with optional `allow_empty`, `at_least`);
- `assumptions`;
- `defaults`.

## Tolerances

- **Log scale** (`--log-tol`, `--log-floor`), for positive quantities: agree if `|log10 a − log10 b| ≤ log_tol`.
  - Stated precision on the log scale: a value v written with an implied half-unit h adds `log10(1 + h/v)`.
  - A value of zero or below cannot be compared on the log scale and is `unparseable`.
- **Linear** (`--abs-tol`, `--rel-tol`, `--floor`): as for `compare`. The two kinds cannot be mixed.
- **With no option given:** the pack's `defaults` are used, and the receipt says `defaults_from_pack: true`.

**Assumptions** (`--assume ki_ic50_x2`): two classes that differ only in the assumption's condition (Ki versus IC50) are merged. The `from` values are multiplied by the factor, and every affected record names the assumption.

## Outputs (`--out DIR`)

| File | One row per |
|---|---|
| `records.csv` | Input record: status, class, consensus, `pool_valid`, `pool_reason`, assumption |
| `classes.csv` | Condition class: conditions, counts, pair verdicts, consensus, pooled value, bounds check, methods |
| `pairs.csv` | Pair in a group: verdict, label, all reasons, difference (log10 units on the log scale), classes |
| `summary.json` | Run: counts, the plain-language text |
| `receipt.json` | Run: input SHA-256, map, pack, options, engine and pint versions, SHA-256 of every output |

## Exit codes

Precedence, highest first:
- **64:** unusable input.
- **3:** a record could not be read.
- **1:** a class disagrees inside.
- **0:** otherwise.

Records refused across classes or excluded by a rule are the expected product of the check, and do not set the exit code.

## Speed

26,205 synthetic ChEMBL-like records, with 1.5 million pairs, take about 20 s on one core (`tests/test_table.py::test_speed_egfr_scale`). Each record's value and unit are read once; pairs use the comparison core directly, with no receipt per pair.

## Agents

`integrations/agent-plugin/consilience-pooling/` runs this check automatically after an agent fetches ChEMBL activity records. It works with ChEMBL agent skills that print the path of the file they write; see the plugin's `README.md`; a recorded live run is in [consilience-benchmarks](https://github.com/Anuja-Khatri/consilience-benchmarks) (`pooling-2026/plugin/LIVE_RUN.md`).

## Limits

- **The bioactivity pack does not check ATP or substrate concentration.** They are mostly free text in ChEMBL.
- **Repeat citations of one measurement are kept** (`potential_duplicate`), so agreement statistics can be inflated by them.
- **Conditions must be exact-match** (tolerance 0) for classes to be well defined. A pack condition with a tolerance is refused by `compare-table`.
- **Pairs are formed only within a group.** Records with a different key are never compared.
