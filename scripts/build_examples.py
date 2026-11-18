"""Write the example envelopes in pilot/examples/.

Two templates have no real instance in this pilot: (a) graded correspondence and (d)
data-quality finding. The nanopub network sets up a type only once a nanopub of that type
exists, and its convention is to bootstrap a new type with one ``npx:ExampleNanopub`` whose
label starts "Example: ". These envelopes hold made-up data and say so; their claim IRIs
and dataset are under example.org. Output is deterministic.

    python scripts/build_examples.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from consilience.receipts import SCHEMA, VERDICT_METHOD, parse_envelope, verdict_hash, verify  # noqa: E402

OUT = ROOT / "pilot" / "examples"
NOTE = ("Example only: this nanopublication shows how the template is filled. Its data is made "
        "up, refers to no real claim or dataset, and is not a Consilience result.")
SOURCE = {"repository": "https://github.com/example/example", "commit": "0" * 40,
          "path": "example.json", "lines": [1, 1],
          "receipt_url": f"https://github.com/example/example/blob/{'0' * 40}/example.json#L1-L1"}

EXAMPLES = {
    "example-graded-correspondence": ("graded_correspondence", {
        "kind": "correspondence", "pair_id": "example-A|example-B",
        "claim_a_id": "example-A", "claim_b_id": "example-B", "rung": 2,
        "ceiling": "Made-up example: a rung-2 correspondence would not license treating the two "
                   "claims as the same finding.",
        "equivocation": "survives (made-up example)",
        "code_version": "example", "rules_version": "example"}, {
        "claim_a_receipt_url": "https://example.org/claim-card/example-A",
        "claim_b_receipt_url": "https://example.org/claim-card/example-B"}),
    "example-data-quality-finding": ("data_quality_finding", {
        "kind": "data_quality_finding", "finding_id": "example-1",
        "dataset": "https://example.org/dataset/example-1",
        "check": "A measured value must not exceed the instrument limit recorded in the same row "
                 "(made-up example).",
        "n_checked": 1000, "n_flagged": 3,
        "finding": "Made-up example: 3 of 1,000 rows of a made-up dataset record a value above the "
                   "instrument limit recorded in the same row.",
        "code_version": "example", "rules_version": "example"}, {}),
}

# The made-up claim IRIs the example correspondence names (used only with --example).
CLAIMS = {
    "https://example.org/claim-card/example-A": {"claim_id": "example-A",
                                                 "claim_iri": "https://example.org/claim/example-A"},
    "https://example.org/claim-card/example-B": {"claim_id": "example-B",
                                                 "claim_iri": "https://example.org/claim/example-B"},
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (rtype, record, ctx) in EXAMPLES.items():
        record = dict(record)
        record["content_hash"] = verdict_hash(record)
        env = {"schema": SCHEMA, "record_type": rtype, "source": SOURCE,
               "receipt": {"content_hash": record["content_hash"], "hash_method": VERDICT_METHOD},
               "context": {**ctx, "pubinfo_note": NOTE}, "record": record}
        verify(parse_envelope(env))
        (OUT / f"{name}.json").write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
    (OUT / "claims.json").write_text(json.dumps(CLAIMS, indent=2) + "\n", encoding="utf-8")
    print(f"{len(EXAMPLES)} example envelopes -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
