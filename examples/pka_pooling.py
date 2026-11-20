"""Second domain: which measured pKa values may be pooled, and do they agree?

    python examples/pka_pooling.py [--out pka_out]

Downloads the IUPAC Digitized pKa Dataset v2.4a at a pinned commit, checks its SHA-256,
and runs the same engine command used for bioactivity:

    consilience compare-table iupac_high-confidence_v2_4.csv --map iupac_pka --pack pka \
        --abs-tol 0.02 --floor 0.2

The tolerance (0.02 pK units) and floor (0.2 pK units) are this example's choice, not a
published criterion: the pka pack has no defaults because no cited source on
inter-laboratory pKa reproducibility was found.

Data licence: CC BY-NC 4.0. "Reproduced by permission of International Union of Pure and
Applied Chemistry." Zheng JW, Lafontant-Joseph O. IUPAC Digitized pKa Dataset, v2.4a
(2026), doi 10.5281/zenodo.7236452. Nothing derived from it is committed or released.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from consilience.table import compare_table

COMMIT = "a1e958d264edf35ddf548ed594684d60a73b8f08"
URL = ("https://raw.githubusercontent.com/IUPAC/Dissociation-Constants/"
       f"{COMMIT}/iupac_high-confidence_v2_4.csv")
SHA256 = "5cd5ca8bda1952be8b223bb1fbe681780de9335617f9f7c0ee2c8f8c6f01cbf3"


def fetch(dest: Path) -> Path:
    if not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL, timeout=120) as f:
            dest.write_bytes(f.read())
    got = hashlib.sha256(dest.read_bytes()).hexdigest()
    if got != SHA256:
        raise SystemExit(f"{dest}: SHA-256 {got}, expected {SHA256}; not the pinned file")
    return dest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="pka_out", help="output directory")
    ap.add_argument("--data", default="pka_data/iupac_high-confidence_v2_4.csv")
    args = ap.parse_args(argv)
    path = fetch(Path(args.data))
    r = compare_table(path, map="iupac_pka", pack="pka", abs_tol="0.02", floor="0.2",
                      out=args.out)
    print(r.text)
    s = r.summary
    multi_groups = s["groups_with_more_than_one_class"]
    print(json.dumps({"records": s["records"], "groups": s["groups"],
                      "groups_with_more_than_one_class": multi_groups,
                      "pairs_within_classes": s["pairs_within_classes"],
                      "class_consensus": s["class_consensus"],
                      "pool_valid_records": s["pool_valid_records"]}, indent=1))
    print(f"receipt: {args.out}/receipt.json (consilience verify {args.out}/receipt.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
