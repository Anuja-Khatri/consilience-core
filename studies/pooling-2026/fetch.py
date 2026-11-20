"""Fetch the study's ChEMBL records from the public ChEMBL web API, pinned and hashed.

    python studies/pooling-2026/fetch.py            # writes data/ (not committed)

For every target in targets.json: every activity of type IC50, Ki, Kd or EC50 with a
standard_value, ordered by activity_id; then every assay those activities use. Each raw
API page is saved as returned, and data/MANIFEST.json lists every file with its SHA-256,
the ChEMBL release the API reported, and the time of the fetch. join.py then builds the
study's input table from these files only.

ChEMBL data: CC BY-SA 3.0 (cite Mendez et al. 2019, NAR 47:D930; keep ChEMBL ids; show
the release number). The raw files stay local; the joined table is released with the
dataset (step 6).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
API = "https://www.ebi.ac.uk/chembl/api/data"
ACTIVITY_FIELDS = [
    "activity_id", "assay_chembl_id", "molecule_chembl_id", "parent_molecule_chembl_id",
    "target_chembl_id", "target_organism", "target_tax_id", "standard_type",
    "standard_relation", "standard_value", "standard_units", "pchembl_value",
    "data_validity_comment", "potential_duplicate", "assay_type", "bao_format",
    "assay_variant_mutation", "assay_variant_accession", "document_chembl_id",
    "document_year", "assay_description", "canonical_smiles"]
ASSAY_FIELDS = [
    "assay_chembl_id", "confidence_score", "assay_organism", "assay_category",
    "assay_tax_id", "assay_strain", "assay_tissue", "assay_cell_type",
    "assay_subcellular_fraction", "assay_parameters"]
PAGE = 1000
ASSAY_BATCH = 50


def get(url: str, tries: int = 6) -> bytes:
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                       "User-Agent": "consilience-study"})
            with urllib.request.urlopen(req, timeout=120) as f:
                return f.read()
        except Exception as exc:  # noqa: BLE001 (retried, then raised)
            if i == tries - 1:
                raise
            wait = 5 * (i + 1)
            print(f"  retry {i + 1} after {exc!r} (waiting {wait}s)", flush=True)
            time.sleep(wait)
    raise AssertionError


def save(path: Path, data: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"file": str(path.relative_to(DATA)), "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data)}


def main() -> int:
    spec = json.loads((HERE / "targets.json").read_text(encoding="utf-8"))
    targets = [spec["demonstration"]] + spec["panel"]
    status = json.loads(get(f"{API}/status.json"))
    manifest = {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "chembl_db_version": status.get("chembl_db_version"),
                "chembl_release_date": status.get("chembl_release_date"),
                "api": API, "targets": targets, "standard_types": spec["standard_types"],
                "files": [], "counts": {}, "missing_targets": []}
    print(f"ChEMBL {manifest['chembl_db_version']} ({manifest['chembl_release_date']})")
    assays: set = set()
    for t in targets:
        n_got, offset, total = 0, 0, None
        try:
            while True:
                q = urllib.parse.urlencode({
                    "target_chembl_id": t,
                    "standard_type__in": ",".join(spec["standard_types"]),
                    "standard_value__isnull": "false", "order_by": "activity_id",
                    "limit": PAGE, "offset": offset, "only": ",".join(ACTIVITY_FIELDS)})
                raw = get(f"{API}/activity.json?{q}")
                d = json.loads(raw)
                total = d["page_meta"]["total_count"]
                manifest["files"].append(save(DATA / "activity" / t / f"{offset:07d}.json", raw))
                acts = d["activities"]
                n_got += len(acts)
                assays.update(a["assay_chembl_id"] for a in acts if a.get("assay_chembl_id"))
                offset += PAGE
                if not acts or offset >= total:
                    break
        except Exception as exc:  # noqa: BLE001 (reported, never replaced)
            print(f"{t}: FAILED ({exc!r}); reported as missing", flush=True)
            manifest["missing_targets"].append({"target": t, "error": repr(exc)})
            continue
        manifest["counts"][t] = {"api_total": total, "fetched": n_got}
        print(f"{t}: {n_got} / {total}", flush=True)
        if n_got != total:
            print(f"{t}: count mismatch", flush=True)
    ids = sorted(assays)
    print(f"assays: {len(ids)}", flush=True)
    for i in range(0, len(ids), ASSAY_BATCH):
        batch = ids[i:i + ASSAY_BATCH]
        q = urllib.parse.urlencode({"assay_chembl_id__in": ",".join(batch),
                                    "limit": ASSAY_BATCH, "only": ",".join(ASSAY_FIELDS)})
        raw = get(f"{API}/assay.json?{q}")
        got = len(json.loads(raw)["assays"])
        if got != len(batch):
            print(f"  assay batch {i}: {got} of {len(batch)} returned", flush=True)
        manifest["files"].append(save(DATA / "assay" / f"{i:07d}.json", raw))
        if (i // ASSAY_BATCH) % 100 == 0:
            print(f"  assays {i}/{len(ids)}", flush=True)
    manifest["assays_requested"] = len(ids)
    (DATA / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
