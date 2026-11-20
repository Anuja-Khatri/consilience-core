"""Package the released dataset (build step 6): files only, nothing is uploaded.

    python studies/pooling-2026/package_dataset.py

Writes release/chembl37-pooling-check/:
- targets/<target>/: the exact input table <target>.csv, and the pooling check's
  records.csv, classes.csv, summary.json and receipt.json (pairs.csv for EGFR);
- all_records.csv: every record of every target with pool_valid and pool_reason;
- README.md (the data card), croissant.json (Croissant 1.0 metadata), LICENSE (ChEMBL's
  CC BY-SA 3.0, as distributed with ChEMBL 37), ATTRIBUTION.md, SHA256SUMS.

Then it re-runs `consilience verify` on every receipt from the packaged copy.
Uploading to Hugging Face and Zenodo is the owner's step.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

from consilience import verify

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
REL = HERE / "release" / "chembl37-pooling-check"
LICENSE_URL = "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE"
LICENSE_FALLBACK = "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/LICENSE"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    res = json.loads((HERE / "results" / "results.json").read_text(encoding="utf-8"))
    if REL.exists():
        shutil.rmtree(REL)
    (REL / "targets").mkdir(parents=True)
    targets = [r["target"] for r in res["per_target"]]
    all_rows, header = [], None
    for t in targets:
        src = WORK / "out" / "P" / t
        dst = REL / "targets" / t
        dst.mkdir()
        shutil.copy2(WORK / "input" / f"{t}.csv", dst / f"{t}.csv")
        for n in ("records.csv", "classes.csv", "summary.json", "receipt.json", "pairs.csv"):
            if (src / n).is_file():
                shutil.copy2(src / n, dst / n)
        with (dst / "records.csv").open(encoding="utf-8", newline="") as fh:
            rd = csv.reader(fh)
            h = next(rd)
            if header is None:
                header = h
            for row in rd:
                all_rows.append(row)
    with (REL / "all_records.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(all_rows)
    for url in (LICENSE_URL, LICENSE_FALLBACK):
        try:
            with urllib.request.urlopen(url, timeout=60) as f:
                (REL / "LICENSE").write_bytes(f.read())
            break
        except Exception:  # noqa: BLE001
            continue
    else:
        raise SystemExit("could not fetch ChEMBL's LICENSE file")
    (REL / "ATTRIBUTION.md").write_text(ATTRIBUTION.format(**res["chembl"]), encoding="utf-8")
    (REL / "README.md").write_text(card(res, len(all_rows)), encoding="utf-8")
    (REL / "croissant.json").write_text(json.dumps(croissant(res), indent=1) + "\n",
                                        encoding="utf-8")
    sums = sorted((str(p.relative_to(REL)), sha(p)) for p in REL.rglob("*") if p.is_file())
    (REL / "SHA256SUMS").write_text("".join(f"{h}  {n}\n" for n, h in sums), encoding="utf-8")
    bad = []
    for t in targets:
        v = verify(REL / "targets" / t / "receipt.json")
        if not v.ok:
            bad.append((t, v.steps))
    print(f"packaged {len(targets)} targets, {len(all_rows)} records; "
          f"receipts verified from the packaged copy: {len(targets) - len(bad)}/{len(targets)}")
    for b in bad:
        print("  FAILED", b)
    return 1 if bad else 0


ATTRIBUTION = """# Attribution

The records in this dataset come from ChEMBL, release {db_version} ({release_date}),
retrieved through the ChEMBL web services. ChEMBL is licensed under the Creative Commons
Attribution-ShareAlike 3.0 Unported licence (see LICENSE). ChEMBL ids are kept unchanged
and the release number is shown, as ChEMBL asks.

Primary citation for ChEMBL:
Mendez D, Gaulton A, Bento AP, et al. ChEMBL: towards direct deposition of bioassay data.
Nucleic Acids Res. 2019; 47(D1):D930-D940. doi 10.1093/nar/gky1075

The added columns (record_status, condition_class, class_consensus, class_stated,
pool_valid, pool_reason, the classes and pairs files) are made by the consilience pooling
check and are shared under the same licence (CC BY-SA 3.0).

Targets: EGFR (CHEMBL203), the example in DeepMind's ChEMBL agent skill
(google-deepmind/science-skills), and the 29 targets of the 30 MoleculeACE benchmark
sets (van Tilborg D, Alenicheva A, Grisoni F. Exposing the limitations of molecular
machine learning with activity cliffs. J Chem Inf Model 2022).
"""


def card(res: dict, n_records: int) -> str:
    egfr = next(r for r in res["per_target"] if r["target"] == "CHEMBL203")
    m1 = egfr["M1"]
    return f"""---
license: cc-by-sa-3.0
pretty_name: ChEMBL {res['chembl']['db_version']} pooling check (EGFR + 29 MoleculeACE targets)
tags: [chemistry, bioactivity, chembl, data-quality, drug-discovery]
---

# ChEMBL {res['chembl']['db_version']} pooling check

Every IC50, Ki, Kd and EC50 record with a value for EGFR (CHEMBL203) and the 29 targets
of the MoleculeACE benchmark sets ({n_records} records), each with a **`pool_valid`**
column: may this record be pooled with the others of its condition class, and if not,
why not.

## What `pool_valid` means

True when the record is an exact value (not a ">" or "<" bound), not excluded by a rule,
every assay condition of its class is stated, and the values in its class agree within
1 log unit (or it is alone in its class). It means "may be pooled **with the other
records of its condition class**" (`condition_class`), never across classes. A molecule
and target can have several valid classes (for example a biochemical and a cell-based
assay); choosing between them is the user's decision.

`pool_reason` names why it is false: `excluded(BR1)` (ChEMBL flags the value as possibly
wrong), `excluded(BR2)` (assay not mapped to a single protein, confidence < 9),
`excluded(BR3)` (approximate or missing relation), `bound`,
`condition_not_stated(...)` (for example an undefined mutation), `class_disagrees`.

Conditions that must match (Landrum & Riniker 2024, J Chem Inf Model, conditions hash):
standard_type, assay_type, assay_organism, assay_category, assay_tax_id, assay_strain,
assay_tissue, assay_cell_type, assay_subcellular_fraction, bao_format, variant. Full
rules and sources: docs/packs/bioactivity.md in github.com/Anuja-Khatri/consilience-core.

## Files

- `all_records.csv`: every record, with its status, class, consensus and `pool_valid`.
- `targets/<target>/<target>.csv`: the exact input (ChEMBL activity fields joined with
  assay fields), `records.csv`, `classes.csv` (pooled value per class), `summary.json`,
  `receipt.json`; `pairs.csv` for EGFR.
- `SHA256SUMS`, `croissant.json`, `LICENSE`, `ATTRIBUTION.md`.

## Check it yourself

```
pip install "consilience>=0.2"
consilience verify targets/CHEMBL203/receipt.json
```

re-runs the check from the input file and confirms every output's hash.

## Example (EGFR)

Of {m1['r0_comparable_pairs']} pairs of records for the same molecule that unit
conversion alone treats as comparable, {m1['pairs_paired_by_p']} are pairs of records the
check keeps, and it refuses {m1['refused']} of those
({(m1['refused_share_of_paired'] or 0):.1%}) because a named assay condition differs or
is not stated. See studies/pooling-2026 for the preregistered study and all numbers.

## Limits

- ATP or substrate concentration is not checked (mostly free text in ChEMBL).
- Repeat citations of one measurement (`potential_duplicate`) are kept.
- Ki and IC50 are never pooled here (the opt-in assumption `ki_ic50_x2` was not used).
- The thresholds 0.3 and 1.0 log units are those Landrum & Riniker (2024) report
  against, not a published agreement criterion.

## Licence

CC BY-SA 3.0, as ChEMBL. See LICENSE and ATTRIBUTION.md.
"""


def croissant(res: dict) -> dict:
    fields = ["row", "id", "parent_molecule_chembl_id", "target_chembl_id", "value",
              "relation", "unit", "record_status", "condition_class", "class_consensus",
              "class_stated", "pool_valid", "pool_reason", "assumption"]
    types = {"row": "sc:Integer", "pool_valid": "sc:Boolean", "class_stated": "sc:Boolean"}
    return {
        "@context": {"@language": "en", "@vocab": "https://schema.org/",
                     "cr": "http://mlcommons.org/croissant/", "sc": "https://schema.org/",
                     "dct": "http://purl.org/dc/terms/",
                     "conformsTo": "dct:conformsTo", "data": {"@id": "cr:data", "@type": "@json"},
                     "field": "cr:field", "fileObject": "cr:fileObject",
                     "recordSet": "cr:recordSet", "source": "cr:source",
                     "extract": "cr:extract", "column": "cr:column",
                     "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
                     "md5": "cr:md5"},
        "@type": "sc:Dataset",
        "conformsTo": "http://mlcommons.org/croissant/1.0",
        "name": "chembl37-pooling-check",
        "description": ("ChEMBL bioactivity records (IC50, Ki, Kd, EC50) for EGFR and the "
                        "29 MoleculeACE targets, each marked pool_valid by the consilience "
                        "pooling check, with the named reason when it may not be pooled."),
        "license": "https://creativecommons.org/licenses/by-sa/3.0/",
        "version": "1.0.0",
        "citeAs": "ChEMBL release " + str(res["chembl"]["db_version"]) + "; Mendez et al. 2019",
        "distribution": [{"@type": "cr:FileObject", "@id": "all_records.csv",
                          "name": "all_records.csv", "contentUrl": "all_records.csv",
                          "encodingFormat": "text/csv",
                          "sha256": sha(REL / "all_records.csv")}],
        "recordSet": [{"@type": "cr:RecordSet", "@id": "records", "name": "records",
                       "field": [{"@type": "cr:Field", "@id": f"records/{f}", "name": f,
                                  "dataType": types.get(f, "sc:Text"),
                                  "source": {"fileObject": {"@id": "all_records.csv"},
                                             "extract": {"column": f}}}
                                 for f in fields]}],
    }


if __name__ == "__main__":
    sys.exit(main())
