"""NOTE (v2): written against the v1 exporter and not updated; see CANDIDATES.md.

Prepare (do not publish) candidate testable-disagreement records from the public
cross-theory demo (consilience-demo.netlify.app), and list everything that does not
qualify with the reason.

The demo's results are public JSON files served by the demo site; they are not in a
public git repository at a pinned commit, and the matcher that produced them is not
public. So these candidates are NOT record envelopes and cannot go through
``consilience export --nanopub`` yet. This script writes:

  candidates/theories/records/<id>.json     the candidate record, in the testable-
                                            disagreement template's fields
  candidates/theories/preview/<id>.ttl      the assertion graph only, built by the
                                            exporter's own mapping (no provenance, no
                                            publication info, not a nanopub)
  candidates/theories/index.json            what qualified, what did not, and why

    curl -sS -o <dir>/iitxgnwt_judge.json \
        https://consilience-demo.netlify.app/results/iitxgnwt_judge.json
    (likewise iitxorch-or_judge.json and iitxgnwt_vs_cogitate.json)
    python scripts/build_theory_candidates.py --snapshot-dir <dir>

The snapshot files' SHA-256 values are checked against the ones recorded below, so a
changed demo is noticed rather than silently used. The snapshots themselves are not
committed. No model identifier from the snapshots is copied into any output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from consilience.export import nanopub as X  # noqa: E402
from consilience.receipts import Envelope  # noqa: E402

DEMO = "https://consilience-demo.netlify.app/results/"
SNAPSHOT_DATE = "2026-11-17"
SNAPSHOTS = {
    "iitxgnwt_judge.json": "91f4bbec746ea145d69b9aa6e05752a4dd12547e622a277cdcdf1a573f3acfdf",
    "iitxorch-or_judge.json": "63cdc761108c1619021ec844df80f5ede826972e0ac5599d568549a1026c988f",
    "iitxgnwt_vs_cogitate.json": "51f416fd7c7465c519aadf32231b2889cc303343b6cfae78f9a29106d887e369",
}
# Fields copied from a claim node. Anything else (including the extractor field) is
# left out on purpose.
NODE_FIELDS = ("claim_id", "theory", "axis", "value", "polarity", "statement")
OBSERVABLE_WORDS = {
    "regional_decoding": "regional decoding",
    "connectivity_metrics": "connectivity metrics",
    "ignition_signature": "ignition signature",
    "temporal_generalization": "temporal generalisation",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot-dir", required=True)
    ap.add_argument("--out", default=str(ROOT / "candidates" / "theories"))
    args = ap.parse_args()
    snap = Path(args.snapshot_dir)
    for name, want in SNAPSHOTS.items():
        got = sha(snap / name)
        if got != want:
            raise SystemExit(f"snapshot changed: {name} hashes to {got}, expected {want}")

    out = Path(args.out)
    (out / "records").mkdir(parents=True, exist_ok=True)
    (out / "preview").mkdir(parents=True, exist_ok=True)
    index = {"snapshot_date": SNAPSHOT_DATE, "snapshots": {DEMO + k: v for k, v in SNAPSHOTS.items()},
             "candidates": [], "not_eligible": []}

    for fname in ("iitxgnwt_judge.json", "iitxorch-or_judge.json"):
        j = json.loads((snap / fname).read_text())
        url = DEMO + fname
        nodes = {n["claim_id"]: n for side in ("left", "right") for n in j[side]["nodes"]}
        for c in j["correspondences"]:
            index["not_eligible"].append({
                "source": url, "kind": "correspondence", "pair": j["pair"],
                "left_ids": c["left_ids"], "right_ids": c["right_ids"], "demo_grade": c["grade"],
                "demo_status": c["status"],
                "reason": "the demo marks every correspondence as a draft, and its grade labels "
                          "('generative', 'partial') are not the four-rung ladder the graded-"
                          "correspondence template needs; publishing it would present a draft "
                          "as a verdict"})
        for f in j["forks"]:
            pid = f"{f['left_ids'][0]}|{f['right_ids'][0]}"
            base = {"source": url, "kind": "fork", "pair_id": pid, "axis": f["axis"],
                    "decidability": f["decidability"]}
            if len(f["left_ids"]) != 1 or len(f["right_ids"]) != 1:
                index["not_eligible"].append({**base, "reason": "not a single claim pair"})
                continue
            if f["decidability"] != "now":
                index["not_eligible"].append({**base, "reason": (
                    "the demo rules this disagreement not decidable with current instruments; "
                    "the template says 'testable now with instrument Y'")})
                continue
            sk = f.get("sketch")
            if not sk or not sk.get("shared_observables"):
                index["not_eligible"].append({**base, "reason": (
                    "decidable now, but the demo names no shared observable for it (the "
                    "disagreement is about what to measure), so there is no instrument to name")})
                continue
            obs = [OBSERVABLE_WORDS.get(o, o.replace("_", " ")) for o in sk["shared_observables"]]
            instrument = "shared observable: " + " and ".join(obs)
            a, b = nodes[f["left_ids"][0]], nodes[f["right_ids"][0]]
            rid = f"disagreement-{pid.replace('|', '--')}"
            rec = {
                "kind": "fork",
                "pair_id": pid,
                "claim_a_id": a["claim_id"],
                "claim_b_id": b["claim_id"],
                "axis": f["axis"],
                "claim_a_value": f["left_value"],
                "claim_b_value": f["right_value"],
                "polarity_opposed": f["polarity_opposed"],
                "type_divergence": f["type_divergence"],
                "testability": "testable_now",
                "instrument": instrument,
                "claim_a": {k: a[k] for k in NODE_FIELDS},
                "claim_b": {k: b[k] for k in NODE_FIELDS},
                "claim_a_locators": [p["locator"] for p in a.get("prov", [])],
                "claim_b_locators": [p["locator"] for p in b.get("prov", [])],
                "source": {"url": url, "sha256": SNAPSHOTS[fname], "retrieved": SNAPSHOT_DATE},
                "status": "candidate, not exportable yet: no pinned public commit, matcher code not public",
            }
            (out / "records" / f"{rid}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
            # Assertion preview through the exporter's own mapping. The claim links are
            # placeholders (the demo file plus the claim id) until the results are
            # committed at a pinned commit; this is NOT a receipt.
            env = Envelope(path=None, record_type="testable_disagreement",
                           source={"repository": "", "commit": "", "path": "", "receipt_url": ""},
                           receipt={"content_hash": "", "hash_method": ""},
                           context={"claim_a_receipt_url": f"{url}#{a['claim_id']}",
                                    "claim_b_receipt_url": f"{url}#{b['claim_id']}",
                                    "testability": "testable_now", "instrument": instrument},
                           record={"kind": "fork", "pair_id": pid, "claim_a_id": a["claim_id"],
                                   "claim_b_id": b["claim_id"], "axis": f["axis"]})
            built = X._disagreement(env)
            ttl = ("# ASSERTION PREVIEW ONLY. Not a nanopublication: no provenance, no publication\n"
                   "# info, not signed. Claim links are placeholders until the demo results are\n"
                   "# committed to a public repository at a pinned commit.\n")
            (out / "preview" / f"{rid}.ttl").write_text(ttl + built.assertion.serialize(format="turtle"))
            index["candidates"].append({**base, "id": rid, "instrument": instrument,
                                        "label": built.label})

    cog = json.loads((snap / "iitxgnwt_vs_cogitate.json").read_text())
    index["cogitate_note"] = (
        "The COGITATE comparison is reported as: 2 of 3 preregistered disagreements recovered "
        "after a disclosed re-review (originally 1 of 3); p = 0.075 against a 1,000-key "
        "permutation null, suggestive only. No nanopub template fits a recovery score, so it is "
        "not a candidate record. The demo tags these forks as lying on the axes of the COGITATE "
        "key (a tag, not the recovery count above): "
        + ", ".join(sorted({fk['pair'] for fk in cog['forks'] if fk['class'] == 'MATCHES_KEY'})))
    (out / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    print(f"candidates {len(index['candidates'])}; not eligible {len(index['not_eligible'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
