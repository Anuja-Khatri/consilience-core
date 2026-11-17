"""Prepare (do not publish) every eligible consilience-ledger record as an unsigned
candidate nanopublication.

Reads the public ledger at a pinned commit with ``git show`` (read only), wraps every
claim card and every refused comparison in a record envelope exactly as
``scripts/select_pilot_records.py`` does, checks each receipt, builds the nanopub with
the exporter, and writes UNSIGNED TriG. Nothing is signed and nothing is sent anywhere.

    python scripts/build_ledger_candidates.py --ledger ../consilience-ledger \
        --commit 7c1f9235b582666403537dd929c844e4b2dfc8cf

Outputs (under candidates/ledger/):
  records/<id>.json   record envelopes (the input to ``consilience export --nanopub``)
  trig/<id>.trig      unsigned TriG in the temporary namespace (not trusty, not signed)
  index.json          one row per candidate: type, label, receipt link, tier, grouping keys
  excluded.json       records that could not be exported, with the exporter's reason
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from consilience.export import nanopub as X  # noqa: E402
from consilience.receipts import (  # noqa: E402
    CARD_METHOD, SCHEMA, VERDICT_METHOD, card_hash, ledger_hash, line_range_of_list_item,
    parse_envelope,
)
from select_pilot_records import REPO, SOURCE_DOCUMENTS, git_show, receipt_url  # noqa: E402

# Fixed so that rebuilding gives byte-identical files. The real creation time is set
# when (and if) a record is signed.
CREATED = "2026-11-17T00:00:00Z"


def defect_signature(rec: dict) -> str:
    parts = sorted(f"{d['defect_type']}:{d['target']}" for d in rec["defects"])
    return f"{rec['outcome']}|{','.join(parts)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", default=str(ROOT / "candidates" / "ledger"))
    args = ap.parse_args()
    ledger, commit = Path(args.ledger), args.commit
    if len(commit) != 40:
        raise SystemExit("give the full 40-hex commit")

    claims_text = git_show(ledger, commit, "ledger/claims.json")
    rej_text = git_show(ledger, commit, "ledger/rejections.json")
    claims, rejections = json.loads(claims_text), json.loads(rej_text)
    rules_lock = git_show(ledger, commit, "rules/rules.lock")
    stated = git_show(ledger, commit, "ledger/ledger.hash").strip()
    rules_version = json.loads(rules_lock)["version"]
    (code_version,) = {r["code_version"] for r in rejections}
    if ledger_hash(claims, rules_lock, code_version) != stated:
        raise SystemExit("ledger.hash does not reproduce")
    rules_yaml = git_show(ledger, commit, "rules/comparability_rules.yaml")
    condition_rules = {m.group(1): [f.strip() for f in m.group(2).split(",")]
                       for m in re.finditer(r"- id: (CR\d+)\n\s+fields: \[([^\]]*)\]", rules_yaml)}

    cfg = json.loads((ROOT / "config" / "agent.json").read_text())
    templates = json.loads((ROOT / "config" / "templates.json").read_text())
    agent = cfg["agent_iri"]

    claim_idx = {c["claim_id"]: i for i, c in enumerate(claims)}

    def claim_url(cid: str) -> str:
        return receipt_url(commit, "ledger/claims.json", line_range_of_list_item(claims_text, claim_idx[cid]))

    out = Path(args.out)
    (out / "records").mkdir(parents=True, exist_ok=True)
    (out / "trig").mkdir(parents=True, exist_ok=True)
    index, excluded = [], []

    def emit(name: str, env: dict, extra: dict) -> None:
        e = parse_envelope(env)
        try:
            ds = X.record_nanopub(e, agent, templates, created=CREATED)
        except X.ExportError as exc:
            excluded.append({"id": name, "record_type": env["record_type"],
                             "receipt_url": env["source"]["receipt_url"], "reason": str(exc)})
            return
        (out / "records" / f"{name}.json").write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n")
        (out / "trig" / f"{name}.trig").write_text(X.to_trig(ds), encoding="utf-8")
        built = X.build_assertion(e)
        index.append({"id": name, "record_type": env["record_type"], "label": built.label,
                      "receipt_url": env["source"]["receipt_url"], **extra})

    for i, card in enumerate(claims):
        lines = line_range_of_list_item(claims_text, i)
        env = {
            "schema": SCHEMA, "record_type": "claim_card",
            "source": {"repository": REPO, "commit": commit, "path": "ledger/claims.json",
                       "lines": list(lines), "receipt_url": receipt_url(commit, "ledger/claims.json", lines)},
            "receipt": {"content_hash": card_hash(card), "hash_method": CARD_METHOD},
            "context": {
                "source_document_url": SOURCE_DOCUMENTS[card["source_document"]],
                "ledger_hash": stated, "code_version": code_version, "rules_version": rules_version,
                "note": "The ledger stores no per-card content hash; this one is computed with "
                        "the ledger's own hasher over the card exactly as committed. The card "
                        "set is covered by ledger_hash.",
            },
            "record": card,
        }
        emit(f"claim-card-{card['claim_id']}", env,
             {"source_sentence_group": card["source_sentence"], "tier": "A"})

    for i, rec in enumerate(rejections):
        lines = line_range_of_list_item(rej_text, i)
        env = {
            "schema": SCHEMA, "record_type": "comparison_refusal",
            "source": {"repository": REPO, "commit": commit, "path": "ledger/rejections.json",
                       "lines": list(lines), "receipt_url": receipt_url(commit, "ledger/rejections.json", lines)},
            "receipt": {"content_hash": rec["content_hash"], "hash_method": VERDICT_METHOD},
            "context": {
                "claim_a_receipt_url": claim_url(rec["claim_a_id"]),
                "claim_b_receipt_url": claim_url(rec["claim_b_id"]),
                "condition_rules": {d["target"]: condition_rules[d["target"]]
                                    for d in rec["defects"] if d["defect_type"] == "condition_mismatch"},
                "rules_url": f"{REPO}/blob/{commit}/rules/comparability_rules.yaml",
            },
            "record": rec,
        }
        ca, cb = claims[claim_idx[rec["claim_a_id"]]], claims[claim_idx[rec["claim_b_id"]]]
        same_axis = rec["outcome"] != "axis_mismatch"
        same_unit = ca["quantity"]["unit"] == cb["quantity"]["unit"]
        # Tier A: the refusal tells a reader something they might otherwise get wrong
        # (same quantity, or different quantities that share a unit). Tier B: true but
        # obvious (different quantities in different units).
        tier = "A" if (same_axis or same_unit) else "B"
        emit(f"refusal-{rec['pair_id'].replace('|', '--')}", env,
             {"outcome": rec["outcome"], "defect_signature": defect_signature(rec),
              "axis_pair": sorted({ca["axis"], cb["axis"]}),
              "same_axis": same_axis, "same_unit": same_unit, "tier": tier})

    (out / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    (out / "excluded.json").write_text(json.dumps(excluded, indent=2, ensure_ascii=False) + "\n")
    counts = defaultdict(int)
    for row in index:
        counts[f"{row['record_type']} tier {row['tier']}"] += 1
    print(f"prepared {dict(counts)}; excluded {len(excluded)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
