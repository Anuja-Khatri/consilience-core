"""Template specifications.

Each record type has one specification. The same specification is used twice:

1. to write the nanopublication *template* (Knowledge Pixels / Nanodash template
   format, ``nt:AssertionTemplate`` or ``nt:ProvenanceTemplate``), and
2. by the tests, to check that every exported nanopublication matches its template
   statement by statement.

So the exporter and the published templates cannot drift apart silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rdflib import Graph, Literal, Namespace, URIRef

from .vocab import (
    CV, DCT, LABELS, NT, PROV, RDF, RDFS, SCHEMA, XSD,
)

TEMP_NS = Namespace("http://purl.org/nanopub/temp/np/")
ASSERTION = NT.ASSERTION  # stands for "this nanopub's assertion graph" in provenance templates


@dataclass(frozen=True)
class PH:
    """A template placeholder."""
    name: str
    kinds: tuple[str, ...]          # ntemplate class local names, e.g. ("LiteralPlaceholder",)
    label: str
    values: tuple[URIRef, ...] = ()  # for RestrictedChoicePlaceholder
    datatype: URIRef | None = None
    default: URIRef | None = None

    @property
    def iri(self) -> URIRef:
        return TEMP_NS[self.name]

    @property
    def is_local(self) -> bool:
        return "LocalResource" in self.kinds

    @property
    def is_literal(self) -> bool:
        return any(k in self.kinds for k in ("LiteralPlaceholder", "LongLiteralPlaceholder"))


Term = "PH | URIRef"


@dataclass(frozen=True)
class St:
    id: str
    s: object
    p: URIRef
    o: object
    optional: bool = False
    repeatable: bool = False


@dataclass(frozen=True)
class Group:
    id: str
    members: tuple[str, ...]
    optional: bool = False
    repeatable: bool = False


@dataclass(frozen=True)
class TemplateSpec:
    key: str
    kind: str                    # "assertion" | "provenance"
    label: str
    description: str
    statements: tuple[St, ...]
    groups: tuple[Group, ...] = ()
    label_pattern: str | None = None
    target_type: URIRef | None = None
    tags: tuple[str, ...] = ("Consilience",)

    def statement(self, sid: str) -> St:
        return next(s for s in self.statements if s.id == sid)

    def top_level_ids(self) -> list[str]:
        grouped = {m for g in self.groups for m in g.members}
        return [s.id for s in self.statements if s.id not in grouped] + [g.id for g in self.groups]


# ---------------------------------------------------------------------------------------
# Placeholders shared across templates

def _local(name, label):
    return PH(name, ("IntroducedResource", "LocalResource"), label)


def _lit(name, label, datatype=None):
    return PH(name, ("LiteralPlaceholder",), label, datatype=datatype)


def _long(name, label):
    return PH(name, ("LongLiteralPlaceholder",), label)


def _ext(name, label):
    return PH(name, ("ExternalUriPlaceholder",), label)


CLAIM_A = _ext("claimA", "claim A (link to its claim card)")
CLAIM_B = _ext("claimB", "claim B (link to its claim card)")
IDENT = _lit("identifier", "identifier of the record in its source repository")
AXIS = _lit("axis", "quantity axis")
SENT_A = _long("sentenceA", "source sentence of claim A")
SENT_B = _long("sentenceB", "source sentence of claim B")

DEFECT_TYPES = (CV.ConditionUnstated, CV.ConditionMismatch, CV.AxisMismatch,
                CV.TypeMismatch, CV.QuantityRefused)
OUTCOMES = (CV.NotComparable, CV.AxisMismatch)
TESTABILITY = (CV.TestableNow, CV.TestableUnderAssumption, CV.NotTestable)

# ---------------------------------------------------------------------------------------
# (b) comparison refused

_REF = _local("refusal", "this refusal")
_DEFECT = PH("defect", ("LocalResource",), "a defect")
REFUSAL = TemplateSpec(
    key="comparison_refusal",
    kind="assertion",
    label="Consilience: comparison refused",
    description=(
        "A comparison between two claims that was refused, with the reason named. "
        "Two claims are compared only if they are on the same quantity axis and every "
        "condition the rule set requires is stated for both and matches. Otherwise the "
        "comparison is refused, and each defect is recorded: a condition that is not "
        "stated in a claim card, a condition that differs between the two, or different "
        "quantity axes. A refusal is a statement about what the two claim cards, as "
        "recorded, allow; it is not a judgement of either source. The rule set, code "
        "version and content hash of the original verdict are in the provenance."
    ),
    statements=(
        St("st01", _REF, RDF.type, CV.ComparisonRefusal),
        St("st02", _REF, DCT.identifier, IDENT),
        St("st03", _REF, CV.claimA, CLAIM_A),
        St("st04", _REF, CV.claimB, CLAIM_B),
        St("st05", _REF, CV.axis, AXIS, optional=True),
        St("st06", _REF, CV.outcome, PH("outcome", ("RestrictedChoicePlaceholder",),
                                        "outcome", values=OUTCOMES)),
        St("st07", _REF, CV.hasDefect, _DEFECT),
        St("st08", _DEFECT, CV.defectType, PH("defectType", ("RestrictedChoicePlaceholder",),
                                               "defect type", values=DEFECT_TYPES)),
        St("st09", _DEFECT, CV.defectTarget, _lit("defectTarget",
                                                   "condition, rule or axes concerned")),
        St("st10", _REF, CV.claimASentence, SENT_A, optional=True),
        St("st11", _REF, CV.claimBSentence, SENT_B, optional=True),
    ),
    groups=(Group("st20", ("st07", "st08", "st09"), repeatable=True),),
    label_pattern="Comparison refused: ${identifier}",
    target_type=CV.ComparisonRefusal,
)

# ---------------------------------------------------------------------------------------
# claim card (needed so the pilot's claim cards have a template too)

_CLAIM = _ext("claim", "the claim card (its location in the source repository)")
_QTY = PH("quantity", ("LocalResource",), "the stated quantity")
_COND = PH("condition", ("LocalResource",), "a stated condition")
CLAIM_CARD = TemplateSpec(
    key="claim_card",
    kind="assertion",
    label="Consilience: claim card",
    description=(
        "One measured claim as an approved Consilience claim card: the exact source "
        "sentence, the source document, the subject, the quantity on its axis with its "
        "unit, the conditions the sentence states and the conditions it does not state. "
        "Comparisons between claims are made only from these cards."
    ),
    statements=(
        St("st01", _CLAIM, RDF.type, CV.ClaimCard),
        St("st02", _CLAIM, DCT.identifier, _lit("claimId", "claim identifier in the source repository")),
        St("st03", _CLAIM, CV.sourceSentence, _long("sentence", "exact source sentence")),
        St("st04", _CLAIM, DCT.source, _ext("document", "source document")),
        St("st05", _CLAIM, CV.subjectName, _lit("subjectName", "subject (e.g. the material)")),
        St("st06", _CLAIM, CV.objectName, _lit("objectName", "what is measured"), optional=True),
        St("st07", _CLAIM, CV.relation, _lit("relation", "relation"), optional=True),
        St("st08", _CLAIM, CV.claimKind, _lit("claimKind", "claim kind")),
        St("st09", _CLAIM, CV.axis, AXIS),
        St("st10", _CLAIM, CV.hasQuantity, _QTY),
        St("st11", _QTY, RDF.type, SCHEMA.QuantitativeValue),
        St("st12", _QTY, SCHEMA.value, _lit("value", "numeric value", XSD.decimal)),
        St("st13", _QTY, SCHEMA.unitText, _lit("unit", "unit as written")),
        St("st14", _QTY, CV.bound, _lit("bound", "bound (exact, approx, lower, upper)")),
        St("st15", _CLAIM, CV.hasCondition, _COND),
        St("st16", _COND, CV.conditionName, _lit("conditionName", "condition name")),
        St("st17", _COND, CV.conditionValueJson, _lit("conditionValue", "condition value as JSON")),
        St("st18", _CLAIM, CV.conditionUnstated, _lit("unstatedCondition", "condition not stated"),
           optional=True, repeatable=True),
        St("st19", _CLAIM, CV.measurability, _lit("measurability", "measurability"), optional=True),
        St("st21", _CLAIM, CV.measurableWith, _lit("instrumentId", "instrument class"), optional=True),
    ),
    groups=(
        Group("st30", ("st10", "st11", "st12", "st13", "st14")),
        Group("st31", ("st15", "st16", "st17"), optional=True, repeatable=True),
    ),
    label_pattern="Claim card ${claimId}",
    target_type=CV.ClaimCard,
)

# ---------------------------------------------------------------------------------------
# theory claim card (claims of scientific theories, which state no measured quantity)

_TCLAIM = _ext("claim", "the claim card (its location in the source repository)")
_LOCATION = PH("location", ("LocalResource",), "a source location")
THEORY_CLAIM_CARD = TemplateSpec(
    key="theory_claim_card",
    kind="assertion",
    label="Consilience: theory claim card",
    description=(
        "One claim of a scientific theory as a reviewed Consilience claim card: the "
        "theory, the claim statement, the axis it is on and the value it takes there, "
        "and the source locations it rests on (document and page). The statement is a "
        "paraphrase of the source that a person has reviewed; it is not a quotation. A "
        "page is the page of the PDF that was read, which can differ from the printed "
        "page number."
    ),
    statements=(
        St("st01", _TCLAIM, RDF.type, CV.TheoryClaimCard),
        St("st02", _TCLAIM, DCT.identifier, _lit("claimId", "claim identifier in the source repository")),
        St("st03", _TCLAIM, CV.theory, _lit("theory", "theory")),
        St("st04", _TCLAIM, CV.claimStatement,
           _long("statement", "claim statement (a reviewed paraphrase, not a quotation)")),
        St("st05", _TCLAIM, CV.statementForm, CV.ReviewedParaphrase),
        St("st06", _TCLAIM, CV.axis, _lit("axis", "axis of the commitment")),
        St("st07", _TCLAIM, RDF.value, _lit("value", "value on that axis")),
        St("st08", _TCLAIM, CV.polarity, _lit("polarity", "polarity (asserts or denies)"),
           optional=True),
        St("st09", _TCLAIM, CV.restsOn, _LOCATION),
        St("st10", _LOCATION, DCT.source, _ext("document", "source document")),
        St("st11", _LOCATION, CV.pageLocator, _lit("page", "page in the PDF read (e.g. p.4)")),
    ),
    groups=(Group("st20", ("st09", "st10", "st11"), optional=True, repeatable=True),),
    label_pattern="Theory claim card ${claimId}",
    target_type=CV.TheoryClaimCard,
)

# ---------------------------------------------------------------------------------------
# (a) graded correspondence

_CORR = _local("correspondence", "this correspondence")
CORRESPONDENCE = TemplateSpec(
    key="graded_correspondence",
    kind="assertion",
    label="Consilience: claim A corresponds to claim B at grade X",
    description=(
        "Two claims were compared by structure and judged to correspond at a grade on a "
        "four-rung ladder, from rung 1 (structural identity) to rung 4 (thematic "
        "resonance only). The ceiling says what that grade does not license. The "
        "equivocation check records whether the correspondence survives removing the "
        "vocabulary the two claims share."
    ),
    statements=(
        St("st01", _CORR, RDF.type, CV.GradedCorrespondence),
        St("st02", _CORR, DCT.identifier, IDENT),
        St("st03", _CORR, CV.claimA, CLAIM_A),
        St("st04", _CORR, CV.claimB, CLAIM_B),
        St("st05", _CORR, CV.grade, _lit("grade", "grade: rung 1 (strongest) to 4 (weakest)", XSD.integer)),
        St("st06", _CORR, CV.gradeCeiling, _long("ceiling", "what this grade does not license"),
           optional=True),
        St("st07", _CORR, CV.equivocation, _lit("equivocation", "equivocation-check result"),
           optional=True),
        St("st08", _CORR, CV.claimASentence, SENT_A, optional=True),
        St("st09", _CORR, CV.claimBSentence, SENT_B, optional=True),
    ),
    label_pattern="Correspondence at grade ${grade}: ${identifier}",
    target_type=CV.GradedCorrespondence,
)

# ---------------------------------------------------------------------------------------
# (c) testable disagreement

_DIS = _local("disagreement", "this disagreement")
DISAGREEMENT = TemplateSpec(
    key="testable_disagreement",
    kind="assertion",
    label="Consilience: this disagreement is testable now with instrument Y",
    description=(
        "Two comparable claims disagree beyond the floor that applies on their axis, "
        "and the disagreement can be tested with an instrument that exists today (or "
        "under a named assumption, or not at all, with the reason). The margin and the "
        "floor are given in the canonical unit of the axis."
    ),
    statements=(
        St("st01", _DIS, RDF.type, CV.TestableDisagreement),
        St("st02", _DIS, DCT.identifier, IDENT),
        St("st03", _DIS, CV.claimA, CLAIM_A),
        St("st04", _DIS, CV.claimB, CLAIM_B),
        St("st05", _DIS, CV.axis, AXIS),
        St("st06", _DIS, CV.testability, PH("testability", ("RestrictedChoicePlaceholder",),
                                             "testability", values=TESTABILITY)),
        St("st07", _DIS, CV.instrument, _lit("instrument", "instrument (class or name)")),
        St("st08", _DIS, CV.assumption, _long("assumption", "assumption needed"), optional=True),
        St("st09", _DIS, CV.margin, _lit("margin", "margin", XSD.decimal), optional=True),
        St("st10", _DIS, CV.floor, _lit("floor", "floor applied", XSD.decimal), optional=True),
        St("st11", _DIS, CV.canonicalUnit, _lit("canonicalUnit", "canonical unit"), optional=True),
    ),
    label_pattern="Testable disagreement: ${identifier}",
    target_type=CV.TestableDisagreement,
)

# ---------------------------------------------------------------------------------------
# (d) data-quality finding

_FIND = _local("finding", "this finding")
DATA_QUALITY = TemplateSpec(
    key="data_quality_finding",
    kind="assertion",
    label="Consilience: data-quality finding",
    description=(
        "A check run over a dataset, and how many records it flagged out of how many "
        "it checked. A finding is an observation about individual records, made "
        "possible by what the dataset records; it credits the dataset and is not a "
        "statement about the people who produced it. Findings are shared with the "
        "dataset's maintainers before they are published."
    ),
    statements=(
        St("st01", _FIND, RDF.type, CV.DataQualityFinding),
        St("st02", _FIND, DCT.identifier, _lit("identifier", "identifier of the finding")),
        St("st03", _FIND, CV.dataset, _ext("dataset", "dataset (persistent link)")),
        St("st04", _FIND, CV.check, _long("check", "the check, in plain words")),
        St("st05", _FIND, CV.recordsChecked, _lit("recordsChecked", "records checked", XSD.integer)),
        St("st06", _FIND, CV.recordsFlagged, _lit("recordsFlagged", "records flagged", XSD.integer)),
        St("st07", _FIND, DCT.description, _long("findingText", "the finding, in plain words")),
    ),
    label_pattern="Data-quality finding: ${identifier}",
    target_type=CV.DataQualityFinding,
)

# ---------------------------------------------------------------------------------------
# provenance: the receipt

RECEIPT_PROVENANCE = TemplateSpec(
    key="receipt_provenance",
    kind="provenance",
    label="Consilience: receipt",
    description=(
        "Where a Consilience record comes from and how to check it: the receipt (the "
        "record at a pinned commit of a public repository), the content hash and the "
        "method that reproduces it, and the code, rule and map versions that produced "
        "the record."
    ),
    statements=(
        St("st01", ASSERTION, PROV.wasAttributedTo,
           PH("agent", ("AgentPlaceholder", "ExternalUriPlaceholder"), "software agent",
              default=NT.CREATOR)),
        St("st02", ASSERTION, PROV.wasDerivedFrom, _ext("receipt", "receipt (record at a pinned commit)")),
        St("st03", ASSERTION, CV.sourceRepository, _ext("repository", "source repository")),
        St("st04", ASSERTION, CV.sourceCommit, _lit("commit", "source commit")),
        St("st05", ASSERTION, CV.contentHash, _lit("contentHash", "content hash (SHA-256)")),
        St("st06", ASSERTION, CV.hashMethod, _lit("hashMethod", "hash method")),
        St("st07", ASSERTION, CV.codeVersion, _lit("codeVersion", "code version"), optional=True),
        St("st08", ASSERTION, CV.rulesVersion, _lit("rulesVersion", "rule version"), optional=True),
        St("st09", ASSERTION, CV.mapVersion, _lit("mapVersion", "axis map version"), optional=True),
        St("st10", ASSERTION, CV.ledgerHash, _lit("ledgerHash", "ledger hash"), optional=True),
        St("st11", ASSERTION, CV.exportedWith, _lit("exporter", "exporter and version")),
    ),
)

ASSERTION_SPECS = {s.key: s for s in (CORRESPONDENCE, REFUSAL, DISAGREEMENT, DATA_QUALITY, CLAIM_CARD,
                                        THEORY_CLAIM_CARD)}
ALL_SPECS = {**ASSERTION_SPECS, RECEIPT_PROVENANCE.key: RECEIPT_PROVENANCE}


# ---------------------------------------------------------------------------------------
# Template graph

def _term(x):
    return x.iri if isinstance(x, PH) else x


def template_assertion_graph(spec: TemplateSpec) -> Graph:
    """The assertion graph of the template nanopub (temp namespace)."""
    g = Graph()
    sub = TEMP_NS
    node = sub["templateVersion"]
    ttype = NT.AssertionTemplate if spec.kind == "assertion" else NT.ProvenanceTemplate
    g.add((node, RDF.type, ttype))
    g.add((node, RDFS.label, Literal(spec.label)))
    g.add((node, DCT.description, Literal(spec.description)))
    for t in spec.tags:
        g.add((node, NT.hasTag, Literal(t)))
    if spec.label_pattern:
        g.add((node, NT.hasNanopubLabelPattern, Literal(spec.label_pattern)))
    if spec.target_type is not None:
        g.add((node, NT.hasTargetNanopubType, spec.target_type))

    grouped = {m for gr in spec.groups for m in gr.members}
    # List every statement on the template node, grouped members included.
    for st in spec.statements:
        g.add((node, NT.hasStatement, sub[st.id]))
    for gr in spec.groups:
        g.add((node, NT.hasStatement, sub[gr.id]))
        g.add((sub[gr.id], RDF.type, NT.GroupedStatement))
        if gr.optional:
            g.add((sub[gr.id], RDF.type, NT.OptionalStatement))
        if gr.repeatable:
            g.add((sub[gr.id], RDF.type, NT.RepeatableStatement))
        for i, m in enumerate(gr.members):
            g.add((sub[gr.id], NT.hasStatement, sub[m]))

    placeholders: dict[str, PH] = {}
    for st in spec.statements:
        sn = sub[st.id]
        g.add((sn, RDF.subject, _term(st.s)))
        g.add((sn, RDF.predicate, st.p))
        g.add((sn, RDF.object, _term(st.o)))
        if st.id not in grouped:
            if st.optional:
                g.add((sn, RDF.type, NT.OptionalStatement))
            if st.repeatable:
                g.add((sn, RDF.type, NT.RepeatableStatement))
        for t in (st.s, st.o):
            if isinstance(t, PH):
                placeholders[t.name] = t
    for ph in placeholders.values():
        for k in ph.kinds:
            g.add((ph.iri, RDF.type, NT[k]))
        g.add((ph.iri, RDFS.label, Literal(ph.label)))
        for v in ph.values:
            g.add((ph.iri, NT.possibleValue, v))
        if ph.datatype is not None:
            g.add((ph.iri, NT.hasDatatype, ph.datatype))
        if ph.default is not None:
            g.add((ph.iri, NT.hasDefaultValue, ph.default))

    # Labels for predicates and fixed values, so forms render readably.
    used = set()
    for st in spec.statements:
        used.add(st.p)
        if isinstance(st.o, URIRef):
            used.add(st.o)
    for ph in placeholders.values():
        used.update(ph.values)
    for iri in sorted(used):
        if iri in LABELS:
            g.add((iri, RDFS.label, Literal(LABELS[iri])))
    return g


# ---------------------------------------------------------------------------------------
# Conformance: does an exported assertion (or provenance) graph match its template?

_REPEAT = re.compile(r"^(?P<base>.+?)(__\d+)?$")


@dataclass
class Conformance:
    unmatched: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    bad_values: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.unmatched or self.missing or self.bad_values)


def _matches(term, slot, ns: str, assertion_iri) -> bool:
    if isinstance(slot, URIRef):
        if slot == ASSERTION:
            return term == assertion_iri
        return term == slot
    ph: PH = slot
    if ph.is_local:
        if not isinstance(term, URIRef) or not str(term).startswith(ns):
            return False
        local = str(term)[len(ns):]
        m = _REPEAT.match(local)
        return bool(m) and m.group("base") == ph.name
    if ph.is_literal:
        if not isinstance(term, Literal):
            return False
        if ph.datatype is not None:
            return term.datatype == ph.datatype
        return True
    if "RestrictedChoicePlaceholder" in ph.kinds:
        return term in ph.values
    return isinstance(term, URIRef)  # External / Agent placeholder


def check_conformance(spec: TemplateSpec, graph: Graph, np_namespace: str, assertion_iri) -> Conformance:
    """Match each triple of ``graph`` against the spec's statements.

    ``np_namespace`` is the namespace local resources live in (the temp namespace for
    unsigned output, ``https://w3id.org/np/RA…/`` once signed).
    """
    res = Conformance()
    hits: dict[str, int] = {s.id: 0 for s in spec.statements}
    for s, p, o in graph:
        found = None
        for st in spec.statements:
            if st.p == p and _matches(s, st.s, np_namespace, assertion_iri) \
                    and _matches(o, st.o, np_namespace, assertion_iri):
                found = st
                break
        if found is None:
            if p == RDFS.label and isinstance(o, Literal):
                continue  # labels on resources are always allowed
            res.unmatched.append((s, p, o))
        else:
            hits[found.id] += 1
    grouped = {m: gr for gr in spec.groups for m in gr.members}
    for st in spec.statements:
        gr = grouped.get(st.id)
        optional = st.optional or (gr is not None and gr.optional)
        if gr is not None and gr.optional:
            # an optional group is either absent or complete
            if any(hits[m] for m in gr.members) and not hits[st.id]:
                res.missing.append(st.id)
            continue
        if not optional and hits[st.id] == 0:
            res.missing.append(st.id)
        if not (st.repeatable or (gr is not None and gr.repeatable)) and hits[st.id] > 1:
            # a non-repeatable statement may still match several triples when its
            # subject is a repeated local resource of a repeatable group; that is
            # handled by the group flag above
            res.bad_values.append((st.id, f"matched {hits[st.id]} times"))
    return res
