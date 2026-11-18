"""Select the pilot records from the public consilience-ledger at a pinned commit.

Reads the ledger with ``git show <commit>:<path>`` from a local clone (read only), wraps
each chosen record in a record envelope (see ``consilience.receipts``) with its receipt
link and content hash, and writes the envelopes to ``pilot/records/``.

    python scripts/select_pilot_records.py --ledger ../consilience-ledger \
        --commit 7c1f9235b582666403537dd929c844e4b2dfc8cf

Every record is checked before it is written: verdict hashes must reproduce, claim
cards must reproduce their provenance hash, and the ledger hash at that commit must
reproduce from the committed claims, rules lock and code version.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from consilience.receipts import (  # noqa: E402
    CARD_METHOD, SCHEMA, VERDICT_METHOD, card_hash, ledger_hash, line_range_of_list_item,
    parse_envelope, verify,
)

REPO = "https://github.com/Anuja-Khatri/consilience-ledger"

# The pilot set. Seven refused comparisons and three claim cards; the refusals of the
# first pair point at the two claim cards below, so the records link to each other.
REFUSALS = [
    "ref40_peng2023__002|ref40_peng2023__011",   # current density differs (rule CR2)
    "ref40_peng2023__009|ref40_peng2023__010",   # current density differs (rule CR2)
    "2609.30133__001|ref40_peng2023__002",       # different quantity axes, both in hours
    "2609.30133__003|2609.30133__004",           # electrolyte and temperature not stated
    "2609.30133__003|ref40_peng2023__013",       # across the two papers, four conditions not stated
    "2609.30133__001|2609.30133__002",           # four conditions not stated
    "ref40_peng2023__026|ref40_peng2023__044",   # mass activity, four conditions not stated
]
CLAIMS = ["ref40_peng2023__002", "ref40_peng2023__011", "2609.30133__003"]
# v2: a refusal names its two claims by the claim IRIs their claim-card nanopubs introduce,
# so every claim a pilot refusal refers to needs a published claim card. These eight are
# the supporting cards (records 11-18); they are written after the ten pilot records so
# that records 01-10 keep their numbers.
SUPPORTING_CLAIMS = ["ref40_peng2023__009", "ref40_peng2023__010", "2609.30133__001",
                     "2609.30133__004", "ref40_peng2023__013", "2609.30133__002",
                     "ref40_peng2023__026", "ref40_peng2023__044"]

REFUSAL_NOTE = (
    "A refused comparison from the public consilience-ledger, under its rule set "
    "comparability-v0.1. Which claim does not state each condition, and the two values of a "
    "condition that differs, are read from the two claims' cards (claim A and claim B), whose "
    "receipts are in their own nanopublications. It records what the two claim cards, as "
    "extracted from their source sentences, allow; it is not a judgement of either paper."
)

# From the ledger's corpus/MANIFEST.yaml at the same commit.
SOURCE_DOCUMENTS = {
    "2609.30133": "https://arxiv.org/abs/2609.30133",
    "ref40_peng2023": "https://doi.org/10.1093/nsr/nwac108",
}


def git_show(ledger: Path, commit: str, path: str) -> str:
    return subprocess.run(["git", "-C", str(ledger), "show", f"{commit}:{path}"],
                          check=True, capture_output=True, text=True).stdout


def receipt_url(commit: str, path: str, lines: tuple[int, int]) -> str:
    return f"{REPO}/blob/{commit}/{path}#L{lines[0]}-L{lines[1]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", default=str(ROOT / "pilot" / "records"))
    args = ap.parse_args()
    ledger, commit = Path(args.ledger), args.commit
    if len(commit) != 40:
        raise SystemExit("give the full 40-hex commit")

    claims_text = git_show(ledger, commit, "ledger/claims.json")
    rej_text = git_show(ledger, commit, "ledger/rejections.json")
    claims = json.loads(claims_text)
    rejections = json.loads(rej_text)
    rules_lock = git_show(ledger, commit, "rules/rules.lock")
    stated_ledger_hash = git_show(ledger, commit, "ledger/ledger.hash").strip()
    rules_version = json.loads(rules_lock)["version"]
    code_versions = {r["code_version"] for r in rejections}
    if len(code_versions) != 1:
        raise SystemExit(f"expected one code version, found {code_versions}")
    code_version = code_versions.pop()
    lh = ledger_hash(claims, rules_lock, code_version)
    if lh != stated_ledger_hash:
        raise SystemExit(f"ledger.hash does not reproduce: {lh} != {stated_ledger_hash}")

    rules_yaml = git_show(ledger, commit, "rules/comparability_rules.yaml")
    condition_rules = {m.group(1): [f.strip() for f in m.group(2).split(",")]
                       for m in re.finditer(r"- id: (CR\d+)\n\s+fields: \[([^\]]*)\]", rules_yaml)}
    if not condition_rules:
        raise SystemExit("could not read the condition rules")

    claim_idx = {c["claim_id"]: i for i, c in enumerate(claims)}
    rej_idx = {r["pair_id"]: i for i, r in enumerate(rejections)}

    def claim_url(cid: str) -> str:
        return receipt_url(commit, "ledger/claims.json", line_range_of_list_item(claims_text, claim_idx[cid]))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    n = 0

    def write_card(cid: str, n: int) -> None:
        i = claim_idx[cid]
        card = claims[i]
        lines = line_range_of_list_item(claims_text, i)
        doc = card["source_document"]
        env = {
            "schema": SCHEMA,
            "record_type": "claim_card",
            "source": {"repository": REPO, "commit": commit, "path": "ledger/claims.json",
                       "lines": list(lines), "receipt_url": receipt_url(commit, "ledger/claims.json", lines)},
            "receipt": {"content_hash": card_hash(card), "hash_method": CARD_METHOD},
            "context": {
                "source_document_url": SOURCE_DOCUMENTS[doc],
                "ledger_hash": stated_ledger_hash,
                "code_version": code_version,
                "rules_version": rules_version,
                "note": "The ledger stores no per-card content hash; this one is computed with "
                        "the ledger's own hasher over the card exactly as committed. The card "
                        "set is covered by ledger_hash.",
            },
            "record": card,
        }
        verify(parse_envelope(env))
        (out / f"{n:02d}-claim-card-{cid}.json").write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n")

    for cid in CLAIMS:
        n += 1
        write_card(cid, n)
    for pid in REFUSALS:
        i = rej_idx[pid]
        rec = rejections[i]
        lines = line_range_of_list_item(rej_text, i)
        env = {
            "schema": SCHEMA,
            "record_type": "comparison_refusal",
            "source": {"repository": REPO, "commit": commit, "path": "ledger/rejections.json",
                       "lines": list(lines), "receipt_url": receipt_url(commit, "ledger/rejections.json", lines)},
            "receipt": {"content_hash": rec["content_hash"], "hash_method": VERDICT_METHOD},
            "context": {
                "claim_a_receipt_url": claim_url(rec["claim_a_id"]),
                "claim_b_receipt_url": claim_url(rec["claim_b_id"]),
                # every condition rule and its fields: which rule requires an unstated
                # condition, and which field a mismatched rule is about
                "condition_rules": condition_rules,
                "rules_url": f"{REPO}/blob/{commit}/rules/comparability_rules.yaml",
                "pubinfo_note": REFUSAL_NOTE,
            },
            "record": rec,
        }
        verify(parse_envelope(env))
        n += 1
        safe = pid.replace("|", "--")
        (out / f"{n:02d}-refusal-{safe}.json").write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n")
    for cid in SUPPORTING_CLAIMS:
        n += 1
        write_card(cid, n)
    print(f"wrote {n} envelopes to {out}; ledger hash {lh} reproduces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
