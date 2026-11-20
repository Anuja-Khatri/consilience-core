# The `pka` pack (second domain)

**For:** measured acid dissociation constants (pKa) of the same molecule and dissociation step, collected from many sources.

**Question it answers:** which of these values may be pooled, and do they agree?

**Use it with the `iupac_pka` column map**, made for the IUPAC Digitized pKa Dataset:

```bash
consilience compare-table iupac_high-confidence_v2_4.csv --map iupac_pka --pack pka \
    --abs-tol 0.02 --floor 0.2 --out result/
```

**Grouping:** by `InChI` (the molecule) and `pka_type` (the dissociation step, for example `pKa1` or `pKaH1`). Values are pure numbers.

## Conditions

| Rule | Field | When two values may be pooled |
|---|---|---|
| PK1 | `temperature` (the dataset's `T`, in °C) | Same temperature. A temperature written "not_stated" is not stated and is never pooled |
| PK2 | `cosolvent` | Same cosolvent. Empty on both counts as the same |
| PK3 | `pressure` | Same pressure. Empty on both counts as the same (ordinary pressure) |

## Record rules

| Rule | Field | Rule |
|---|---|---|
| PKR1 | `assessment` | IUPAC's own grade must be Reliable, Approximate or Uncertain. "Very uncertain", other grades and no grade are left out |
| PKR2 | `value` | Present |

## No default tolerance

No cited source on inter-laboratory pKa reproducibility was found for this pack, so it has no defaults. Give `--abs-tol` and `--floor` yourself. The example in `examples/pka_pooling.py` states the values it uses as a choice, not a claim.

## What this pack does not check

- **Ionic strength.** In the IUPAC dataset it is only in free-text remarks.
- **The measurement method.** It is deliberately not a condition: different methods measuring the same pKa are what pooling is for. The methods present are listed for each condition class.
- **Cosolvent.** The dataset fills `cosolvent` only "if able to be parsed from remarks", so an empty cosolvent means "none parsed", not proven pure water.

## Licence of the data

The IUPAC Digitized pKa Dataset is CC BY-NC 4.0: "Reproduced by permission of International Union of Pure and Applied Chemistry". Nothing derived from it is committed or released here. The example downloads it at a pinned commit and checks its SHA-256.
