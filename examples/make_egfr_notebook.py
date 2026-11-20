"""Build examples/egfr_pooling.ipynb (run once; the notebook is committed).

    python examples/make_egfr_notebook.py
"""

from pathlib import Path

import nbformat as nbf

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells = [
    md("""# Before pooling EGFR potency values: which records may be pooled?

DeepMind's ChEMBL agent skill (`google-deepmind/science-skills`, `skills/chembl_database`)
documents this example call:

```
uv run scripts/chembl_api.py activity --filter target_chembl_id=CHEMBL203 standard_type=IC50 --limit 5 --normalize --output /tmp/egfr_normalized.json
```

`--normalize` converts every value to nM. That makes the **units** comparable. This
notebook shows the next step: which of those records may be **pooled**, why the others may
not, and whether the poolable ones agree, using `consilience compare-table` with the
`bioactivity` pack. Every result has a receipt anyone can re-run.

Part 1 runs on a small live fetch (the same API call, made directly). Part 2 runs on the
full EGFR set from the study (`studies/pooling-2026`), all 28,741 IC50, Ki, Kd and EC50
records."""),
    code("""import json, urllib.request, urllib.parse
from pathlib import Path
from consilience import compare_table, verify, __version__
print("consilience", __version__)"""),
    md("## Part 1: one page, as an agent would fetch it"),
    code("""q = urllib.parse.urlencode({"target_chembl_id": "CHEMBL203", "standard_type": "IC50",
                            "limit": 20, "format": "json"})
url = "https://www.ebi.ac.uk/chembl/api/data/activity.json?" + q
try:
    with urllib.request.urlopen(url, timeout=120) as f:
        page = json.load(f)
    print(len(page["activities"]), "of", page["page_meta"]["total_count"], "records")
except Exception as exc:            # the public API is sometimes slow or down
    page = None
    print("ChEMBL API not reachable now:", exc)"""),
    code("""if page:
    r = compare_table(page["activities"], map="chembl", pack="bioactivity", out="egfr_page")
    print(r.text)"""),
    md("""A single page is not enough to decide anything: the summary says so, and it says
which assay conditions could not be checked because they live in ChEMBL's `/assay`
records. Part 2 uses the full set, joined with its assay fields."""),
    md("## Part 2: all EGFR records (the study's input)"),
    code("""candidates = [Path("../studies/pooling-2026/work/input/CHEMBL203.csv"),
              Path("chembl37-pooling-check/targets/CHEMBL203/CHEMBL203.csv")]
egfr = next((p for p in candidates if p.is_file()), None)
print(egfr or "EGFR input not found: run studies/pooling-2026 fetch.py and join.py, or "
      "download the released dataset (chembl37-pooling-check)")"""),
    code("""r = compare_table(egfr, map="chembl", pack="bioactivity", out="egfr_full")
print(r.text)
print("exit code:", r.exit_code)"""),
    md("""### One molecule, several assays

Pick the molecule with the most condition classes and look at its classes: each class is
a set of records measured under the same assay conditions; values are pooled only within
a class."""),
    code("""from collections import Counter
n_cls = Counter(c["key"] for c in r.classes)
key, k = n_cls.most_common(1)[0]
print("molecule, target:", key, "-", k, "condition classes")
rows = [c for c in r.classes if c["key"] == key]
rows.sort(key=lambda c: -c["n_records"])
for c in rows[:8]:
    cond = {f: v for f, v in c["conditions"].items() if v}
    print(f'{c["class"]:>4}  n={c["n_records"]:<3} {c["consensus"]:<12} pooled={c["pooled_value"]!s:<22} '
          f'{c["pooled_unit"] or "":<4} {cond}')"""),
    code("""# what unit conversion alone would do: average every value of this molecule in nM
UNIT = {"nm": 1.0, "um": 1e3, "µm": 1e3, "mm": 1e6, "m": 1e9, "pm": 1e-3, "fm": 1e-6}
import csv, math, statistics
vals = []
with open(egfr, encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        if (row["parent_molecule_chembl_id"], row["target_chembl_id"]) == key:
            u = row["standard_units"].strip().lower()
            if row["standard_value"] and u in UNIT:
                vals.append(float(row["standard_value"]) * UNIT[u])
print(len(vals), "values; geometric mean of all, ignoring assay and relation:",
      round(10 ** statistics.mean(math.log10(v) for v in vals if v > 0), 3), "nM")"""),
    md("""### Why pairs are refused, across the whole set"""),
    code("""for reason, count in list(r.summary["pairs_across_classes_by_reason"].items())[:10]:
    print(f"{count:>9,}  {reason}")"""),
    md("""### Check it

The receipt records the input's SHA-256, the pack, the options and the hash of every
output. `verify` re-runs everything from the input file."""),
    code("""v = verify("egfr_full/receipt.json")
print("ok" if v.ok else "FAILED")
for step in v.steps:
    print(step)"""),
    md("""## What this does not do

- It does not check ATP or substrate concentration (mostly free text in ChEMBL).
- It does not decide which class to use when a molecule has several; that is the user's
  choice (`classes.csv`).
- Ki and IC50 are never pooled unless you switch on `assume=["ki_ic50_x2"]`.

Rules and sources: `docs/packs/bioactivity.md`. Study and all numbers:
`studies/pooling-2026/results/RESULTS.md`."""),
]

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3",
                                "language": "python"}
out = Path(__file__).resolve().parent / "egfr_pooling.ipynb"
nbf.write(nb, out)
print("wrote", out)
