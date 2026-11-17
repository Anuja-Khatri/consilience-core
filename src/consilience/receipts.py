"""Record envelopes and receipt (content-hash) checks.

A *record envelope* is a JSON file that wraps one record exactly as it appears in a
public Consilience repository, together with where it came from:

    {
      "schema": "consilience-record/v0",
      "record_type": "comparison_refusal" | "claim_card" | "graded_correspondence"
                     | "testable_disagreement" | "data_quality_finding",
      "source": {
        "repository": "https://github.com/<owner>/<repo>",
        "commit": "<40-hex commit>",
        "path": "ledger/rejections.json",
        "lines": [start, end],
        "receipt_url": "https://github.com/<owner>/<repo>/blob/<commit>/<path>#L<start>-L<end>"
      },
      "receipt": {"content_hash": "<64-hex>", "hash_method": "<method id>"},
      "context": {...},          # facts the record points at (e.g. claim receipt URLs)
      "record": {...}            # the record, byte-for-byte content as published
    }

Every check here fails closed: anything that does not verify raises ``ReceiptError``
with a named reason. Nothing is coerced or guessed.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "consilience-record/v0"

RECORD_TYPES = (
    "comparison_refusal",
    "claim_card",
    "graded_correspondence",
    "testable_disagreement",
    "data_quality_finding",
    "theory_claim_card",
)

# Hash methods.
#
# verdict-sha256-v0: SHA-256 over json.dumps(record without "content_hash",
#   sort_keys=True, default=str). This is the hasher the consilience-ledger judge uses
#   (vendor/engine/judge/hash/determinism_check.py, compute_verdict_hash), so a
#   verdict's stored content_hash can be recomputed from the record alone.
# card-sha256-v0: SHA-256 over json.dumps(card, sort_keys=True, default=str). The ledger
#   stores no per-card content hash (a card carries a 16-hex provenance_hash over its
#   source document and sentence, and the whole set of cards is covered by
#   ledger/ledger.hash). The exporter computes this hash with the same hasher so that
#   each published card has a checkable content hash of its own.
# json-sha256-v0: SHA-256 over json.dumps(record, sort_keys=True, default=str), for records
#   copied from a receipt file that stores no hash of its own (the cross-theory demo's
#   claim cards and disagreements). The formula is the same as card-sha256-v0; the name
#   says that no claim-card provenance hash is involved. The receipt file as a whole is
#   covered by its SHA-256 in the source repository's manifest (source.file_sha256).
VERDICT_METHOD = "verdict-sha256-v0"
CARD_METHOD = "card-sha256-v0"
JSON_METHOD = "json-sha256-v0"
# Record types that may use JSON_METHOD.
JSON_METHOD_TYPES = ("theory_claim_card", "testable_disagreement")

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


class ReceiptError(ValueError):
    """A record or its receipt does not verify. The message names the reason."""


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str)


def verdict_hash(record: dict) -> str:
    """Content hash of a verdict record, excluding its own content_hash field."""
    body = {k: v for k, v in record.items() if k != "content_hash"}
    return hashlib.sha256(_canonical(body).encode()).hexdigest()


def card_hash(card: dict) -> str:
    """Content hash of a claim card (the whole card)."""
    return hashlib.sha256(_canonical(card).encode()).hexdigest()


def json_hash(record: dict) -> str:
    """Content hash of a record that carries no hash of its own (json-sha256-v0)."""
    return hashlib.sha256(_canonical(record).encode()).hexdigest()


def card_provenance_hash(card: dict) -> str:
    """The ledger's 16-hex provenance hash over source document and source sentence."""
    prov = f"{card.get('source_document', '')}\x1f{card.get('source_sentence', '')}"
    return hashlib.sha256(prov.encode()).hexdigest()[:16]


def ledger_hash(claims: list, rules_lock_text: str, code_version: str) -> str:
    """Recompute consilience-ledger's ledger.hash (labext/ledger.py, build_ledger)."""
    canon = json.dumps(claims, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((canon + "\x1f" + rules_lock_text + "\x1f" + code_version).encode()).hexdigest()


@dataclass(frozen=True)
class Envelope:
    path: Path | None
    record_type: str
    source: dict
    receipt: dict
    context: dict
    record: dict

    @property
    def content_hash(self) -> str:
        return self.receipt["content_hash"]

    @property
    def receipt_url(self) -> str:
        return self.source["receipt_url"]


def _require(cond: bool, reason: str) -> None:
    if not cond:
        raise ReceiptError(reason)


def parse_envelope(data: dict, path: Path | None = None) -> Envelope:
    """Validate the envelope's shape. Does not check hashes (see ``verify``)."""
    _require(isinstance(data, dict), "envelope_not_object")
    _require(data.get("schema") == SCHEMA, f"unknown_schema: {data.get('schema')!r}")
    rtype = data.get("record_type")
    _require(rtype in RECORD_TYPES, f"unknown_record_type: {rtype!r}")
    src = data.get("source")
    _require(isinstance(src, dict), "missing_source")
    for key in ("repository", "commit", "path", "receipt_url"):
        _require(isinstance(src.get(key), str) and src[key], f"missing_source_field: {key}")
    _require(bool(_HEX40.match(src["commit"])), "source_commit_not_pinned: need a full 40-hex commit")
    _require(src["repository"].startswith("https://github.com/"), "source_repository_not_github_https")
    _require(
        src["receipt_url"].startswith(f"{src['repository']}/blob/{src['commit']}/{src['path']}"),
        "receipt_url_not_pinned_to_source_commit_and_path",
    )
    rec = data.get("record")
    _require(isinstance(rec, dict) and rec, "missing_record")
    receipt = data.get("receipt")
    _require(isinstance(receipt, dict), "missing_receipt")
    _require(receipt.get("hash_method") in (VERDICT_METHOD, CARD_METHOD, JSON_METHOD),
             f"unknown_hash_method: {receipt.get('hash_method')!r}")
    _require(bool(_HEX64.match(str(receipt.get("content_hash", "")))), "receipt_hash_not_sha256_hex")
    ctx = data.get("context", {})
    _require(isinstance(ctx, dict), "context_not_object")
    return Envelope(path=path, record_type=rtype, source=src, receipt=receipt, context=ctx, record=rec)


def load_envelope(path: str | Path) -> Envelope:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"unreadable_envelope: {p}: {exc}") from None
    return parse_envelope(data, p)


def recompute(env: Envelope) -> str:
    """Recompute the record's content hash with the method its receipt names."""
    method = env.receipt["hash_method"]
    if method == VERDICT_METHOD:
        return verdict_hash(env.record)
    if method == CARD_METHOD:
        return card_hash(env.record)
    if method == JSON_METHOD:
        return json_hash(env.record)
    raise ReceiptError(f"unknown_hash_method: {method!r}")  # unreachable after parse


def verify(env: Envelope) -> str:
    """Check the record against its receipt. Returns the verified content hash.

    - The recomputed hash must equal the receipt's content_hash.
    - Verdict records must also carry that same hash in their own content_hash field
      (it is what the source repository published).
    - Claim cards must reproduce their own provenance_hash.
    """
    got = recompute(env)
    _require(got == env.content_hash,
             f"content_hash_mismatch: receipt says {env.content_hash}, record hashes to {got}")
    if env.receipt["hash_method"] == VERDICT_METHOD:
        _require(env.record.get("content_hash") == env.content_hash,
                 "record_content_hash_differs_from_receipt")
    if env.record_type == "claim_card":
        _require(env.receipt["hash_method"] == CARD_METHOD, "claim_card_needs_card_hash_method")
        ph = env.record.get("provenance_hash")
        _require(ph == card_provenance_hash(env.record),
                 f"provenance_hash_mismatch: card says {ph!r}")
    elif env.receipt["hash_method"] == JSON_METHOD:
        _require(env.record_type in JSON_METHOD_TYPES,
                 f"json_hash_method_not_allowed_for: {env.record_type}")
    elif env.record_type == "theory_claim_card":
        raise ReceiptError("theory_claim_card_needs_json_hash_method")
    else:
        _require(env.receipt["hash_method"] == VERDICT_METHOD, "verdict_needs_verdict_hash_method")
    return got


def line_range_of_list_item(text: str, index: int) -> tuple[int, int]:
    """1-based line range of item ``index`` in a top-level JSON list written by
    ``json.dump(data, fh, indent=2, sort_keys=True)`` (the ledger's writer).

    Fails closed if the file does not have that layout or the item does not re-parse
    to the same object.
    """
    lines = text.split("\n")
    _require(lines and lines[0] == "[", "not_an_indent2_json_list")
    starts = [i for i, ln in enumerate(lines) if ln == "  {"]
    ends = [i for i, ln in enumerate(lines) if ln in ("  },", "  }")]
    _require(len(starts) == len(ends), "unbalanced_list_items")
    _require(0 <= index < len(starts), f"index_out_of_range: {index}")
    s, e = starts[index], ends[index]
    chunk = "\n".join(lines[s:e + 1]).rstrip(",")
    item = json.loads(chunk)
    _require(item == json.loads(text)[index], "line_range_does_not_reparse_to_item")
    return s + 1, e + 1
