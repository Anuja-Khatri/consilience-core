# Preregistration: how pooling choices change potency datasets

**Fixed on 20 Nov 2026, before any full run of the analysis.** It was committed and pushed while the data fetch was still running, and before `run_study.py` existed. Changes after this commit are added below as dated amendments; nothing above them is edited.

## Question

When an AI agent or a person gathers potency values (IC50, Ki, Kd, EC50) from ChEMBL for the same molecule and target, how many of the comparisons that **unit conversion alone** treats as comparable would a condition-aware check refuse, and for what named reasons? And how much does the pooled potency of a molecule change?

## What we already know (disclosed)

On 19 Nov 2026 we looked at counts for DeepMind's documented example (EGFR, CHEMBL203, IC50) through the ChEMBL API:
- 26,600 records;
- 3,309 with `>`;
- 2,067 with `<`.

On 20 Nov (step 0) we looked at one page of 1,000 EGFR activities (all types) to check field meanings:
- relations `=` 755, `>` 203, `<` 6, empty 36;
- 13,960 EGFR activities carry a variant mutation, 199 of them "UNDEFINED MUTATION" in that page.

**What this means for the stop rule.** We therefore expect the stop rule on M1 to pass, so it is a guard against an implementation surprise, not a test of the idea. No numbers for the 29 panel targets have been looked at.

## Data

- **Source:** ChEMBL 37 (release 2026-05-01), fetched by `fetch.py` from the public web API. Every raw page is hashed in `data/MANIFEST.json`.
- **Records:** every activity of type IC50, Ki, Kd or EC50 with a `standard_value`, for:
  - **EGFR, CHEMBL203:** the demonstration, because it is the example in DeepMind's ChEMBL skill (`google-deepmind/science-skills` @370f8f3);
  - **the panel:** the 29 targets of the 30 MoleculeACE benchmark sets (van Tilborg et al. 2022; `molML/MoleculeACE` @7e6de0b), listed in `targets.json`.
- **Join:** `join.py` joins each activity with its assay (on `assay_chembl_id`), adding `confidence_score`, `assay_organism`, `assay_category`, `assay_tax_id`, `assay_strain`, `assay_tissue`, `assay_cell_type`, `assay_subcellular_fraction` and `assay_parameters`. The result is one CSV, `work/pooling_input.csv`, which is the exact input to every run below and is released with the dataset.
- **Missing targets:** a target the API cannot serve is reported as missing, never replaced.

## The three ways of pooling compared

1. **R0, units only.** DeepMind's skill `_normalize_activity` (`skills/chembl_database/scripts/chembl_api.py`, 370f8f3), re-implemented exactly:
   - lower-case `standard_units`;
   - convert with `UNIT_CONVERSION_TO_NM` (nm, um, µm, mm, m, pm, fm);
   - `float(standard_value)`.

   It does not read `standard_relation`, the measurement type or the assay. Any two records of the same group that both get an nM value are "comparable under R0".
2. **R1, averaging across types.** chembl-downloader's `get_target_smi_df` default (`cthoyt/chembl-downloader` @14e3aee, `src/chembl_downloader/contrib.py`, `aggregate="mean"`): the mean of `pchembl_value` per (`canonical_smiles`, `molecule_chembl_id`), across all measurement types the query returns. Records without a `pchembl_value` drop out. ChEMBL fills `pchembl_value` only for exact (`=`) values.
3. **P, the pooling check.**

   ```
   consilience compare-table work/pooling_input.csv --map chembl --pack bioactivity
   ```

   - Group key: parent molecule + target.
   - Defaults: agree ≤ 0.3, floor ≤ 1.0 log units.
   - No assumption switched on.
   - **P-a** is the same with `--assume ki_ic50_x2`.

   Engine: `consilience` at the commit recorded with the results.

## Measures

Each is reported for EGFR alone, for the 29-target panel, and per target.

- **M1. Refused comparisons.**
  - Population: pairs of records in the same group (parent molecule + target) that R0 treats as comparable (both get an nM value).
  - Headline: the share P refuses, meaning pairs P marks `not_comparable` (different condition class) or `not_stated` (a condition not stated), with counts by first named reason.
  - Reported separately, not in the headline:
    - R0-comparable pairs where at least one record is excluded by a record rule or unparseable (by rule);
    - `undecidable_bounds` pairs.
- **M2. Bounds treated as numbers.** Of the records R0 gives an nM value, the share whose `standard_relation` is not `=` (`>`, `<`, `>=`, `<=`, `~`, and others reported separately), plus the share with no relation.
- **M3. Shift in pooled potency.**
  - P is also run with key `molecule_chembl_id` + target, R1's own key, so that both are compared on the same groups.
  - For each group where both have a value: R1's mean pChEMBL against −log10(molar) of P's pooled value for the **largest valid class**. That is the class with the most usable records and consensus `agree`, `within_floor` or `single`; ties go to the lowest class id; only molar units.
  - Reported: the share of groups shifting by more than 0.3 and more than 1.0 log units, and the median shift. Also the number of groups where R1 gives a value but P has no valid class, with the reasons.
- **M4. Agreement inside classes** (sanity check, not a finding).
  - Among P's within-class pairs that compare two exact values: the shares that agree, are within the floor, and disagree.
  - Reported twice: with all pairs, and without pairs where either record has `potential_duplicate = 1` (Kramer et al. 2012 found repeat citations in 90% of public Ki pairs).
  - Set beside Landrum & Riniker 2024's figures, as context only.
- **M5. What was left out, and what cannot be checked.**
  - Records excluded, by rule.
  - Kinase targets (EGFR, ABL1, CLK4, GSK3β, JAK1, JAK2, PIM1, PIK3CA): the share of activities whose `assay_parameters` mention ATP, and the share whose description mentions ATP.
  - Cell-based assays (`assay_type` F): the share with `assay_cell_type` stated.
  - Records whose assay description mentions mutant, mutation or variant with no variant recorded (Landrum & Riniker's text rule, reported only).
- **M1 and M3 also for P-a**, to show the effect of the Ki ×2 assumption.

## Stop rule

If M1 on EGFR is below 2%, stop: report this honestly and do not release the study as a finding.

## Second-way check

`check_independent.py` recomputes M1, M2 and M3 for EGFR and the panel with pandas, without importing `consilience`, from the same `work/pooling_input.csv`. It is a separate implementation of:
- the record rules;
- the condition classes;
- the log-scale comparison (bounds and stated precision included);
- the consensus;
- the pooled value.

Every mismatch is resolved and logged in `VERIFICATION_LOG.md` before any number is reported.

## Framing

The study is about how pooling choices change potency datasets. It credits ChEMBL, DeepMind's ChEMBL skill, chembl-downloader and MoleculeACE. It starts from DeepMind's documented call because that is the documented workflow. It does not say that any of these is wrong: R0 and R1 do what they document.

## Amendments

- **20 Nov 2026 (before any analysis run): how the data is fetched, not which data.** The public API failed on deep offsets: offset 5,000 and beyond for EGFR timed out or returned HTTP 500, on four tries with no other load. So `fetch.py` now asks for each target in slices by document year, and further by measurement type when a year is still large, so that no slice needs a deep offset. The set of records is the same as defined above. Completeness is checked exactly: for each target, the slices' counts must add up to the target's total count, and the union of activity ids must have that size. Incomplete targets are reported, never replaced.
- **20 Nov 2026, AFTER the first full analysis run (disclosed; see VERIFICATION_LOG.md).** Three changes, each forced by a problem the second-way check found. None changes a measure's definition.
  - **(a)** The bioactivity conditions are compared as text (`as_text`). A cell line such as "3T3-L1" had been read as a quantity, making records unreadable.
  - **(b)** M3's "largest valid class … only molar units" is applied as written: the choice is among molar classes. The first script chose among all units and then skipped non-molar ones.
  - **(c)** 80 API pages that came back with blank assay and target fields are refused and fetched again. The first run's numbers were computed on them, are void, and are not reported as results.

