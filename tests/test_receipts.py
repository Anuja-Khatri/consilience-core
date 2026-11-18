"""Each pilot record's content hash matches its source receipt."""

import copy
import json

import pytest

from consilience.receipts import (
    CARD_METHOD, ReceiptError, card_hash, ledger_hash, line_range_of_list_item, load_envelope,
    parse_envelope, verify, verdict_hash,
)
from conftest import RECORDS, load_json


def test_pilot_has_ten_records_and_eight_supporting_claim_cards():
    assert len(RECORDS) == 18
    kinds = [load_json(p)["record_type"] for p in RECORDS[:10]]
    assert kinds.count("claim_card") == 3
    assert kinds.count("comparison_refusal") == 7
    # records 11-18 are the claim cards the refusals name, so that every claim A and claim B
    # is a claim IRI introduced by a published claim card
    assert [load_json(p)["record_type"] for p in RECORDS[10:]] == ["claim_card"] * 8
    named = {load_json(p)["record"][k] for p in RECORDS if "refusal" in p.name
             for k in ("claim_a_id", "claim_b_id")}
    cards = {load_json(p)["record"]["claim_id"] for p in RECORDS if "claim-card" in p.name}
    assert named == cards


@pytest.mark.parametrize("path", RECORDS, ids=lambda p: p.stem)
def test_record_hash_reproduces(path):
    env = load_envelope(path)
    assert verify(env) == env.content_hash


@pytest.mark.parametrize("path", RECORDS, ids=lambda p: p.stem)
def test_record_is_identical_to_the_receipt_at_pinned_commit(path, ledger):
    """The record in the envelope is exactly the record at the receipt's lines."""
    env = load_envelope(path)
    text = ledger(env.source["commit"], env.source["path"])
    items = json.loads(text)
    matches = [i for i, it in enumerate(items) if it == env.record]
    assert len(matches) == 1, "record not found exactly once at the pinned commit"
    start, end = line_range_of_list_item(text, matches[0])
    assert [start, end] == env.source["lines"]
    assert env.receipt_url.endswith(f"#L{start}-L{end}")
    # and the hash, recomputed from the source repository's own copy, is the receipt's
    src = items[matches[0]]
    got = card_hash(src) if env.receipt["hash_method"] == CARD_METHOD else verdict_hash(src)
    assert got == env.content_hash
    if env.receipt["hash_method"] != CARD_METHOD:
        assert src["content_hash"] == env.content_hash


def test_claim_cards_are_covered_by_the_ledger_hash(ledger):
    env = load_envelope(next(p for p in RECORDS if "claim-card" in p.name))
    commit = env.source["commit"]
    claims = json.loads(ledger(commit, "ledger/claims.json"))
    lock = ledger(commit, "rules/rules.lock")
    stated = ledger(commit, "ledger/ledger.hash").strip()
    assert ledger_hash(claims, lock, env.context["code_version"]) == stated
    assert env.context["ledger_hash"] == stated


@pytest.mark.parametrize("path", RECORDS, ids=lambda p: p.stem)
def test_claim_links_point_into_the_same_commit(path):
    env = load_envelope(path)
    for key in ("claim_a_receipt_url", "claim_b_receipt_url"):
        if key in env.context:
            assert f"/blob/{env.source['commit']}/ledger/claims.json#L" in env.context[key]


def _tamper(env_path, fn):
    data = load_json(env_path)
    fn(data)
    return parse_envelope(data)


def test_tampered_value_is_refused():
    p = next(p for p in RECORDS if "refusal" in p.name)

    def change(d):
        d["record"]["axis"] = "something_else"
    with pytest.raises(ReceiptError, match="content_hash_mismatch"):
        verify(_tamper(p, change))


def test_tampered_receipt_is_refused():
    p = next(p for p in RECORDS if "claim-card" in p.name)

    def change(d):
        d["receipt"]["content_hash"] = "0" * 64
    with pytest.raises(ReceiptError, match="content_hash_mismatch"):
        verify(_tamper(p, change))


def test_card_with_altered_sentence_fails_its_provenance_hash():
    p = next(p for p in RECORDS if "claim-card" in p.name)
    data = load_json(p)
    data["record"]["source_sentence"] += " "
    data["receipt"]["content_hash"] = card_hash(data["record"])  # even with a fresh hash
    with pytest.raises(ReceiptError, match="provenance_hash_mismatch"):
        verify(parse_envelope(data))


@pytest.mark.parametrize("field,value,reason", [
    ("schema", "other/v9", "unknown_schema"),
    ("record_type", "opinion", "unknown_record_type"),
])
def test_bad_envelope_fields_are_refused(field, value, reason):
    data = load_json(RECORDS[0])
    data[field] = value
    with pytest.raises(ReceiptError, match=reason):
        parse_envelope(data)


def test_unpinned_commit_is_refused():
    data = copy.deepcopy(load_json(RECORDS[0]))
    data["source"]["commit"] = "main"
    with pytest.raises(ReceiptError, match="source_commit_not_pinned"):
        parse_envelope(data)
