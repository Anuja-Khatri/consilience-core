# The `bioactivity` pack

**For:** potency values (IC50, Ki, Kd, EC50…) gathered from ChEMBL or similar sources, before they are averaged, ranked or used to train a model.

**Question it answers:** which of these values may be pooled, and if not, why not?

**Use it with the `chembl` column map:**

```bash
consilience compare-table activities.json --map chembl --pack bioactivity --out result/
```

The map reads the ChEMBL web API's `/activity` JSON, or a CSV or SQL export with the same column names. Five conditions (BA3, BA4, BA6, BA7, BA9) and the confidence-score rule (BR2) use assay fields that are not in `/activity` records. Join them from `/assay` on `assay_chembl_id` first. The study scripts in [consilience-benchmarks](https://github.com/Anuja-Khatri/consilience-benchmarks) (`pooling-2026/`) show how.

If a column is missing from the table, its rule is **not applied**, and the summary lists it under "not checked".

## Conditions: when two values may be pooled

Two records may be pooled only if every one of these is equal. A field left empty on **both** records counts as equal, exactly as in Landrum & Riniker's "conditions hash". A field empty on one side only is `not_stated`.

| Rule | Field | Why |
|---|---|---|
| BA1 | `standard_type` | IC50, Ki, Kd and EC50 are different quantities. "In contrast to Ki values, IC50 data is assay specific" (Kalliokoski et al. 2013). Empty never counts as equal here |
| BA2 | `assay_type` | Binding (B) and functional (F) potencies differ systematically |
| BA3 | `assay_organism` | Landrum & Riniker 2024, conditions-hash field |
| BA4 | `assay_category` | Same source |
| BA5 | `assay_tax_id` | Same source |
| BA6 | `assay_strain` | Same source |
| BA7 | `assay_tissue` | Same source |
| BA8 | `assay_cell_type` | "the assays may be run using different cell types" (Landrum & Riniker 2024) |
| BA9 | `assay_subcellular_fraction` | Landrum & Riniker 2024, conditions-hash field |
| BA10 | `bao_format` | Single-protein, cell-based and organism-based formats |
| BA11 | `assay_variant_mutation` | "different variants of the same parent protein are assigned the same target ID in ChEMBL" (Landrum & Riniker 2024). The `chembl` map turns ChEMBL's "UNDEFINED MUTATION" (VARIANT_ID −1, "unclassified") into *not stated*, so such a record is never pooled, not even with another undefined mutation |

## Record rules: values left out before any comparison

| Rule | Field | Rule | Why |
|---|---|---|---|
| BR1 | `data_validity_comment` | Must be empty or "Manually validated" | ChEMBL flags likely-wrong values ("Outside typical range", "Potential author error", "Non standard unit type", "Potential missing data"…). "Manually validated" means the value was checked against the paper, so it is kept |
| BR2 | `confidence_score` | At least 9 | "any assay that does not have a confidence score value of 9 (indicating that the assay is assigned to a direct single target) is removed" (Landrum & Riniker 2024) |
| BR3 | `relation` | One of `=`, `<`, `<=`, `>`, `>=` | `~` (approximate), `>>`, other relations and a missing relation cannot be read exactly; nothing is guessed |
| BR4 | `value` | Present | Nothing to compare otherwise |

**A value with a unit that cannot be read** is `unparseable` for that record only (exit code 3). A value with no unit at all is excluded as "unit: not stated".

## Agreement: the defaults

When no tolerance is given, the pack's defaults apply, and the receipt records that it used them (`defaults_from_pack: true`).

- **Agree:** `|log10 a − log10 b| ≤ 0.3` (about 2-fold).
- **Within the floor:** `≤ 1.0` (10-fold).
- **Otherwise:** disagree.

**Where the numbers come from:**
- **Landrum & Riniker 2024** report their results against these two thresholds: with minimal curation, "almost 65% of the points differ by more than 0.3 log units, 27% differ by more than one log unit". These are the thresholds they report against, not a published agreement criterion, and the pack says so.
- **Kramer et al. 2012** estimate the standard deviation of public Ki data at 0.54 pKi, so one log unit is about two standard deviations.

Change them with `--log-tol` and `--log-floor`.

**Bounds** (">10 µM", "<1 nM") are compared as bounds:
- A value agrees with a bound it satisfies.
- Two bounds that can both hold are `undecidable_bounds`.
- A bound is never averaged into a pooled value.

## The opt-in assumption `ki_ic50_x2`

With `--assume ki_ic50_x2`, a Ki is multiplied by 2 and pooled with IC50 values measured under the same assay conditions. Affected records carry the assumption's name in every output.

- **The physics:** Cheng–Prusoff, with the substrate at its Km, gives IC50 = 2·Ki.
- **The evidence:** Kalliokoski et al. 2013 write, "For a broad dataset such as ChEMBL database a Ki- IC50 conversion factor of 2 was found to be the most reasonable". They observed a mean offset of 0.355 log units, a factor of 2.3.

It is off by default.

## What this pack does not check

- **ATP or substrate concentration.** It is mostly free text in ChEMBL, so two kinase IC50s that pass this pack may still differ in ATP concentration.
- **Assays whose description mentions "mutant", "mutation" or "variant" without a variant record.** Landrum & Riniker remove these by text search; this pack does not.
- **Repeat citations of one measurement** (`potential_duplicate = 1`). These are kept. Kramer et al. 2012 found repeat citations in 90% of pairs, so agreement statistics should be read with that in mind.

## Sources

- Landrum GA, Riniker S. *Combining IC50 or Ki Values from Different Sources Is a Source of Significant Noise.* J Chem Inf Model 2024. doi 10.1021/acs.jcim.4c00049 (PMC10934815).
- Kalliokoski T, Kramer C, Vulpetti A, Gedeck P. *Comparability of Mixed IC50 Data – A Statistical Analysis.* PLoS One 2013; 8:e61007 (PMC3628986).
- Kramer C, Kalliokoski T, Gedeck P, Vulpetti A. *The experimental uncertainty of heterogeneous public Ki data.* J Med Chem 2012; 55:5165–73. doi 10.1021/jm300131x.
- ChEMBL schema documentation, release 37 (data validity comments, confidence scores, variants, parent molecules).
