"""The cross-theory records (pilot/theories/): receipts, mapping, signed TriG, wording."""

import copy
import hashlib
import json
import re
from pathlib import Path

import pytest
from rdflib import Dataset, Literal, URIRef

from consilience.export import nanopub as X
from consilience.export import spec as S
from consilience.export.vocab import CV, DCT, NP, NT, PROV, RDF, WD
from consilience.receipts import JSON_METHOD, ReceiptError, json_hash, load_envelope, parse_envelope, verify
from conftest import ROOT, THEORY_RECORDS, load_json

TEMPLATES = load_json(ROOT / "config" / "templates.json")
CLAIMS = X.Claims.load(ROOT / "pilot" / "claims.json")
REVIEW = load_json(ROOT / "config" / "review.json")
REVIEWER = URIRef(f"https://orcid.org/{REVIEW['reviewer_orcid']}")
TRIG = ROOT / "pilot" / "theories" / "trig"
CARDS = [p for p in THEORY_RECORDS if "theory-claim-card" in p.name]
FORKS = [p for p in THEORY_RECORDS if "disagreement" in p.name]


def _parse(path: Path):
    ds = Dataset()
    ds.parse(data=path.read_text(encoding="utf-8"), format="trig")
    head = next(g for g in ds.graphs() if (None, NP.hasAssertion, None) in g)
    np_uri = next(head.subjects(RDF.type, NP.Nanopublication))
    return np_uri, {k: ds.graph(head.value(np_uri, p)) for k, p in
                    (("assertion", NP.hasAssertion), ("provenance", NP.hasProvenance),
                     ("pubinfo", NP.hasPublicationInfo))}


def _sub(term, ns):
    if isinstance(term, URIRef) and str(term).startswith(str(S.TEMP_NS)):
        return URIRef(ns + str(term)[len(str(S.TEMP_NS)):])
    return term


def test_eleven_claim_cards_and_eight_disagreements_in_three_groups():
    assert len(CARDS) == 11 and len(FORKS) == 8
    groups = {}
    for p in FORKS:
        env = load_json(p)
        groups.setdefault(env["context"]["disagreement"], []).append(p)
    assert {k: len(v) for k, v in groups.items()} == {"location": 4, "time course": 3, "connectivity": 1}


@pytest.mark.parametrize("path", THEORY_RECORDS, ids=lambda p: p.stem)
def test_record_hash_reproduces(path):
    env = load_envelope(path)
    assert env.receipt["hash_method"] == JSON_METHOD
    assert verify(env) == env.content_hash == json_hash(env.record)


@pytest.mark.parametrize("path", THEORY_RECORDS, ids=lambda p: p.stem)
def test_record_is_identical_to_the_receipt_at_pinned_commit(path, engine):
    env = load_envelope(path)
    src = env.source
    text = engine(src["commit"], src["path"])
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == src["file_sha256"]
    manifest = json.loads(engine(src["commit"], "results/demo/MANIFEST.json"))
    assert {f["path"]: f["sha256"] for f in manifest["files"]}[src["path"]] == src["file_sha256"]
    s, e = src["lines"]
    chunk = "\n".join(text.split("\n")[s - 1:e]).rstrip(",")
    assert json.loads(chunk) == env.record
    assert env.receipt_url.endswith(f"#L{s}-L{e}")
    assert json_hash(json.loads(chunk)) == env.content_hash


def test_disagreements_point_at_the_claim_iris_of_published_claim_cards():
    card_urls = {load_envelope(p).receipt_url for p in CARDS}
    used = set()
    for p in FORKS:
        env = load_envelope(p)
        a, b = env.context["claim_a_receipt_url"], env.context["claim_b_receipt_url"]
        assert {a, b} <= card_urls
        used |= {a, b}
        left, right = env.record["left_ids"][0], env.record["right_ids"][0]
        ids = {load_envelope(c).receipt_url: load_envelope(c).record["claim_id"] for c in CARDS}
        assert (ids[a], ids[b]) == (left, right)
        g = X.build_assertion(env, CLAIMS).assertion
        me = S.TEMP_NS["disagreement"]
        assert g.value(me, CV.claimA) == URIRef(CLAIMS.entries[a]["claim_iri"])
        assert g.value(me, CV.claimB) == URIRef(CLAIMS.entries[b]["claim_iri"])
        assert "github.com" not in str(g.value(me, CV.claimA))
        # observables are observables, and the demo names no instrument
        assert set(g.objects(me, CV.observable)) and not set(g.objects(me, CV.instrument))
        assert g.value(me, CV.dimension) in (CV.Locus, CV.TemporalProfile, CV.Connectivity)
        assert g.value(me, CV.testability) == CV.TestableNow
        assert "names no specific instrument" in str(g.value(me, CV.testabilityReason))
    assert used == card_urls


@pytest.mark.parametrize("path", THEORY_RECORDS, ids=lambda p: p.stem)
def test_signed_trig_matches_the_envelope(path):
    env = load_envelope(path)
    trig = TRIG / f"{path.stem}.trig"
    assert X.check_signed(trig.read_text(encoding="utf-8"))
    np_uri, parts = _parse(trig)
    ns = str(np_uri) + "/"
    a = URIRef(ns + "assertion")
    built = X.build_assertion(env, CLAIMS)
    assert {(_sub(s, ns), p, _sub(o, ns)) for s, p, o in built.assertion} == set(parts["assertion"])
    res = S.check_conformance(built.spec, parts["assertion"], ns, a)
    assert res.ok, (res.unmatched, res.missing, res.bad_values)
    prov = parts["provenance"]
    assert prov.value(a, CV.contentHash) == Literal(env.content_hash)
    assert prov.value(a, CV.hashMethod) == Literal(JSON_METHOD)
    assert prov.value(a, PROV.wasDerivedFrom) == URIRef(env.receipt_url)
    assert prov.value(a, CV.sourceCommit) == Literal(env.source["commit"])
    pub = parts["pubinfo"]
    assert pub.value(np_uri, NT.wasCreatedFromTemplate) == URIRef(TEMPLATES[built.spec.key])
    note = str(pub.value(np_uri, DCT.description))
    assert "not a quotation" in note or "not quotations" in note
    assert env.source["commit"] in note
    if env.record_type == "theory_claim_card":
        # the reviewer is named, and what drafted the statement is stated generically
        assert prov.value(a, CV.reviewedBy) == REVIEWER
        assert prov.value(a, CV.draftedBy) == Literal(REVIEW["drafted_by"]) == Literal("a large language model")


@pytest.mark.parametrize("path", CARDS, ids=lambda p: p.stem)
def test_claim_card_states_reviewed_paraphrase_and_page(path):
    env = load_envelope(path)
    g = X.build_assertion(env).assertion
    me = S.TEMP_NS["claim"]
    assert (me, RDF.type, CV.TheoryClaim) in g
    assert (me, CV.statementForm, CV.ReviewedParaphrase) in g
    # theory, dimension and position are IRIs, not strings
    assert g.value(me, CV.theory) in (WD.Q6042884, CV.GlobalNeuronalWorkspaceTheory)
    assert isinstance(g.value(me, CV.dimension), URIRef) and isinstance(g.value(me, CV.position), URIRef)
    assert g.value(me, CV.claimStatement) == Literal(env.record["statement"])
    pages = {str(o) for loc in g.objects(me, CV.restsOn) for o in g.objects(loc, CV.pageLocator)}
    assert pages == {p["locator"] for p in env.record["prov"]}
    assert all(str(d).startswith("https://doi.org/") for loc in g.objects(me, CV.restsOn)
               for d in g.objects(loc, DCT.source))


def test_unapproved_card_is_refused():
    data = copy.deepcopy(load_json(CARDS[0]))
    data["record"]["status"] = "draft"
    data["receipt"]["content_hash"] = json_hash(data["record"])
    with pytest.raises(X.ExportError, match="claim_card_not_approved"):
        X.build_assertion(parse_envelope(data))


def test_fork_not_decidable_now_is_refused():
    data = copy.deepcopy(load_json(FORKS[0]))
    data["record"]["decidability"] = "not_current"
    data["receipt"]["content_hash"] = json_hash(data["record"])
    with pytest.raises(X.ExportError, match="demo_fork_not_decidable_now"):
        X.build_assertion(parse_envelope(data))


def test_an_instrument_the_record_does_not_name_is_refused():
    data = copy.deepcopy(load_json(FORKS[0]))
    data["context"]["instrument"] = "a better-sounding instrument"
    with pytest.raises(X.ExportError, match="instrument_not_named_by_the_record"):
        X.build_assertion(parse_envelope(data), CLAIMS)


def test_theory_card_needs_the_reviewer():
    env = load_envelope(CARDS[0])
    with pytest.raises(X.ExportError, match="needs_reviewer"):
        X.build_provenance(env, URIRef("https://example.org/agent"), None)


def test_tampered_theory_record_is_refused():
    data = copy.deepcopy(load_json(CARDS[0]))
    data["record"]["statement"] += " (edited)"
    with pytest.raises(ReceiptError, match="content_hash_mismatch"):
        verify(parse_envelope(data))


def test_json_hash_method_is_not_accepted_for_verdicts():
    data = copy.deepcopy(load_json(CARDS[0]))
    data["record_type"] = "comparison_refusal"
    with pytest.raises(ReceiptError, match="json_hash_method_not_allowed_for"):
        verify(parse_envelope(data))


# Wording rules for everything published about the cross-theory work.
FORBIDDEN = [r"typed subgraph matching", r"two exactly", r"third in part", r"discover"]
COGITATE = "2 of 3 after a disclosed re-review, originally 1 of 3, p = 0.075"


def _theory_texts():
    files = list(THEORY_RECORDS) + sorted(TRIG.glob("*.trig")) + [
        ROOT / "templates" / "theory_claim_card.trig", ROOT / "templates" / "disagreement.trig",
        ROOT / "config" / "review.json", ROOT / "PILOT.md", ROOT / "vocab" / "cv.ttl"]
    return [(p, p.read_text(encoding="utf-8")) for p in files]


def test_no_forbidden_wording_and_no_model_identifier():
    for p, text in _theory_texts():
        low = text.lower()
        for pat in FORBIDDEN:
            assert not re.search(pat, low), (p.name, pat)
        for marker in ("extractor_model", "drafting_model", "claude", "sonnet", "haiku", "gpt-"):
            assert marker not in low, (p.name, marker)


def test_pilot_page_uses_the_locked_cogitate_wording():
    page = (ROOT / "PILOT.md").read_text(encoding="utf-8")
    section = page[page.index("## COGITATE"):]
    assert COGITATE in section
    low = section.lower()
    for pat in FORBIDDEN:
        assert not re.search(pat, low), pat
