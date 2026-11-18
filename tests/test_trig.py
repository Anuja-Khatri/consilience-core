"""The committed v2 TriG files are valid, signed nanopublications that match their records."""

import json
import os
import urllib.request
from pathlib import Path

import pytest
from rdflib import Dataset, Literal, URIRef

from consilience.export import nanopub as X
from consilience.export import spec as S
from consilience.export.vocab import CV, DCT, FOAF, FRBR, NP, NPX, NT, PROV, RDF
from consilience.receipts import load_envelope
from conftest import ROOT, load_json

AGENT_CFG = load_json(ROOT / "config" / "agent.json")
TEMPLATES = load_json(ROOT / "config" / "templates.json")
PUBS = load_json(ROOT / "pilot" / "publications.json")
CLAIMS = X.Claims.load(ROOT / "pilot" / "claims.json")
REVIEW = load_json(ROOT / "config" / "review.json")
AGENT = URIRef(AGENT_CFG["agent_iri"])
OWNER = URIRef(f"https://orcid.org/{AGENT_CFG['responsible_person_orcid']}")

RECORD_TRIG = sorted((ROOT / "pilot" / "trig").glob("*.trig")) \
    + sorted((ROOT / "pilot" / "theories" / "trig").glob("*.trig"))
EXAMPLE_TRIG = sorted((ROOT / "pilot" / "examples" / "trig").glob("*.trig"))
TEMPLATE_TRIG = sorted((ROOT / "templates").glob("*.trig"))
SIGNED = RECORD_TRIG + EXAMPLE_TRIG + TEMPLATE_TRIG + [ROOT / "agent" / "introduction.trig"]


def parse(path: Path):
    ds = Dataset()
    ds.parse(data=path.read_text(encoding="utf-8"), format="trig")
    heads = [g for g in ds.graphs() if (None, NP.hasAssertion, None) in g]
    assert len(heads) == 1
    head = heads[0]
    np_uri = next(head.subjects(RDF.type, NP.Nanopublication))
    parts = {k: ds.graph(head.value(np_uri, p)) for k, p in
             (("assertion", NP.hasAssertion), ("provenance", NP.hasProvenance),
              ("pubinfo", NP.hasPublicationInfo))}
    return np_uri, parts


def sub(term, ns):
    if isinstance(term, URIRef) and str(term).startswith(str(S.TEMP_NS)):
        return URIRef(ns + str(term)[len(str(S.TEMP_NS)):])
    return term


def envelope_of(trig: Path) -> Path:
    if trig.parent.name == "trig" and trig.parent.parent.name == "examples":
        return ROOT / "pilot" / "examples" / f"{trig.stem}.json"
    base = trig.parent.parent  # pilot/ or pilot/theories/
    return base / "records" / f"{trig.stem}.json"


def test_counts():
    assert len(TEMPLATE_TRIG) == 7
    assert len(list((ROOT / "pilot" / "trig").glob("*.trig"))) == 18      # 10 pilot + 8 supporting cards
    assert len(list((ROOT / "pilot" / "theories" / "trig").glob("*.trig"))) == 19
    assert len(EXAMPLE_TRIG) == 2
    assert len(PUBS) == 1 + 7 + 18 + 19 + 2


@pytest.mark.parametrize("path", SIGNED, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_signed_trig_is_a_valid_nanopub(path):
    trig = path.read_text(encoding="utf-8")
    uri = X.check_signed(trig)          # trusty URI and RSA signature both verify
    np_uri, parts = parse(path)
    assert str(np_uri) == uri
    assert all(len(g) > 0 for g in parts.values())
    pub = parts["pubinfo"]
    sig = next(pub.subjects(NPX.hasSignatureTarget, np_uri))
    assert pub.value(sig, NPX.hasPublicKey) == Literal(AGENT_CFG["public_key"])
    assert pub.value(sig, NPX.signedBy) == AGENT      # everything is signed by the engine's key
    assert pub.value(np_uri, DCT.license) == URIRef("https://creativecommons.org/licenses/by/4.0/")
    assert pub.value(np_uri, NT.wasCreatedFromTemplate) is not None
    assert pub.value(np_uri, NT.wasCreatedFromProvenanceTemplate) is not None


def test_every_signed_file_is_recorded_as_a_test_publication():
    files = {v["file"]: v for v in PUBS.values()}
    for path in SIGNED:
        rel = str(path.relative_to(ROOT))
        assert rel in files, rel
        entry = files[rel]
        assert entry["registry"] == "test"
        assert entry["resolves_at"].startswith("https://test.registry.knowledgepixels.com/np/RA")
        assert entry["nanopub"] == str(parse(path)[0])
        assert entry["supersedes"] is None   # nothing published in v2 supersedes anything


@pytest.mark.parametrize("path", RECORD_TRIG, ids=lambda p: p.stem)
def test_published_record_matches_its_envelope(path):
    env = load_envelope(envelope_of(path))
    np_uri, parts = parse(path)
    ns = str(np_uri) + "/"
    a = URIRef(ns + "assertion")
    prov = parts["provenance"]
    assert prov.value(a, CV.contentHash) == Literal(env.content_hash)
    assert prov.value(a, PROV.wasDerivedFrom) == URIRef(env.receipt_url)   # the GitHub receipt
    assert prov.value(a, CV.sourceCommit) == Literal(env.source["commit"])
    assert prov.value(a, PROV.wasAttributedTo) == AGENT
    # the assertion equals what the exporter builds today, once the namespace is substituted
    built = X.build_assertion(env, CLAIMS)
    rebuilt = {(sub(s, ns), p, sub(o, ns)) for s, p, o in built.assertion}
    assert rebuilt == set(parts["assertion"])
    res = S.check_conformance(built.spec, parts["assertion"], ns, a)
    assert res.ok, (res.unmatched, res.missing, res.bad_values)
    res = S.check_conformance(S.RECEIPT_PROVENANCE, prov, ns, a)
    assert res.ok, (res.unmatched, res.missing, res.bad_values)
    pub = parts["pubinfo"]
    assert pub.value(np_uri, DCT.creator) == AGENT
    assert pub.value(np_uri, NT.wasCreatedFromTemplate) == URIRef(TEMPLATES[built.spec.key])
    assert pub.value(np_uri, NT.wasCreatedFromProvenanceTemplate) == URIRef(TEMPLATES["receipt_provenance"])
    assert pub.value(np_uri, NPX.introduces) == sub(built.main, ns)


def test_claim_registry_matches_the_published_claim_cards():
    by_file = {v["file"]: v["nanopub"] for v in PUBS.values()}
    assert len(CLAIMS.entries) == 11 + 11
    for url, e in CLAIMS.entries.items():
        env = load_envelope(ROOT / e["envelope"])
        assert env.receipt_url == url and env.record["claim_id"] == e["claim_id"]
        trig = ROOT / ("pilot/theories/trig" if "theories" in e["envelope"] else "pilot/trig") \
            / f"{Path(e['envelope']).stem}.trig"
        np_uri, parts = parse(trig)
        assert by_file[str(trig.relative_to(ROOT))] == str(np_uri) == e["nanopub"]
        assert e["claim_iri"] == str(np_uri) + "/claim"
        assert (np_uri, NPX.introduces, URIRef(e["claim_iri"])) in parts["pubinfo"]


@pytest.mark.parametrize("key", list(S.ALL_SPECS))
def test_published_template_matches_its_spec_and_is_attributed_to_the_owner(key):
    path = ROOT / "templates" / f"{key}.trig"
    np_uri, parts = parse(path)
    ns = str(np_uri) + "/"
    assert TEMPLATES[key] == ns + "templateVersion"
    expected = {(sub(s, ns), p, sub(o, ns)) for s, p, o in S.template_assertion_graph(S.ALL_SPECS[key])}
    assert expected == set(parts["assertion"])
    pub = parts["pubinfo"]
    assert (np_uri, NPX.embeds, URIRef(ns + "templateVersion")) in pub
    # attributed to Anuja Khatri (ORCID), signed by the engine (checked above)
    assert pub.value(np_uri, DCT.creator) == OWNER
    assert pub.value(OWNER, FOAF.name) == Literal(AGENT_CFG["responsible_person_name"])
    assert parts["provenance"].value(URIRef(ns + "assertion"), PROV.wasAttributedTo) == OWNER


@pytest.mark.parametrize("path", EXAMPLE_TRIG, ids=lambda p: p.stem)
def test_examples_are_marked_as_examples(path):
    np_uri, parts = parse(path)
    pub = parts["pubinfo"]
    assert str(pub.value(np_uri, URIRef("http://www.w3.org/2000/01/rdf-schema#label"))).startswith("Example: ")
    assert (np_uri, NPX.hasNanopubType, NPX.ExampleNanopub) in pub
    assert "made up" in str(pub.value(np_uri, DCT.description))
    env = load_envelope(envelope_of(path))
    built = X.build_assertion(env, X.Claims.load(ROOT / "pilot" / "examples" / "claims.json"))
    ns = str(np_uri) + "/"
    assert {(sub(s, ns), p, sub(o, ns)) for s, p, o in built.assertion} == set(parts["assertion"])
    for o in parts["assertion"].objects():
        if isinstance(o, URIRef) and "example" in str(o):
            assert str(o).startswith("https://example.org/")


def test_introduction_names_the_owner_by_orcid():
    np_uri, parts = parse(ROOT / "agent" / "introduction.trig")
    a = parts["assertion"]
    assert (AGENT, RDF.type, NPX.SoftwareAgent) in a
    assert (AGENT, FRBR.owner, OWNER) in a
    decl = next(a.subjects(NPX.declaredBy, AGENT))
    assert a.value(decl, NPX.hasPublicKey) == Literal(AGENT_CFG["public_key"])
    assert (np_uri, NPX.introduces, AGENT) in parts["pubinfo"]
    assert (OWNER, FOAF.name, Literal(AGENT_CFG["responsible_person_name"])) in parts["pubinfo"]
    assert parts["provenance"].value(URIRef(str(np_uri) + "/assertion"), PROV.wasAttributedTo) == OWNER
    assert str(AGENT) == str(np_uri) + "/" + AGENT_CFG["agent_local_name"]
    old = AGENT_CFG["previous_introductions"][0]["agent_iri"]
    assert old != str(AGENT)   # v2 is a new introduction, so the agent IRI changed


@pytest.mark.parametrize("path", sorted((ROOT / "archive" / "v1").rglob("*.trig")), ids=lambda p: p.stem)
def test_v1_files_are_kept_and_still_verify(path):
    assert X.check_signed(path.read_text(encoding="utf-8"))


@pytest.mark.skipif(bool(os.environ.get("CONSILIENCE_OFFLINE")), reason="offline")
@pytest.mark.parametrize("name", sorted(PUBS), ids=str)
def test_publication_resolves_on_the_test_server(name):
    entry = PUBS[name]
    req = urllib.request.Request(entry["resolves_at"], headers={"Accept": "application/trig"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8")
    except OSError as exc:
        pytest.skip(f"test server not reachable: {exc}")
    assert X.check_signed(text) == entry["nanopub"]


def test_publications_record_has_no_live_entries():
    assert {e["registry"] for e in PUBS.values()} == {"test"}
    assert json.dumps(PUBS).count("registry.knowledgepixels.com/np/") == \
        json.dumps(PUBS).count("test.registry.knowledgepixels.com/np/")
