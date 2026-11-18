"""v2 of the nanopublication pilot, after review by Tobias Kuhn (Knowledge Pixels).

One section per point of the review:

1. claims have their own identity (a claim IRI that survives supersession);
2. people in the provenance (owner, template author, reviewer);
3. IRIs over strings (conditions, axes, instruments; refusals say which claim and which
   condition);
4. the general disagreement template (observables and instruments apart, testability
   constrained, always with a reason).
"""

import copy
import re
from pathlib import Path

import pytest
from rdflib import Dataset, Literal, URIRef

from consilience.export import nanopub as X
from consilience.export import spec as S
from consilience.export.vocab import CV, LABELS, NP, NPX, NT, QUDT, RDF, TERMS, vocab_graph
from consilience.receipts import json_hash, load_envelope, parse_envelope
from conftest import RECORDS, ROOT, THEORY_RECORDS, load_json

PUBS = load_json(ROOT / "pilot" / "publications.json")
CLAIMS = X.Claims.load(ROOT / "pilot" / "claims.json")
TEMPLATES = load_json(ROOT / "config" / "templates.json")
AGENT = load_json(ROOT / "config" / "agent.json")["agent_iri"]
TEMP = str(S.TEMP_NS)


def parse(path: Path):
    ds = Dataset()
    ds.parse(data=path.read_text(encoding="utf-8"), format="trig")
    head = next(g for g in ds.graphs() if (None, NP.hasAssertion, None) in g)
    np_uri = next(head.subjects(RDF.type, NP.Nanopublication))
    return np_uri, {k: ds.graph(head.value(np_uri, p)) for k, p in
                    (("assertion", NP.hasAssertion), ("provenance", NP.hasProvenance),
                     ("pubinfo", NP.hasPublicationInfo))}


def one(graph, predicate):
    """The single object of ``predicate`` in ``graph`` (fails if there is not exactly one)."""
    objs = set(graph.objects(None, predicate))
    assert len(objs) == 1, (predicate, objs)
    return objs.pop()


def trig_of(env_path: Path) -> Path:
    return env_path.parent.parent / "trig" / f"{env_path.stem}.trig"


REFUSALS = [p for p in RECORDS if "refusal" in p.name]
CARD_FILES = [p for p in list(RECORDS) + list(THEORY_RECORDS) if "claim-card" in p.name]
CARD_01 = next(p for p in RECORDS if p.name.startswith("01-claim-card"))
REFUSAL_04 = next(p for p in RECORDS if p.name.startswith("04-refusal"))


# --------------------------------------------------------------------------------------
# 1. Claims get their own identity

@pytest.mark.parametrize("path", CARD_FILES, ids=lambda p: p.stem)
def test_each_claim_card_introduces_its_own_claim_iri(path):
    np_uri, parts = parse(trig_of(path))
    claim = URIRef(f"{np_uri}/claim")
    assert set(parts["pubinfo"].objects(np_uri, NPX.introduces)) == {claim}
    assert (claim, RDF.type, None) in parts["assertion"]
    # the GitHub receipt is in the provenance, not the claim's identity
    env = load_envelope(path)
    assert "github.com" not in str(claim)
    assert parts["provenance"].value(URIRef(f"{np_uri}/assertion"),
                                     URIRef("http://www.w3.org/ns/prov#wasDerivedFrom")) == URIRef(env.receipt_url)


@pytest.mark.parametrize("path", [p for p in list(RECORDS) + list(THEORY_RECORDS)
                                  if "refusal" in p.name or "disagreement" in p.name], ids=lambda p: p.stem)
def test_refusals_and_disagreements_point_at_claim_iris(path):
    env = load_envelope(path)
    np_uri, parts = parse(trig_of(path))
    a = parts["assertion"]
    claim_iris = {e["claim_iri"] for e in CLAIMS.entries.values()}
    for p in (CV.claimA, CV.claimB):
        (obj,) = list(a.objects(None, p))
        assert str(obj) in claim_iris
        assert "github.com" not in str(obj)
    assert str(one(a, CV.claimA)) == CLAIMS.entries[env.context["claim_a_receipt_url"]]["claim_iri"]
    assert str(one(a, CV.claimB)) == CLAIMS.entries[env.context["claim_b_receipt_url"]]["claim_iri"]


def _superseding_version(created="2026-11-18T00:00:00Z"):
    env = load_envelope(CARD_01)
    old = CLAIMS.entries[env.receipt_url]
    sup = {"nanopub": old["nanopub"], "introduces": old["claim_iri"]}
    ds = X.record_nanopub(env, AGENT, TEMPLATES, created=created, claims=CLAIMS, supersedes=sup)
    return env, old, ds


def test_claim_iri_is_stable_across_supersession():
    env, old, ds = _superseding_version()
    a = ds.graph(S.TEMP_NS["assertion"])
    pub = ds.graph(S.TEMP_NS["pubinfo"])
    this = URIRef(TEMP)
    claim = URIRef(old["claim_iri"])
    # the corrected card supersedes the old nanopub ...
    assert (this, NPX.supersedes, URIRef(old["nanopub"])) in pub
    # ... and introduces the same claim IRI, written out in full (not sub:claim)
    assert set(pub.objects(this, NPX.introduces)) == {claim}
    assert (claim, RDF.type, CV.MeasuredClaim) in a
    assert (S.TEMP_NS["claim"], None, None) not in a
    # it still matches the template, with the carried IRI
    res = S.check_conformance(S.CLAIM_CARD, a, TEMP, S.TEMP_NS["assertion"],
                              carried={"claim": claim})
    assert res.ok, (res.unmatched, res.missing, res.bad_values)
    # and the refusal that points at the claim is unchanged: its link stays valid
    np04, parts04 = parse(trig_of(REFUSAL_04))
    assert one(parts04["assertion"], CV.claimA) == claim


def test_superseding_version_signs_to_a_new_uri_with_the_same_claim():
    from consilience.agent import AgentError, profile_for
    try:
        prof = profile_for(AGENT, "The Consilience engine")
    except AgentError:
        pytest.skip("no local key on this machine")
    env, old, ds = _superseding_version()
    uri, trig = X.sign(ds, prof)
    assert uri != old["nanopub"]
    back = Dataset()
    back.parse(data=trig, format="trig")
    assert (URIRef(uri), NPX.introduces, URIRef(old["claim_iri"])) in back.graph(URIRef(uri + "/pubinfo"))
    assert (URIRef(uri), NPX.supersedes, URIRef(old["nanopub"])) in back.graph(URIRef(uri + "/pubinfo"))


def test_supersession_cannot_mint_a_new_claim_iri():
    env = load_envelope(CARD_01)
    old = CLAIMS.entries[env.receipt_url]
    with pytest.raises(X.ExportError, match="supersedes.introduces_must_be_the_old_nanopub"):
        X.build_assertion(env, CLAIMS, {"nanopub": old["nanopub"],
                                        "introduces": "https://w3id.org/np/RAother/claim"})


def test_dry_run_supersession_example_is_documented_and_not_published():
    path = ROOT / "docs" / "examples" / "supersede-claim-card-01.dry-run.trig"
    text = path.read_text(encoding="utf-8")
    env = load_envelope(CARD_01)
    old = CLAIMS.entries[env.receipt_url]
    assert old["claim_iri"] in text and old["nanopub"] in text
    assert "npx:supersedes" in text or str(NPX.supersedes) in text
    assert "hasSignature" not in text            # unsigned: it cannot be published as it stands
    assert not any(e.get("supersedes") for e in PUBS.values())


# --------------------------------------------------------------------------------------
# 3. IRIs over strings

LITERAL_OK = {  # predicates whose object is meant to be text or a number
    "http://purl.org/dc/terms/identifier", str(CV.sourceSentence), str(CV.subjectName),
    str(QUDT.numericValue), str(CV.unitAsWritten), str(CV.claimStatement), str(CV.pageLocator),
    str(CV.rule), str(CV.valueInClaimA), str(CV.valueInClaimB), str(CV.claimASentence),
    str(CV.claimBSentence), str(CV.testabilityReason), str(CV.assumption), str(CV.margin),
    str(CV.floor), str(CV.defectTarget), "http://purl.org/dc/terms/description", str(CV.check),
    str(CV.recordsChecked), str(CV.recordsFlagged), str(CV.grade), str(CV.gradeCeiling),
    str(CV.equivocation),
}
SNAKE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)+$")


@pytest.mark.parametrize("path", [trig_of(p) for p in list(RECORDS) + list(THEORY_RECORDS)],
                         ids=lambda p: p.stem)
def test_no_condition_axis_or_instrument_is_a_string(path):
    np_uri, parts = parse(path)
    for s, p, o in parts["assertion"]:
        if isinstance(o, Literal):
            assert str(p) in LITERAL_OK, (path.name, p, o)
            if p != URIRef("http://purl.org/dc/terms/identifier"):  # source ids stay as written
                assert not SNAKE.match(str(o)), (path.name, p, o)   # no snake_case values
        assert p not in (CV.conditionName, CV.conditionValueJson, CV.hasCondition, CV.objectName,
                         CV.relation, CV.canonicalUnit), (path.name, p)
    for p in (CV.condition, CV.conditionUnstated, CV.conditionValue, CV.axis, CV.dimension,
              CV.position, CV.theory, CV.observable, CV.instrument, CV.measurableWith,
              CV.claimKind, QUDT.unit, CV.unstatedIn, CV.axisOfClaimA, CV.axisOfClaimB):
        for o in parts["assertion"].objects(None, p):
            assert isinstance(o, URIRef), (path.name, p, o)


def test_conditions_are_structured_triples_not_json():
    np_uri, parts = parse(trig_of(CARD_01))
    a = parts["assertion"]
    claim = URIRef(f"{np_uri}/claim")
    nodes = list(a.objects(claim, CV.statesQuantityCondition))
    assert nodes
    for n in nodes:
        assert isinstance(a.value(n, CV.condition), URIRef)
        assert a.value(n, QUDT.numericValue).datatype == URIRef("http://www.w3.org/2001/XMLSchema#decimal")
        assert isinstance(a.value(n, QUDT.unit), URIRef)
    assert "{" not in " ".join(str(o) for o in a.objects() if isinstance(o, Literal)
                               and not str(o).startswith(("After", "Furthermore")))


def test_record_04_says_only_claim_b_lacks_the_electrolyte_and_names_the_differing_condition():
    env = load_envelope(REFUSAL_04)
    np_uri, parts = parse(trig_of(REFUSAL_04))
    a = parts["assertion"]
    claim_a, claim_b = one(a, CV.claimA), one(a, CV.claimB)
    lacking = {}
    for n in a.objects(None, CV.hasUnstatedCondition):
        lacking.setdefault(a.value(n, CV.condition), set()).add(a.value(n, CV.unstatedIn))
        assert a.value(n, CV.rule) is not None
    assert lacking[CV.Electrolyte] == {claim_b}                    # only claim B lacks it
    assert lacking[CV.Temperature] == {claim_a, claim_b}
    assert lacking[CV.IRCorrection] == {claim_a, claim_b}
    (m,) = list(a.objects(None, CV.hasConditionMismatch))
    assert a.value(m, CV.condition) == CV.CurrentDensity           # which condition differs
    assert a.value(m, CV.rule) == Literal("CR2")                   # the rule id, kept as a field
    assert (float(a.value(m, CV.valueInClaimA)), float(a.value(m, CV.valueInClaimB))) == (10.0, 100.0)
    assert a.value(m, QUDT.unit) == CV["MilliA-PER-CentiM2"]
    assert env.record["defects"][1] == {"defect_type": "condition_mismatch", "target": "CR2"}


@pytest.mark.parametrize("path", REFUSALS, ids=lambda p: p.stem)
def test_every_unstated_defect_names_exactly_the_claims_that_lack_it(path):
    env = load_envelope(path)
    np_uri, parts = parse(trig_of(path))
    a = parts["assertion"]
    card = {CLAIMS.entries[env.context[k]]["claim_iri"]: CLAIMS.card(env.context[k])
            for k in ("claim_a_receipt_url", "claim_b_receipt_url")}
    got = {}
    for n in a.objects(None, CV.hasUnstatedCondition):
        got.setdefault(a.value(n, CV.condition), set()).add(str(a.value(n, CV.unstatedIn)))
    from consilience.export.mapping import CONDITIONS
    want = {}
    for d in env.record["defects"]:
        if d["defect_type"] == "condition_unstated":
            want[CONDITIONS[d["target"]]] = {iri for iri, c in card.items()
                                             if c.record["conditions"].get(d["target"], "unstated") == "unstated"}
    assert got == want
    rules = {d["target"] for d in env.record["defects"] if d["defect_type"] == "condition_mismatch"}
    assert {str(a.value(m, CV.rule)) for m in a.objects(None, CV.hasConditionMismatch)} == rules


def test_axis_mismatch_names_both_axes_as_iris():
    path = next(p for p in REFUSALS if p.name.startswith("06-"))
    np_uri, parts = parse(trig_of(path))
    a = parts["assertion"]
    assert one(a, CV.axisOfClaimA) == CV.HoursToThreshold
    assert one(a, CV.axisOfClaimB) == CV.OperationalStabilityDuration


def test_unsupported_claim_card_condition_is_refused():
    data = copy.deepcopy(load_json(CARD_01))
    data["record"]["conditions"]["temperature"] = "room_temperature"
    from consilience.receipts import card_hash
    data["receipt"]["content_hash"] = card_hash(data["record"])
    with pytest.raises(X.ExportError, match="unsupported_condition_value"):
        X.build_assertion(parse_envelope(data))


# --------------------------------------------------------------------------------------
# 4. The disagreement template

def test_testability_values_are_constrained_to_three():
    ph = S.DISAGREEMENT.statement("st08").o
    assert set(ph.values) == {CV.TestableNow, CV.TestableUnderAssumption, CV.NotYetTestable}
    assert CV.NotTestable not in ph.values
    np_uri, parts = parse(ROOT / "templates" / "disagreement.trig")
    allowed = set(parts["assertion"].objects(URIRef(f"{np_uri}/testability"),
                                             URIRef("https://w3id.org/np/o/ntemplate/possibleValue")))
    assert allowed == set(ph.values)


def test_template_c_is_no_longer_called_testable_and_separates_observable_from_instrument():
    labels = {st.id: (st.p, st.o.label if isinstance(st.o, S.PH) else None) for st in S.DISAGREEMENT.statements}
    assert "testable now" not in S.DISAGREEMENT.label
    assert labels["st05"][0] == CV.dimension
    assert labels["st06"][0] == CV.observable and "observable" in labels["st06"][1]
    assert labels["st07"][0] == CV.instrument and "instrument" in labels["st07"][1]
    assert CV.axis not in {st.p for st in S.DISAGREEMENT.statements}
    assert CV.axis not in {st.p for st in S.THEORY_CLAIM_CARD.statements}   # "locus" is not a quantity axis
    assert not S.DISAGREEMENT.statement("st09").optional                   # a reason is required


def test_a_not_testable_status_is_refused():
    from test_mapping import FORK, PAIR_CLAIMS, PAIR_CTX, _synthetic
    for status in ("not_testable", "maybe"):
        env = _synthetic("disagreement", FORK, {**PAIR_CTX, "testability": status,
                                                "testability_reason": "x"})
        with pytest.raises(X.ExportError, match="unsupported_testability"):
            X.build_assertion(env, PAIR_CLAIMS)


def test_conformance_rejects_a_disagreement_marked_not_testable():
    env = load_envelope(next(p for p in THEORY_RECORDS if "disagreement" in p.name))
    built = X.build_assertion(env, CLAIMS)
    g = built.assertion
    me = S.TEMP_NS["disagreement"]
    g.remove((me, CV.testability, None))
    g.add((me, CV.testability, CV.NotTestable))
    res = S.check_conformance(S.DISAGREEMENT, g, TEMP, S.TEMP_NS["assertion"])
    assert not res.ok


def test_testability_needs_reason_and_assumption():
    from test_mapping import FORK, PAIR_CLAIMS, PAIR_CTX, _synthetic
    env = _synthetic("disagreement", FORK, {**PAIR_CTX, "testability": "not_yet_testable"})
    with pytest.raises(X.ExportError, match="testability_needs_a_reason"):
        X.build_assertion(env, PAIR_CLAIMS)
    env = _synthetic("disagreement", FORK, {**PAIR_CTX, "testability": "testable_under_assumption",
                                            "testability_reason": "x"})
    with pytest.raises(X.ExportError, match="needs_the_assumption"):
        X.build_assertion(env, PAIR_CLAIMS)
    env = _synthetic("disagreement", FORK, {**PAIR_CTX, "testability": "not_yet_testable",
                                            "testability_reason": "no instrument resolves it"})
    g = X.build_assertion(env, PAIR_CLAIMS).assertion
    assert g.value(S.TEMP_NS["disagreement"], CV.testability) == CV.NotYetTestable


def test_demo_fork_not_decidable_now_is_still_refused():
    data = copy.deepcopy(load_json(next(p for p in THEORY_RECORDS if "disagreement" in p.name)))
    data["record"]["decidability"] = "not_current"
    data["receipt"]["content_hash"] = json_hash(data["record"])
    with pytest.raises(X.ExportError, match="demo_fork_not_decidable_now"):
        X.build_assertion(parse_envelope(data), CLAIMS)


# --------------------------------------------------------------------------------------
# The vocabulary

def test_cv_ttl_is_generated_from_the_terms_table():
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "write_vocab.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    g = vocab_graph()
    for local, t in TERMS.items():
        assert (CV[local], URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None) in g
        assert t["comment"].strip()


def test_every_cv_term_used_by_v2_is_defined_and_current():
    files = sorted((ROOT / "pilot").rglob("*.trig")) + sorted((ROOT / "templates").glob("*.trig")) \
        + [ROOT / "agent" / "introduction.trig"]
    deprecated = {CV[k] for k, t in TERMS.items() if t.get("deprecated")}
    for f in files:
        ds = Dataset()
        ds.parse(data=f.read_text(encoding="utf-8"), format="trig")
        for s, p, o, _ in ds.quads():
            for term in (s, p, o):
                if isinstance(term, URIRef) and str(term).startswith(str(CV)):
                    assert term in LABELS, (f.name, term)
                    assert term not in deprecated, (f.name, term)
