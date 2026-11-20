---
description: Check which ChEMBL activity records in a file may be pooled, and why not
argument-hint: <file with ChEMBL activity records (JSON or CSV)>
---

Run the Consilience pooling check on `$ARGUMENTS`:

```bash
consilience compare-table "$ARGUMENTS" --map chembl --pack bioactivity --out consilience_receipts/check-pooling
```

Then summarise for the user:
- how many records may be pooled;
- the main reasons the others may not, from the "Pairs refused" and "left out by a rule" lines;
- the receipt path.

Pool values only within a condition class (`classes.csv`).
