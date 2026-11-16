"""Export Consilience records as nanopublications.

A record envelope (see ``consilience.receipts``) becomes one nanopublication:

- **assertion**: the record's statement (a comparison refusal, a claim card, a graded
  correspondence, a testable disagreement or a data-quality finding), shaped exactly as
  the matching template in ``consilience.export.spec`` says;
- **provenance**: the receipt: the source repository and pinned commit, a link to the
  record at that commit, the content hash and the method that reproduces it, and the
  code, rule and map versions that produced the record;
- **publication info**: the software agent as creator, the CC BY 4.0 licence, a label,
  and links to the templates.

Every record is checked against its receipt before anything is built; a record whose
hash does not reproduce is refused.

Signing uses the ``nanopub`` package with the agent's local key. Publishing goes to the
Knowledge Pixels **test** registry only.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
from dataclasses import dataclass

import requests
from rdflib import Dataset, Graph, Literal, URIRef

from .. import __version__
from ..agent import TEST_REGISTRY_URL
from ..receipts import Envelope, ReceiptError, verify
from . import spec as S
from .vocab import (
    CC_BY_4, CV, DCT, FOAF, FRBR, META_ASSERTION_TEMPLATE, META_PROVENANCE_TEMPLATE, NP, NPX,
    NT, PROV, PROV_TEMPLATE_ATTRIBUTED, PUBINFO_TEMPLATE_CREATOR, PUBINFO_TEMPLATE_LICENSE,
    RDF, RDFS, SCHEMA, XSD,
)

SUB = S.TEMP_NS
THIS = URIRef(str(SUB))  # the nanopub itself, before signing
EXPORTER = f"consilience {__version__} (github.com/Anuja-Khatri/consilience-core)"

AGENT_INTRO_TEMPLATE = URIRef("https://w3id.org/np/RAbn04KkfbV5PK2UDGkp-j7RUghs_y75DL4qWl_8zQQ3w")

_OUTCOMES = {"not_comparable": CV.NotComparable, "axis_mismatch": CV.AxisMismatch}
_DEFECTS = {
    "condition_unstated": CV.ConditionUnstated,
    "condition_mismatch": CV.ConditionMismatch,
    "axis_mismatch": CV.AxisMismatch,
    "type_mismatch": CV.TypeMismatch,
    "quantity_refused": CV.QuantityRefused,
}
_TESTABILITY = {
    "measurable_now": CV.TestableNow,
    "testable_now": CV.TestableNow,
    "testable_under_assumption": CV.TestableUnderAssumption,
    "not_testable": CV.NotTestable,
}


class ExportError(ValueError):
    """A record cannot be exported as it stands. The message names the reason."""


def _need(cond, reason):
    if not cond:
        raise ExportError(reason)


def _lit(v) -> Literal:
    _need(isinstance(v, str) and v.strip() != "", f"empty_or_non_text_value: {v!r}")
    return Literal(v)


def _dec(v) -> Literal:
    _need(isinstance(v, (int, float)) and not isinstance(v, bool), f"non_numeric_value: {v!r}")
    _need(math.isfinite(v), f"non_finite_value: {v!r}")
    return Literal(repr(float(v)) if isinstance(v, float) else str(v), datatype=XSD.decimal)


def _int(v) -> Literal:
    _need(isinstance(v, int) and not isinstance(v, bool), f"non_integer_value: {v!r}")
    return Literal(str(v), datatype=XSD.integer)


def _iri(v, what) -> URIRef:
    _need(isinstance(v, str) and v.startswith("https://"), f"missing_or_non_https_iri: {what}={v!r}")
    return URIRef(v)


def _local(name: str, i: int) -> URIRef:
    """Local resource names follow Nanodash's repeat convention: name, name__1, name__2..."""
    return SUB[name if i == 0 else f"{name}__{i}"]


def _short(text: str, n: int = 200) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


# ---------------------------------------------------------------------------------------
# Assertions

@dataclass
class Built:
    spec: S.TemplateSpec
    assertion: Graph
    main: URIRef           # the record's main resource
    introduced: bool       # whether the nanopub introduces ``main``
    label: str


def _pair_claims(env: Envelope) -> tuple[URIRef, URIRef]:
    a = _iri(env.context.get("claim_a_receipt_url"), "context.claim_a_receipt_url")
    b = _iri(env.context.get("claim_b_receipt_url"), "context.claim_b_receipt_url")
    return a, b


def _refusal(env: Envelope) -> Built:
    r = env.record
    _need(r.get("kind") == "rejection", f"not_a_rejection_record: kind={r.get('kind')!r}")
    outcome = _OUTCOMES.get(r.get("outcome"))
    _need(outcome is not None, f"unsupported_outcome: {r.get('outcome')!r}")
    defects = r.get("defects") or []
    _need(isinstance(defects, list) and defects, "refusal_without_defects")
    a, b = _pair_claims(env)
    g = Graph()
    me = SUB["refusal"]
    g.add((me, RDF.type, CV.ComparisonRefusal))
    g.add((me, DCT.identifier, _lit(r["pair_id"])))
    g.add((me, CV.claimA, a))
    g.add((me, CV.claimB, b))
    if r.get("axis") is not None:
        g.add((me, CV.axis, _lit(r["axis"])))
    g.add((me, CV.outcome, outcome))
    unstated, differs, other = [], [], []
    for i, d in enumerate(defects):
        dt = _DEFECTS.get(d.get("defect_type"))
        _need(dt is not None, f"unsupported_defect_type: {d.get('defect_type')!r}")
        node = _local("defect", i)
        g.add((me, CV.hasDefect, node))
        g.add((node, CV.defectType, dt))
        g.add((node, CV.defectTarget, _lit(d.get("target"))))
        if dt == CV.ConditionUnstated:
            unstated.append(d["target"])
        elif dt == CV.ConditionMismatch:
            differs.append(d["target"])
        else:
            other.append(d["target"])
    if r.get("claim_a_sentence"):
        g.add((me, CV.claimASentence, _lit(r["claim_a_sentence"])))
    if r.get("claim_b_sentence"):
        g.add((me, CV.claimBSentence, _lit(r["claim_b_sentence"])))
    parts = []
    if other:
        parts.append("different quantity axes (" + "; ".join(other) + ")"
                     if outcome == CV.AxisMismatch else "; ".join(other))
    if differs:
        rules = env.context.get("condition_rules") or {}
        parts.append("; ".join(
            f"{', '.join(rules[t])} differs (rule {t})" if t in rules else f"condition rule {t} not met"
            for t in differs))
    if unstated:
        parts.append("not stated: " + ", ".join(unstated))
    label = f"Comparison refused, {r['claim_a_id']} vs {r['claim_b_id']}: " + "; ".join(parts)
    return Built(S.REFUSAL, g, me, True, _short(label))


def _claim_card(env: Envelope) -> Built:
    c = env.record
    q = c.get("quantity")
    _need(isinstance(q, dict), "claim_card_without_quantity")
    _need(q.get("uncertainty") is None,
          "stated_uncertainty_not_supported_by_claim_card_template_v0")
    me = _iri(env.receipt_url, "source.receipt_url")
    doc = _iri(env.context.get("source_document_url"), "context.source_document_url")
    g = Graph()
    g.add((me, RDF.type, CV.ClaimCard))
    g.add((me, DCT.identifier, _lit(c["claim_id"])))
    g.add((me, CV.sourceSentence, _lit(c["source_sentence"])))
    g.add((me, DCT.source, doc))
    g.add((me, CV.subjectName, _lit(c["subject"])))
    if c.get("object"):
        g.add((me, CV.objectName, _lit(c["object"])))
    if c.get("relation"):
        g.add((me, CV.relation, _lit(c["relation"])))
    g.add((me, CV.claimKind, _lit(c["claim_kind"])))
    g.add((me, CV.axis, _lit(c["axis"])))
    qn = SUB["quantity"]
    g.add((me, CV.hasQuantity, qn))
    g.add((qn, RDF.type, SCHEMA.QuantitativeValue))
    g.add((qn, SCHEMA.value, _dec(q.get("value"))))
    g.add((qn, SCHEMA.unitText, _lit(q.get("unit"))))
    g.add((qn, CV.bound, _lit(q.get("bound"))))
    conds = c.get("conditions") or {}
    _need(isinstance(conds, dict), "conditions_not_object")
    i = 0
    for name in sorted(conds):
        val = conds[name]
        if val == "unstated":
            g.add((me, CV.conditionUnstated, _lit(name)))
            continue
        node = _local("condition", i)
        i += 1
        g.add((me, CV.hasCondition, node))
        g.add((node, CV.conditionName, _lit(name)))
        g.add((node, CV.conditionValueJson, Literal(json.dumps(val, sort_keys=True))))
    if c.get("measurability"):
        g.add((me, CV.measurability, _lit(c["measurability"])))
    if c.get("measurable_with"):
        g.add((me, CV.measurableWith, _lit(c["measurable_with"])))
    bound = "" if q.get("bound") == "exact" else f" (bound: {q.get('bound')})"
    label = (f"Claim card {c['claim_id']}: {c['subject']}, {c['axis']} "
             f"{q.get('value')} {q.get('unit')}{bound}")
    return Built(S.CLAIM_CARD, g, me, False, _short(label))


def _correspondence(env: Envelope) -> Built:
    r = env.record
    _need(r.get("kind") == "correspondence", f"not_a_correspondence_record: kind={r.get('kind')!r}")
    a, b = _pair_claims(env)
    g = Graph()
    me = SUB["correspondence"]
    g.add((me, RDF.type, CV.GradedCorrespondence))
    g.add((me, DCT.identifier, _lit(r["pair_id"])))
    g.add((me, CV.claimA, a))
    g.add((me, CV.claimB, b))
    g.add((me, CV.grade, _int(r.get("rung"))))
    if r.get("ceiling"):
        g.add((me, CV.gradeCeiling, _lit(r["ceiling"])))
    if r.get("equivocation"):
        g.add((me, CV.equivocation, _lit(r["equivocation"])))
    if r.get("claim_a_sentence"):
        g.add((me, CV.claimASentence, _lit(r["claim_a_sentence"])))
    if r.get("claim_b_sentence"):
        g.add((me, CV.claimBSentence, _lit(r["claim_b_sentence"])))
    label = f"Claim {r['claim_a_id']} corresponds to claim {r['claim_b_id']} at grade {r['rung']}"
    return Built(S.CORRESPONDENCE, g, me, True, _short(label))


def _disagreement(env: Envelope) -> Built:
    r = env.record
    _need(r.get("kind") == "fork", f"not_a_fork_record: kind={r.get('kind')!r}")
    t = _TESTABILITY.get(env.context.get("testability"))
    _need(t is not None, f"unsupported_testability: {env.context.get('testability')!r}")
    a, b = _pair_claims(env)
    g = Graph()
    me = SUB["disagreement"]
    g.add((me, RDF.type, CV.TestableDisagreement))
    g.add((me, DCT.identifier, _lit(r["pair_id"])))
    g.add((me, CV.claimA, a))
    g.add((me, CV.claimB, b))
    g.add((me, CV.axis, _lit(r.get("axis"))))
    g.add((me, CV.testability, t))
    g.add((me, CV.instrument, _lit(env.context.get("instrument"))))
    if env.context.get("assumption"):
        g.add((me, CV.assumption, _lit(env.context["assumption"])))
    if r.get("margin") is not None:
        g.add((me, CV.margin, _dec(r["margin"])))
    if r.get("floor_applied") is not None:
        g.add((me, CV.floor, _dec(r["floor_applied"])))
    if r.get("canonical_unit"):
        g.add((me, CV.canonicalUnit, _lit(r["canonical_unit"])))
    label = (f"Disagreement {r['claim_a_id']} vs {r['claim_b_id']} is testable with "
             f"{env.context.get('instrument')}")
    return Built(S.DISAGREEMENT, g, me, True, _short(label))


def _data_quality(env: Envelope) -> Built:
    r = env.record
    _need(r.get("kind") == "data_quality_finding", f"not_a_finding_record: kind={r.get('kind')!r}")
    n_checked, n_flagged = r.get("n_checked"), r.get("n_flagged")
    _need(isinstance(n_checked, int) and isinstance(n_flagged, int) and 0 <= n_flagged <= n_checked,
          "flagged_count_must_be_between_0_and_checked_count")
    g = Graph()
    me = SUB["finding"]
    g.add((me, RDF.type, CV.DataQualityFinding))
    g.add((me, DCT.identifier, _lit(r["finding_id"])))
    g.add((me, CV.dataset, _iri(r.get("dataset"), "record.dataset")))
    g.add((me, CV.check, _lit(r.get("check"))))
    g.add((me, CV.recordsChecked, _int(n_checked)))
    g.add((me, CV.recordsFlagged, _int(n_flagged)))
    g.add((me, DCT.description, _lit(r.get("finding"))))
    label = f"Data-quality finding {r['finding_id']}: {n_flagged} of {n_checked} records flagged"
    return Built(S.DATA_QUALITY, g, me, True, _short(label))


_BUILDERS = {
    "comparison_refusal": _refusal,
    "claim_card": _claim_card,
    "graded_correspondence": _correspondence,
    "testable_disagreement": _disagreement,
    "data_quality_finding": _data_quality,
}


def build_assertion(env: Envelope) -> Built:
    """Verify the receipt, then map the record to its assertion graph."""
    try:
        verify(env)
    except ReceiptError as exc:
        raise ExportError(f"receipt_does_not_verify: {exc}") from None
    return _BUILDERS[env.record_type](env)


# ---------------------------------------------------------------------------------------
# Provenance and publication info

def build_provenance(env: Envelope, agent_iri: URIRef) -> Graph:
    r = env.record
    g = Graph()
    a = SUB["assertion"]
    g.add((a, PROV.wasAttributedTo, agent_iri))
    g.add((a, PROV.wasDerivedFrom, _iri(env.receipt_url, "source.receipt_url")))
    g.add((a, CV.sourceRepository, _iri(env.source["repository"], "source.repository")))
    g.add((a, CV.sourceCommit, _lit(env.source["commit"])))
    g.add((a, CV.contentHash, _lit(env.content_hash)))
    g.add((a, CV.hashMethod, _lit(env.receipt["hash_method"])))
    code = r.get("code_version") or env.context.get("code_version")
    rules = r.get("rules_version") or env.context.get("rules_version")
    amap = r.get("map_version") or env.context.get("map_version")
    if code:
        g.add((a, CV.codeVersion, _lit(code)))
    if rules:
        g.add((a, CV.rulesVersion, _lit(rules)))
    if amap:
        g.add((a, CV.mapVersion, _lit(amap)))
    if env.context.get("ledger_hash"):
        g.add((a, CV.ledgerHash, _lit(env.context["ledger_hash"])))
    g.add((a, CV.exportedWith, Literal(EXPORTER)))
    return g


def _created(created: str | None) -> Literal:
    if created is None:
        created = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return Literal(created, datatype=XSD.dateTime)


def _common_pubinfo(g: Graph, agent_iri: URIRef, label: str, created: str | None) -> None:
    g.add((THIS, DCT.created, _created(created)))
    g.add((THIS, DCT.creator, agent_iri))
    g.add((THIS, DCT.license, CC_BY_4))
    g.add((THIS, RDFS.label, Literal(label)))


def build_pubinfo(built: Built, agent_iri: URIRef, templates: dict, created: str | None) -> Graph:
    g = Graph()
    _common_pubinfo(g, agent_iri, built.label, created)
    g.add((THIS, NPX.hasNanopubType, built.spec.target_type))
    if built.introduced:
        g.add((THIS, NPX.introduces, built.main))
    tmpl = templates.get(built.spec.key)
    prov_tmpl = templates.get(S.RECEIPT_PROVENANCE.key)
    _need(tmpl, f"template_not_published: {built.spec.key} (publish templates first)")
    _need(prov_tmpl, "template_not_published: receipt_provenance (publish templates first)")
    g.add((THIS, NT.wasCreatedFromTemplate, URIRef(tmpl)))
    g.add((THIS, NT.wasCreatedFromProvenanceTemplate, URIRef(prov_tmpl)))
    g.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_LICENSE))
    g.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_CREATOR))
    return g


# ---------------------------------------------------------------------------------------
# Whole nanopubs (unsigned, temp namespace)

def assemble(assertion: Graph, provenance: Graph, pubinfo: Graph) -> Dataset:
    ds = Dataset()
    for prefix, ns in (("this", str(SUB)), ("sub", str(SUB)), ("np", str(NP)), ("npx", str(NPX)),
                       ("nt", str(NT)), ("cv", str(CV)), ("dct", str(DCT)), ("prov", str(PROV)),
                       ("rdfs", str(RDFS)), ("xsd", str(XSD)), ("schema", str(SCHEMA)),
                       ("foaf", str(FOAF)), ("frbr", str(FRBR))):
        ds.bind(prefix, ns, override=True, replace=True)
    head = ds.graph(SUB["Head"])
    head.add((THIS, RDF.type, NP.Nanopublication))
    head.add((THIS, NP.hasAssertion, SUB["assertion"]))
    head.add((THIS, NP.hasProvenance, SUB["provenance"]))
    head.add((THIS, NP.hasPublicationInfo, SUB["pubinfo"]))
    for name, g in (("assertion", assertion), ("provenance", provenance), ("pubinfo", pubinfo)):
        target = ds.graph(SUB[name])
        for t in g:
            target.add(t)
    return ds


def record_nanopub(env: Envelope, agent_iri: str, templates: dict, created: str | None = None) -> Dataset:
    built = build_assertion(env)
    agent = URIRef(agent_iri)
    return assemble(built.assertion, build_provenance(env, agent),
                    build_pubinfo(built, agent, templates, created))


def template_nanopub(spec: S.TemplateSpec, agent_iri: str, created: str | None = None) -> Dataset:
    agent = URIRef(agent_iri)
    prov = Graph()
    prov.add((SUB["assertion"], PROV.wasAttributedTo, agent))
    pub = Graph()
    _common_pubinfo(pub, agent, spec.label, created)
    pub.add((THIS, NPX.embeds, SUB["templateVersion"]))
    meta = META_ASSERTION_TEMPLATE if spec.kind == "assertion" else META_PROVENANCE_TEMPLATE
    pub.add((THIS, NT.wasCreatedFromTemplate, meta))
    pub.add((THIS, NT.wasCreatedFromProvenanceTemplate, PROV_TEMPLATE_ATTRIBUTED))
    pub.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_LICENSE))
    pub.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_CREATOR))
    return assemble(S.template_assertion_graph(spec), prov, pub)


def introduction_nanopub(name: str, local_name: str, public_key: str, responsible_name: str,
                         responsible_orcid: str | None, created: str | None = None) -> Dataset:
    """Self-signed introduction of the engine as a software agent (sign with
    signer = the temp sub-IRI of the agent, see ``sign``)."""
    agent = SUB[local_name]
    decl = SUB["decl"]
    owner = URIRef(f"https://orcid.org/{responsible_orcid}") if responsible_orcid \
        else SUB["responsible-person"]
    a = Graph()
    a.add((agent, RDF.type, NPX.SoftwareAgent))
    a.add((agent, RDF.type, NPX.SoftwareTool))
    a.add((agent, FOAF.name, Literal(name)))
    a.add((agent, FRBR.owner, owner))
    a.add((decl, NPX.declaredBy, agent))
    a.add((decl, NPX.hasAlgorithm, Literal("RSA")))
    a.add((decl, NPX.hasPublicKey, Literal(public_key)))
    prov = Graph()
    prov.add((SUB["assertion"], PROV.wasAttributedTo, agent))
    pub = Graph()
    _common_pubinfo(pub, agent, name, created)
    pub.add((THIS, NPX.hasNanopubType, NPX.declaredBy))
    pub.add((THIS, NPX.introduces, agent))
    pub.add((owner, FOAF.name, Literal(responsible_name)))
    pub.add((THIS, NT.wasCreatedFromTemplate, AGENT_INTRO_TEMPLATE))
    pub.add((THIS, NT.wasCreatedFromProvenanceTemplate, PROV_TEMPLATE_ATTRIBUTED))
    pub.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_LICENSE))
    pub.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_CREATOR))
    return assemble(a, prov, pub)


# ---------------------------------------------------------------------------------------
# Serialise, sign, verify, publish

def to_trig(ds: Dataset) -> str:
    return ds.serialize(format="trig")


def sign(ds: Dataset, profile) -> tuple[str, str]:
    """Sign with the nanopub package. Returns (nanopub URI, signed TriG)."""
    from nanopub import Nanopub, NanopubConf

    conf = NanopubConf(profile=profile, use_test_server=True,
                       add_pubinfo_generated_time=False, add_prov_generated_time=False)
    np_ = Nanopub(rdf=ds, conf=conf)
    np_.sign()
    signed = np_.rdf
    signed.bind("this", np_.source_uri, override=True, replace=True)
    signed.bind("sub", np_.source_uri + "/", override=True, replace=True)
    return np_.source_uri, signed.serialize(format="trig")


def check_signed(trig: str) -> str:
    """Parse signed TriG and check its trusty URI and signature. Returns the URI."""
    from nanopub import Nanopub, NanopubConf

    ds = Dataset()
    ds.parse(data=trig, format="trig")
    np_ = Nanopub(rdf=ds, conf=NanopubConf(use_test_server=True))
    if not (np_.has_valid_trusty and np_.has_valid_signature):
        raise ExportError(f"signed_nanopub_does_not_verify: {np_.source_uri}")
    return np_.source_uri


def artifact_code(uri: str) -> str:
    code = uri.rstrip("/").rsplit("/", 1)[-1]
    _need(code.startswith("RA") and len(code) == 45, f"not_a_trusty_uri: {uri}")
    return code


def test_server_url(uri: str) -> str:
    return TEST_REGISTRY_URL + artifact_code(uri)


def publish_to_test_server(signed_trig: str, timeout: float = 60) -> str:
    """POST a signed nanopub to the Knowledge Pixels TEST registry. Returns its URI.

    There is no production path in this module, on purpose.
    """
    uri = check_signed(signed_trig)
    url = TEST_REGISTRY_URL
    _need(url.startswith("https://test.registry.knowledgepixels.com/"), "refusing_non_test_registry")
    r = requests.post(url, data=signed_trig.encode("utf-8"),
                      headers={"Content-Type": "application/trig"}, timeout=timeout)
    if r.status_code >= 300:
        raise ExportError(f"test_registry_rejected: HTTP {r.status_code}: {r.text[:300]}")
    return uri


def fetch_from_test_server(uri: str, timeout: float = 60) -> str:
    r = requests.get(test_server_url(uri), headers={"Accept": "application/trig"}, timeout=timeout)
    if r.status_code != 200:
        raise ExportError(f"not_resolvable_on_test_server: HTTP {r.status_code}: {uri}")
    return r.text
