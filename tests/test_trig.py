"""The committed TriG files are valid, signed nanopublications that match their records."""

import json
import os
import urllib.request
from pathlib import Path

import pytest
from rdflib import Dataset, Literal, URIRef

from consilience.export import nanopub as X
from consilience.export import spec as S
from consilience.export.vocab import CV, DCT, NP, NPX, NT, PROV, RDF
from consilience.receipts import load_envelope
from conftest import RECORDS, ROOT, load_json

AGENT_CFG = load_json(ROOT / "config" / "agent.json")
TEMPLATES = load_json(ROOT / "config" / "templates.json")
PUBS = load_json(ROOT / "pilot" / "publications.json")
AGENT = URIRef(AGENT_CFG["agent_iri"])

SIGNED = sorted((ROOT / "pilot" / "trig").glob("*.trig")) + sorted((ROOT / "templates").glob("*.trig")) \
    + [ROOT / "agent" / "introduction.trig"]


def _parse(path: Path):
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


@pytest.mark.parametrize("path", SIGNED, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_signed_trig_is_a_valid_nanopub(path):
    trig = path.read_text(encoding="utf-8")
    uri = X.check_signed(trig)          # trusty URI and RSA signature both verify
    np_uri, parts = _parse(path)
    assert str(np_uri) == uri
    assert all(len(g) > 0 for g in parts.values())
    pub = parts["pubinfo"]
    sig = next(pub.subjects(NPX.hasSignatureTarget, np_uri))
    assert pub.value(sig, NPX.hasPublicKey) == Literal(AGENT_CFG["public_key"])
    assert pub.value(sig, NPX.signedBy) == AGENT
    assert pub.value(np_uri, DCT.creator) == AGENT
    assert pub.value(np_uri, DCT.license) == URIRef("https://creativecommons.org/licenses/by/4.0/")


def test_every_signed_file_is_recorded_as_a_test_publication():
    files = {v["file"]: v for v in PUBS.values()}
    for path in SIGNED:
        rel = str(path.relative_to(ROOT))
        assert rel in files, rel
        entry = files[rel]
        assert entry["registry"] == "test"
        assert entry["resolves_at"].startswith("https://test.registry.knowledgepixels.com/np/RA")
        assert entry["nanopub"] == str(_parse(path)[0])


@pytest.mark.parametrize("path", RECORDS, ids=lambda p: p.stem)
def test_published_record_matches_its_envelope(path):
    env = load_envelope(path)
    trig_path = ROOT / "pilot" / "trig" / f"{path.stem}.trig"
    np_uri, parts = _parse(trig_path)
    ns = str(np_uri) + "/"
    a = URIRef(ns + "assertion")
    prov = parts["provenance"]
    assert prov.value(a, CV.contentHash) == Literal(env.content_hash)
    assert prov.value(a, PROV.wasDerivedFrom) == URIRef(env.receipt_url)
    assert prov.value(a, CV.sourceCommit) == Literal(env.source["commit"])
    # assertion equals what the exporter builds today, once the namespace is substituted
    built = X.build_assertion(env)
    rebuilt = {(_sub(s, ns), p, _sub(o, ns)) for s, p, o in built.assertion}
    assert rebuilt == set(parts["assertion"])
    res = S.check_conformance(built.spec, parts["assertion"], ns, a)
    assert res.ok, (res.unmatched, res.missing, res.bad_values)
    pub = parts["pubinfo"]
    assert pub.value(np_uri, NT.wasCreatedFromTemplate) == URIRef(TEMPLATES[built.spec.key])
    assert pub.value(np_uri, NT.wasCreatedFromProvenanceTemplate) == URIRef(TEMPLATES["receipt_provenance"])


def _sub(term, ns):
    if isinstance(term, URIRef) and str(term).startswith(str(S.TEMP_NS)):
        return URIRef(ns + str(term)[len(str(S.TEMP_NS)):])
    return term


@pytest.mark.parametrize("key", list(S.ALL_SPECS))
def test_published_template_matches_its_spec(key):
    path = ROOT / "templates" / f"{key}.trig"
    np_uri, parts = _parse(path)
    ns = str(np_uri) + "/"
    assert TEMPLATES[key] == ns + "templateVersion"
    expected = {(_sub(s, ns), p, _sub(o, ns)) for s, p, o in S.template_assertion_graph(S.ALL_SPECS[key])}
    assert expected == set(parts["assertion"])
    assert (np_uri, NPX.embeds, URIRef(ns + "templateVersion")) in parts["pubinfo"]


def test_dry_run_unsigned_trig_parses(tmp_path):
    env = load_envelope(RECORDS[3])
    ds = X.record_nanopub(env, str(AGENT), TEMPLATES, created="2026-11-16T00:00:00Z")
    out = tmp_path / "x.trig"
    out.write_text(X.to_trig(ds))
    back = Dataset()
    back.parse(out, format="trig")
    assert len(back) == len(ds)


def test_introduction_declares_the_engine_as_software():
    np_uri, parts = _parse(ROOT / "agent" / "introduction.trig")
    a = parts["assertion"]
    assert (AGENT, RDF.type, NPX.SoftwareAgent) in a
    decl = next(a.subjects(NPX.declaredBy, AGENT))
    assert a.value(decl, NPX.hasPublicKey) == Literal(AGENT_CFG["public_key"])
    assert (np_uri, NPX.introduces, AGENT) in parts["pubinfo"]
    # no ORCID is invented: none appears until Anu supplies hers
    if not AGENT_CFG["responsible_person_orcid"]:
        text = (ROOT / "agent" / "introduction.trig").read_text()
        assert "orcid.org" not in text


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
