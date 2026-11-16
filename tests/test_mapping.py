"""Mapping records to nanopublication graphs, and conformance to the templates."""

import copy

import pytest
from rdflib import Literal, URIRef

from consilience.export import nanopub as X
from consilience.export import spec as S
from consilience.export.vocab import CV, DCT, PROV, RDF, XSD
from consilience.receipts import (
    SCHEMA, VERDICT_METHOD, load_envelope, parse_envelope, verdict_hash,
)
from conftest import RECORDS, load_json

TEMPLATES = {k: f"https://example.org/template/{k}" for k in S.ALL_SPECS}
AGENT = "https://example.org/agent"
NS = str(S.TEMP_NS)
ASSERTION = S.TEMP_NS["assertion"]


def _graphs(ds):
    return {str(g.identifier)[len(NS):]: g for g in ds.graphs() if str(g.identifier).startswith(NS)}


@pytest.mark.parametrize("path", RECORDS, ids=lambda p: p.stem)
def test_pilot_record_conforms_to_its_template(path):
    env = load_envelope(path)
    built = X.build_assertion(env)
    res = S.check_conformance(built.spec, built.assertion, NS, ASSERTION)
    assert res.ok, (res.unmatched, res.missing, res.bad_values)
    prov = X.build_provenance(env, URIRef(AGENT))
    res = S.check_conformance(S.RECEIPT_PROVENANCE, prov, NS, ASSERTION)
    assert res.ok, (res.unmatched, res.missing, res.bad_values)


@pytest.mark.parametrize("path", RECORDS, ids=lambda p: p.stem)
def test_provenance_carries_the_receipt(path):
    env = load_envelope(path)
    prov = X.build_provenance(env, URIRef(AGENT))
    a = ASSERTION
    assert (a, PROV.wasDerivedFrom, URIRef(env.receipt_url)) in prov
    assert (a, CV.contentHash, Literal(env.content_hash)) in prov
    assert (a, CV.sourceCommit, Literal(env.source["commit"])) in prov
    assert (a, CV.sourceRepository, URIRef(env.source["repository"])) in prov
    assert (a, CV.codeVersion, None) in prov
    assert (a, CV.rulesVersion, None) in prov
    assert (a, PROV.wasAttributedTo, URIRef(AGENT)) in prov


def test_refusal_mapping_is_faithful():
    env = load_envelope(next(p for p in RECORDS if "ref40_peng2023__002--ref40_peng2023__011" in p.name))
    g = X.build_assertion(env).assertion
    me = S.TEMP_NS["refusal"]
    assert (me, RDF.type, CV.ComparisonRefusal) in g
    assert (me, DCT.identifier, Literal(env.record["pair_id"])) in g
    assert (me, CV.outcome, CV.NotComparable) in g
    defects = sorted((str(g.value(d, CV.defectType)), str(g.value(d, CV.defectTarget)))
                     for d in g.objects(me, CV.hasDefect))
    expected = sorted((str(X._DEFECTS[d["defect_type"]]), d["target"]) for d in env.record["defects"])
    assert defects == expected
    assert g.value(me, CV.claimA) == URIRef(env.context["claim_a_receipt_url"])


def test_claim_card_mapping_is_faithful():
    env = load_envelope(next(p for p in RECORDS if "claim-card-2609.30133__003" in p.name))
    g = X.build_assertion(env).assertion
    me = URIRef(env.receipt_url)
    c = env.record
    assert (me, CV.sourceSentence, Literal(c["source_sentence"])) in g
    q = g.value(me, CV.hasQuantity)
    assert float(g.value(q, URIRef("https://schema.org/value"))) == c["quantity"]["value"]
    stated = {str(g.value(n, CV.conditionName)) for n in g.objects(me, CV.hasCondition)}
    unstated = {str(o) for o in g.objects(me, CV.conditionUnstated)}
    assert stated == {k for k, v in c["conditions"].items() if v != "unstated"}
    assert unstated == {k for k, v in c["conditions"].items() if v == "unstated"}


def test_record_that_fails_its_receipt_is_not_exported():
    data = load_json(RECORDS[-1])
    data["record"]["outcome"] = "fork"  # changes the record, so the hash no longer matches
    with pytest.raises(X.ExportError, match="receipt_does_not_verify"):
        X.build_assertion(parse_envelope(data))


def _synthetic(record_type, record, context):
    """Synthetic records for record types with no public instance yet (tests only)."""
    record = dict(record)
    record["content_hash"] = verdict_hash(record)
    return parse_envelope({
        "schema": SCHEMA,
        "record_type": record_type,
        "source": {"repository": "https://github.com/example/synthetic",
                   "commit": "0" * 40, "path": "synthetic.json", "lines": [1, 1],
                   "receipt_url": f"https://github.com/example/synthetic/blob/{'0' * 40}/synthetic.json#L1-L1"},
        "receipt": {"content_hash": record["content_hash"], "hash_method": VERDICT_METHOD},
        "context": context,
        "record": record,
    })


PAIR_CTX = {"claim_a_receipt_url": "https://example.org/claim/a",
            "claim_b_receipt_url": "https://example.org/claim/b"}

SYNTHETIC = {
    "graded_correspondence": _synthetic("graded_correspondence", {
        "kind": "correspondence", "outcome": "structural", "pair_id": "A|B",
        "claim_a_id": "A", "claim_b_id": "B", "rung": 2, "ceiling": "synthetic ceiling text",
        "equivocation": "survives", "code_version": "test-0", "rules_version": "test-0"}, PAIR_CTX),
    "testable_disagreement": _synthetic("testable_disagreement", {
        "kind": "fork", "outcome": "fork", "pair_id": "A|B", "claim_a_id": "A", "claim_b_id": "B",
        "axis": "synthetic_axis", "margin": 0.2, "floor_applied": 0.013, "canonical_unit": "V",
        "code_version": "test-0", "rules_version": "test-0"},
        {**PAIR_CTX, "testability": "measurable_now", "instrument": "synthetic_instrument"}),
    "data_quality_finding": _synthetic("data_quality_finding", {
        "kind": "data_quality_finding", "finding_id": "synthetic-1",
        "dataset": "https://example.org/dataset", "check": "value below its recorded limit",
        "n_checked": 10, "n_flagged": 1, "finding": "one synthetic record over its limit",
        "code_version": "test-0", "rules_version": "test-0"}, {}),
}


@pytest.mark.parametrize("key", list(SYNTHETIC))
def test_other_record_types_conform_to_their_templates(key):
    env = SYNTHETIC[key]
    built = X.build_assertion(env)
    assert built.spec.key == key
    res = S.check_conformance(built.spec, built.assertion, NS, ASSERTION)
    assert res.ok, (res.unmatched, res.missing, res.bad_values)
    ds = X.record_nanopub(env, AGENT, TEMPLATES, created="2026-01-01T00:00:00Z")
    assert set(_graphs(ds)) == {"Head", "assertion", "provenance", "pubinfo"}


def test_grade_is_an_integer_literal():
    g = X.build_assertion(SYNTHETIC["graded_correspondence"]).assertion
    grade = g.value(S.TEMP_NS["correspondence"], CV.grade)
    assert grade.datatype == XSD.integer and int(grade) == 2


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_non_finite_quantities_are_refused(bad):
    data = load_json(next(p for p in RECORDS if "claim-card" in p.name))
    data["record"]["quantity"]["value"] = bad
    from consilience.receipts import card_hash
    data["receipt"]["content_hash"] = card_hash(data["record"])
    with pytest.raises(X.ExportError, match="non_finite_value"):
        X.build_assertion(parse_envelope(data))


def test_flagged_count_cannot_exceed_checked():
    rec = dict(SYNTHETIC["data_quality_finding"].record)
    rec.pop("content_hash")
    rec["n_flagged"] = 11
    with pytest.raises(X.ExportError, match="flagged_count"):
        X.build_assertion(_synthetic("data_quality_finding", rec, {}))


def test_unknown_outcome_is_refused():
    data = copy.deepcopy(load_json(RECORDS[-1]))
    data["record"]["outcome"] = "maybe"
    data["record"]["content_hash"] = verdict_hash(data["record"])
    data["receipt"]["content_hash"] = data["record"]["content_hash"]
    with pytest.raises(X.ExportError, match="unsupported_outcome"):
        X.build_assertion(parse_envelope(data))


def test_export_needs_published_templates():
    env = load_envelope(RECORDS[0])
    with pytest.raises(X.ExportError, match="template_not_published"):
        X.record_nanopub(env, AGENT, {}, created="2026-01-01T00:00:00Z")


def test_templates_list_every_statement_and_carry_labels():
    for spec in S.ALL_SPECS.values():
        g = S.template_assertion_graph(spec)
        node = S.TEMP_NS["templateVersion"]
        listed = {str(o)[len(NS):] for o in g.objects(node, URIRef("https://w3id.org/np/o/ntemplate/hasStatement"))}
        assert {s.id for s in spec.statements} <= listed
        assert {gr.id for gr in spec.groups} <= listed
