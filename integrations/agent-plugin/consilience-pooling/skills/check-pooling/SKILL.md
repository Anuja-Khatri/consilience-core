---
name: check-pooling
description: Use before averaging, ranking or comparing potency values (IC50, Ki, Kd, EC50) gathered from ChEMBL or similar sources, or before building a training set from them. Says which records may be pooled, names why the others may not (different assay type, format, cell type, target variant, measurement type, a ">" or "<" bound, a ChEMBL validity warning), and whether the poolable ones agree within published inter-lab noise. Deterministic, with a receipt.
---

# Check before pooling potency values

Unit conversion is not enough to make two potency values comparable. Before you average, rank or train on values for the same molecule and target, run the pooling check.

## When to run it

- After fetching ChEMBL activity records (for example with a ChEMBL skill's `activity` command, or a ChEMBL MCP tool). The plugin's hook runs it automatically on each fetch and adds a summary to your context.
- On the **full** set of records before deciding anything. A single page (`--limit 10`) is not enough: fetch every page into one JSON or CSV file, then run:

```bash
consilience compare-table <file> --map chembl --pack bioactivity --out pooling/
```

For the assay conditions to be checked too, join assay fields from ChEMBL's `/assay` endpoint on `assay_chembl_id`:
- `confidence_score`, `assay_organism`, `assay_category`, `assay_tax_id`, `assay_strain`;
- `assay_tissue`, `assay_cell_type`, `assay_subcellular_fraction`.

Without them, the summary says which rules were not checked.

## How to read the result

- **`pool_valid` (records.csv):** true means the record may be pooled with the other records of its **condition class**, never across classes. Use `pooled_value` from `classes.csv` per class.
- **`pool_reason`:** why a record may not be pooled:
  - `excluded(BR1)`: ChEMBL flags the value as possibly wrong;
  - `excluded(BR2)`: the assay is not mapped to a single protein;
  - `excluded(BR3)`: approximate or missing relation;
  - `bound`: a `>` or `<` value, kept as a bound and never averaged;
  - `condition_not_stated(...)`: for example an undefined mutation;
  - `class_disagrees`: values in the class differ by more than 1 log unit.
- **Pairs across classes** are refused with the condition that differs, for example `not_comparable(assay_type)`.
- **Agreement:** within 0.3 log units (agree) or 1 log unit (within the floor). These are the thresholds Landrum & Riniker 2024 report against.

## Say this to the user

Report how many records may be pooled and the main reasons the others may not. Pool only within a class. Mention the receipt path: anyone can re-check it with `consilience verify <receipt>`.

## Limits

- **Not checked:** ATP or substrate concentration (mostly free text in ChEMBL).
- **Ki and IC50** are never pooled unless the user accepts the assumption `--assume ki_ic50_x2` (Ki × 2, Cheng–Prusoff with substrate at Km; Kalliokoski et al. 2013).
- **Repeat citations** of one measurement are kept.
