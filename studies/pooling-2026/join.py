"""Build the study's input tables from the fetched ChEMBL pages (and nothing else).

    python studies/pooling-2026/join.py

Checks every file in data/MANIFEST.json against its SHA-256. Then it joins each activity
with its assay (on assay_chembl_id) and writes one CSV per target:
work/input/<target>.csv, rows ordered by activity_id. Values are written exactly as the
API returned them (text), so the written digits are kept. work/INPUT.json lists each
file's SHA-256 and row count.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
WORK = HERE / "work"
sys.path.insert(0, str(HERE))
from fetch import ACTIVITY_FIELDS, ASSAY_FIELDS  # noqa: E402

ASSAY_EXTRA = [f for f in ASSAY_FIELDS if f != "assay_chembl_id"]
COLUMNS = ACTIVITY_FIELDS + ASSAY_EXTRA


def text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(v)


def main() -> int:
    man = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    for e in man["files"]:
        b = (DATA / e["file"]).read_bytes()
        if hashlib.sha256(b).hexdigest() != e["sha256"]:
            raise SystemExit(f"hash mismatch: {e['file']}")
    print(f"{len(man['files'])} files verified against MANIFEST.json")
    assays = {}
    for e in man["files"]:
        if e["file"].startswith("assay/"):
            for a in json.loads((DATA / e["file"]).read_bytes())["assays"]:
                assays[a["assay_chembl_id"]] = a
    out_dir = WORK / "input"
    out_dir.mkdir(parents=True, exist_ok=True)
    index = {"chembl_db_version": man["chembl_db_version"],
             "chembl_release_date": man["chembl_release_date"], "files": {},
             "missing_targets": man["missing_targets"], "activities_without_assay": 0}
    for t in man["targets"]:
        if any(m["target"] == t for m in man["missing_targets"]):
            continue
        acts = []
        for e in sorted((e for e in man["files"] if e["file"].startswith(f"activity/{t}/")),
                        key=lambda e: e["file"]):
            acts.extend(json.loads((DATA / e["file"]).read_bytes())["activities"])
        acts.sort(key=lambda a: a["activity_id"])
        blank = sum(1 for a in acts if not (a.get("assay_chembl_id") and a.get("target_chembl_id")))
        if blank:
            raise SystemExit(f"{t}: {blank} activities with blank assay/target fields "
                             "(a damaged API page); run fetch.py --recover first")
        ids = [a["activity_id"] for a in acts]
        if len(ids) != len(set(ids)):
            raise SystemExit(f"{t}: duplicate activity ids across pages")
        p = out_dir / f"{t}.csv"
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(COLUMNS)
            for a in acts:
                asy = assays.get(a.get("assay_chembl_id"))
                if asy is None:
                    index["activities_without_assay"] += 1
                    asy = {}
                w.writerow([text(a.get(c)) for c in ACTIVITY_FIELDS]
                           + [text(asy.get(c)) for c in ASSAY_EXTRA])
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        index["files"][t] = {"file": f"input/{t}.csv", "rows": len(acts), "sha256": h}
        print(f"{t}: {len(acts)} rows")
    (WORK / "INPUT.json").write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
