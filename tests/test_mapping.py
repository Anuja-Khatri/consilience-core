"""Mapping records to nanopublication graphs, and conformance to the templates (offline)."""

import copy

import pytest
from rdflib import Literal, URIRef

from consilience.export import nanopub as X
from consilience.export import spec as S
from consilience.export.vocab import CV, DCT, PROV, QUDT, RDF, XSD
from consilience.receipts import (
    SCHEMA, VERDICT_METHOD, card_hash, load_envelope, parse_envelope, verdict_hash,
)
from conftest import RECORDS, ROOT, THEORY_RECORDS, load_json

TEMPLATES = {k: f"https://example.org/template/{k}" for k in S.ALL_SPECS}
AGENT = "https://example.org/agent"
NS = str(S.TEMP_NS)
ASSERTION = S.TEMP_NS["assertion"]
REVIEW = {"reviewer": "https://orcid.org/0009-0008-3375-7858", "drafted_by": "a large language model"}


def offline_claims():
    """A claims registry with made-up claim IRIs, so mapping is tested without the network."""
    entries = {}
    for p in list(RECORDS) + list(THEORY_RECORDS):
        env = load_envelope(p)
        if env.record_type in ("claim_card", "theory_claim_card"):
            cid = env.record["claim_id"]
            entries[env.receipt_url] = {"claim_id": cid, "claim_iri": f"https://example.org/claim/{cid}",
                                        "envelope": env}
    return X.Claims(entries)


CLAIMS = offline_claims()


def _graphs(ds):
    return {str(g.identifier)[len(NS):]: g for g in ds.graphs() if str(g.identifier).startswith(NS)}


@pytest.mark.parametrize("path", list(RECORDS) + list(THEORY_RECORDS), ids=lambda p: p.stem)
def test_record_conforms_to_its_template(path):
    env = load_envelope(path)
    built = X.build_assertion(env, CLAIMS)
    res = S.check_conformance(built.spec, built.assertion, NS, ASSERTION)
    assert res.ok, (res.unmatched, res.missing, res.bad_values)
    prov = X.build_provenance(env, URIRef(AGENT), REVIEW)
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
    assert (a, CV.reviewedBy, None) not in prov   # only theory claim cards were reviewed


def test_claim_card_mapping_is_faithful():
    env = load_envelope(next(p for p in RECORDS if "claim-card-ref40_peng2023__002" in p.name))
    g = X.build_assertion(env).assertion
    me = S.TEMP_NS["claim"]
    c = env.record
    assert (me, RDF.type, CV.MeasuredClaim) in g
    assert (me, CV.sourceSentence, Literal(c["source_sentence"])) in g
    assert g.value(me, CV.axis) == CV.OperationalStabilityDuration
    q = g.value(me, CV.hasQuantity)
    assert float(g.value(q, QUDT.numericValue)) == c["quantity"]["value"]
    assert g.value(q, QUDT.unit) == URIRef("http://qudt.org/vocab/unit/HR")
    assert g.value(q, CV.bound) == CV.ExactValue
    qconds = {(g.value(n, CV.condition), float(g.value(n, QUDT.numericValue)), g.value(n, QUDT.unit))
              for n in g.objects(me, CV.statesQuantityCondition)}
    assert qconds == {(CV.CurrentDensity, 10.0, CV["MilliA-PER-CentiM2"]),
                      (CV.ElectrolyteConcentration, 1.0, URIRef("http://qudt.org/vocab/unit/MOL-PER-L"))}
    cconds = {(g.value(n, CV.condition), g.value(n, CV.conditionValue))
              for n in g.objects(me, CV.statesCategoricalCondition)}
    assert cconds == {(CV.CurrentDensityNormalization, CV.GeometricArea),
                      (CV.Electrolyte, URIRef("http://purl.obolibrary.org/obo/CHEBI_29221"))}
    unstated = set(g.objects(me, CV.conditionUnstated))
    assert CV.Temperature in unstated and CV.IRCorrection in unstated and CV.Electrolyte not in unstated
    assert g.value(me, CV.measurableWith) == URIRef("http://purl.obolibrary.org/obo/CHMO_0000017")


def test_record_that_fails_its_receipt_is_not_exported():
    data = load_json(next(p for p in RECORDS if "refusal" in p.name))
    data["record"]["outcome"] = "fork"  # changes the record, so the hash no longer matches
    with pytest.raises(X.ExportError, match="receipt_does_not_verify"):
        X.build_assertion(parse_envelope(data), CLAIMS)


def test_unknown_strings_are_refused_not_guessed():
    data = load_json(next(p for p in RECORDS if "claim-card" in p.name))
    data["record"]["axis"] = "a_new_axis"
    data["receipt"]["content_hash"] = card_hash(data["record"])
    with pytest.raises(X.ExportError, match="no_iri_for_axis"):
        X.build_assertion(parse_envelope(data))


def test_refusal_needs_its_claim_cards_published_first():
    env = load_envelope(next(p for p in RECORDS if "refusal" in p.name))
    with pytest.raises(X.ExportError, match="claim_not_published_yet"):
        X.build_assertion(env, X.NO_CLAIMS)


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


PAIR_CTX = {"claim_a_receipt_url": "https://example.org/card/a",
            "claim_b_receipt_url": "https://example.org/card/b"}
PAIR_CLAIMS = X.Claims({"https://example.org/card/a": {"claim_iri": "https://example.org/claim/a"},
                        "https://example.org/card/b": {"claim_iri": "https://example.org/claim/b"}})
FORK = {"kind": "fork", "outcome": "fork", "pair_id": "A|B", "claim_a_id": "A", "claim_b_id": "B",
        "axis": "overpotential_at_current_density", "margin": 0.2, "floor_applied": 0.013,
        "canonical_unit": "V", "code_version": "test-0", "rules_version": "test-0"}

SYNTHETIC = {
    "graded_correspondence": _synthetic("graded_correspondence", {
        "kind": "correspondence", "outcome": "structural", "pair_id": "A|B",
        "claim_a_id": "A", "claim_b_id": "B", "rung": 2, "ceiling": "synthetic ceiling text",
        "equivocation": "survives", "code_version": "test-0", "rules_version": "test-0"}, PAIR_CTX),
    "disagreement": _synthetic("disagreement", FORK, {
        **PAIR_CTX, "testability": "testable_now", "instruments": ["cp_chronopotentiometry"],
        "testability_reason": "synthetic reason"}),
    "data_quality_finding": _synthetic("data_quality_finding", {
        "kind": "data_quality_finding", "finding_id": "synthetic-1",
        "dataset": "https://example.org/dataset", "check": "value below its recorded limit",
        "n_checked": 10, "n_flagged": 1, "finding": "one synthetic record over its limit",
        "code_version": "test-0", "rules_version": "test-0"}, {}),
}


@pytest.mark.parametrize("key", list(SYNTHETIC))
def test_other_record_types_conform_to_their_templates(key):
    env = SYNTHETIC[key]
    built = X.build_assertion(env, PAIR_CLAIMS)
    assert built.spec.key == key
    res = S.check_conformance(built.spec, built.assertion, NS, ASSERTION)
    assert res.ok, (res.unmatched, res.missing, res.bad_values)
    ds = X.record_nanopub(env, AGENT, TEMPLATES, created="2026-01-01T00:00:00Z", claims=PAIR_CLAIMS)
    assert set(_graphs(ds)) == {"Head", "assertion", "provenance", "pubinfo"}


def test_measured_disagreement_keeps_observables_and_instruments_apart():
    g = X.build_assertion(SYNTHETIC["disagreement"], PAIR_CLAIMS).assertion
    me = S.TEMP_NS["disagreement"]
    assert g.value(me, CV.instrument) == URIRef("http://purl.obolibrary.org/obo/CHMO_0000017")
    assert g.value(me, CV.observable) is None
    assert g.value(me, CV.dimension) == CV.OverpotentialAtCurrentDensity
    assert g.value(me, QUDT.unit) == URIRef("http://qudt.org/vocab/unit/V")


def test_grade_is_an_integer_literal():
    g = X.build_assertion(SYNTHETIC["graded_correspondence"], PAIR_CLAIMS).assertion
    grade = g.value(S.TEMP_NS["correspondence"], CV.grade)
    assert grade.datatype == XSD.integer and int(grade) == 2


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_non_finite_quantities_are_refused(bad):
    data = load_json(next(p for p in RECORDS if "claim-card" in p.name))
    data["record"]["quantity"]["value"] = bad
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
    data = copy.deepcopy(load_json(next(p for p in RECORDS if "refusal" in p.name)))
    data["record"]["outcome"] = "maybe"
    data["record"]["content_hash"] = verdict_hash(data["record"])
    data["receipt"]["content_hash"] = data["record"]["content_hash"]
    with pytest.raises(X.ExportError, match="unsupported_outcome"):
        X.build_assertion(parse_envelope(data), CLAIMS)


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


def test_unsigned_dry_run_trig_parses(tmp_path):
    from rdflib import Dataset
    env = load_envelope(next(p for p in RECORDS if "refusal" in p.name))
    ds = X.record_nanopub(env, AGENT, TEMPLATES, created="2026-11-16T00:00:00Z", claims=CLAIMS)
    out = tmp_path / "x.trig"
    out.write_text(X.to_trig(ds))
    back = Dataset()
    back.parse(out, format="trig")
    assert len(back) == len(ds)
    assert (S.TEMP_NS["refusal"], DCT.identifier, None) in back.graph(S.TEMP_NS["assertion"])
