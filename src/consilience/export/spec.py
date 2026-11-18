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
    CV, DCT, LABELS, NT, PROV, QUDT, RDF, RDFS, XSD,
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
    """A resource the nanopub introduces: other nanopubs link to it, and a superseding
    version keeps its IRI."""
    return PH(name, ("IntroducedResource", "LocalResource"), label)


def _node(name, label):
    """A resource that belongs to this nanopub only (a value node, a defect node)."""
    return PH(name, ("LocalResource",), label)


def _lit(name, label, datatype=None):
    return PH(name, ("LiteralPlaceholder",), label, datatype=datatype)


def _long(name, label):
    return PH(name, ("LongLiteralPlaceholder",), label)


def _ext(name, label):
    return PH(name, ("ExternalUriPlaceholder",), label)


def _choice(name, label, values):
    return PH(name, ("RestrictedChoicePlaceholder",), label, values=tuple(values))


CLAIM_A = _ext("claimA", "claim A (the claim IRI its claim card introduces)")
CLAIM_B = _ext("claimB", "claim B (the claim IRI its claim card introduces)")
IDENT = _lit("identifier", "identifier of the record in its source repository")
SENT_A = _long("sentenceA", "source sentence of claim A")
SENT_B = _long("sentenceB", "source sentence of claim B")

DEFECT_TYPES = (CV.TypeMismatch, CV.QuantityRefused)
OUTCOMES = (CV.NotComparable, CV.AxisMismatch)
TESTABILITY = (CV.TestableNow, CV.TestableUnderAssumption, CV.NotYetTestable)
BOUNDS = (CV.ExactValue, CV.ApproximateValue, CV.LowerBound, CV.UpperBound)

# ---------------------------------------------------------------------------------------
# (b) comparison refused

_REF = _local("refusal", "this refusal")
_UNSTATED = _node("unstated", "a condition not stated in one claim")
_MISMATCH = _node("mismatch", "a condition that differs")
_DEFECT = _node("defect", "another defect")
REFUSAL = TemplateSpec(
    key="comparison_refusal",
    kind="assertion",
    label="Consilience: comparison refused",
    description=(
        "A comparison between two claims that was refused, with each reason named. Two "
        "claims are compared only if they are on the same quantity axis and every condition "
        "the rule set requires is stated for both and matches. Each reason is recorded with "
        "IRIs: a condition that one claim does not state (which condition, which claim, "
        "under which rule; if both claims lack it, once for each), a condition that differs "
        "(which condition, under which rule, its value in claim A and in claim B, and the "
        "unit), or the two different quantity axes. Claim A and claim B are the claim IRIs "
        "their claim-card nanopublications introduce. A refusal is a statement about what "
        "the two claims, as recorded, allow; it is not a judgement of either source. The "
        "rule set, code version and content hash of the original verdict are in the "
        "provenance."
    ),
    statements=(
        St("st01", _REF, RDF.type, CV.ComparisonRefusal),
        St("st02", _REF, DCT.identifier, IDENT),
        St("st03", _REF, CV.claimA, CLAIM_A),
        St("st04", _REF, CV.claimB, CLAIM_B),
        St("st05", _REF, CV.axis, _ext("axis", "quantity axis of both claims"), optional=True),
        St("st06", _REF, CV.outcome, _choice("outcome", "outcome", OUTCOMES)),
        # a condition not stated in one claim
        St("st10", _REF, CV.hasUnstatedCondition, _UNSTATED),
        St("st11", _UNSTATED, CV.condition, _ext("unstatedCondition", "condition not stated")),
        St("st12", _UNSTATED, CV.unstatedIn, _ext("lackingClaim", "the claim that does not state it")),
        St("st13", _UNSTATED, CV.rule, _lit("unstatedRule", "rule that requires it (e.g. CR1)")),
        # a condition that differs
        St("st20", _REF, CV.hasConditionMismatch, _MISMATCH),
        St("st21", _MISMATCH, CV.condition, _ext("differingCondition", "condition that differs")),
        St("st22", _MISMATCH, CV.rule, _lit("mismatchRule", "rule not met (e.g. CR2)")),
        St("st23", _MISMATCH, CV.valueInClaimA, _lit("valueA", "value in claim A", XSD.decimal)),
        St("st24", _MISMATCH, CV.valueInClaimB, _lit("valueB", "value in claim B", XSD.decimal)),
        St("st25", _MISMATCH, QUDT.unit, _ext("mismatchUnit", "unit of both values (QUDT or cv)")),
        # different quantity axes
        St("st30", _REF, CV.axisOfClaimA, _ext("axisA", "quantity axis of claim A")),
        St("st31", _REF, CV.axisOfClaimB, _ext("axisB", "quantity axis of claim B")),
        # another defect
        St("st40", _REF, CV.hasDefect, _DEFECT),
        St("st41", _DEFECT, CV.defectType, _choice("defectType", "defect type", DEFECT_TYPES)),
        St("st42", _DEFECT, CV.defectTarget, _lit("defectTarget", "what the defect concerns")),
        St("st50", _REF, CV.claimASentence, SENT_A, optional=True),
        St("st51", _REF, CV.claimBSentence, SENT_B, optional=True),
    ),
    groups=(
        Group("st60", ("st10", "st11", "st12", "st13"), optional=True, repeatable=True),
        Group("st61", ("st20", "st21", "st22", "st23", "st24", "st25"), optional=True, repeatable=True),
        Group("st62", ("st30", "st31"), optional=True),
        Group("st63", ("st40", "st41", "st42"), optional=True, repeatable=True),
    ),
    label_pattern="Comparison refused: ${identifier}",
    target_type=CV.ComparisonRefusal,
)

# ---------------------------------------------------------------------------------------
# measured claim (the ledger's claim cards)

_CLAIM = _local("claim", "this claim (its IRI is the claim's identity)")
_QTY = _node("quantity", "the stated quantity")
_QCOND = _node("quantityCondition", "a stated condition with a number and a unit")
_CCOND = _node("categoricalCondition", "a stated condition whose value is an IRI")
CLAIM_CARD = TemplateSpec(
    key="claim_card",
    kind="assertion",
    label="Consilience: measured claim (claim card)",
    description=(
        "One measured claim, introduced with its own IRI, which stays the same if a "
        "corrected card supersedes this one. It gives the exact source sentence, the source "
        "document, the subject, the quantity on its axis (a QUDT numeric value and unit, "
        "with the bound and the unit as written), the conditions the sentence states (each "
        "as a condition IRI with a number and unit, or with an IRI value such as a ChEBI "
        "electrolyte) and the conditions it does not state. Comparisons between claims are "
        "made only from these cards. Where the card comes from (its record at a pinned "
        "commit, and its content hash) is in the provenance."
    ),
    statements=(
        St("st01", _CLAIM, RDF.type, CV.MeasuredClaim),
        St("st02", _CLAIM, DCT.identifier, _lit("claimId", "claim identifier in the source repository")),
        St("st03", _CLAIM, CV.sourceSentence, _long("sentence", "exact source sentence")),
        St("st04", _CLAIM, DCT.source, _ext("document", "source document")),
        St("st05", _CLAIM, CV.subjectName, _lit("subjectName", "subject (e.g. the material)")),
        St("st06", _CLAIM, CV.claimKind, _ext("claimKind", "claim kind")),
        St("st07", _CLAIM, CV.axis, _ext("axis", "quantity axis")),
        St("st10", _CLAIM, CV.hasQuantity, _QTY),
        St("st11", _QTY, RDF.type, QUDT.QuantityValue),
        St("st12", _QTY, QUDT.numericValue, _lit("value", "numeric value", XSD.decimal)),
        St("st13", _QTY, QUDT.unit, _ext("unit", "unit (QUDT or cv)")),
        St("st14", _QTY, CV.bound, _choice("bound", "bound", BOUNDS)),
        St("st15", _QTY, CV.unitAsWritten, _lit("unitAsWritten", "unit as written in the source")),
        St("st20", _CLAIM, CV.statesQuantityCondition, _QCOND),
        St("st21", _QCOND, CV.condition, _ext("qCondition", "condition")),
        St("st22", _QCOND, QUDT.numericValue, _lit("qValue", "numeric value", XSD.decimal)),
        St("st23", _QCOND, QUDT.unit, _ext("qUnit", "unit (QUDT or cv)")),
        St("st30", _CLAIM, CV.statesCategoricalCondition, _CCOND),
        St("st31", _CCOND, CV.condition, _ext("cCondition", "condition")),
        St("st32", _CCOND, CV.conditionValue, _ext("cValue", "value (an IRI, e.g. a ChEBI entity)")),
        St("st40", _CLAIM, CV.conditionUnstated, _ext("unstatedCondition", "condition not stated"),
           optional=True, repeatable=True),
        St("st41", _CLAIM, CV.measurability, _ext("measurability", "measurability"), optional=True),
        St("st42", _CLAIM, CV.measurableWith, _ext("technique", "measurement technique"), optional=True),
    ),
    groups=(
        Group("st50", ("st10", "st11", "st12", "st13", "st14", "st15")),
        Group("st51", ("st20", "st21", "st22", "st23"), optional=True, repeatable=True),
        Group("st52", ("st30", "st31", "st32"), optional=True, repeatable=True),
    ),
    label_pattern="Measured claim ${claimId}",
    target_type=CV.MeasuredClaim,
)

# ---------------------------------------------------------------------------------------
# theory claim (claims of scientific theories, which state no measured quantity)

_TCLAIM = _local("claim", "this claim (its IRI is the claim's identity)")
_LOCATION = _node("location", "a source location")
THEORY_CLAIM_CARD = TemplateSpec(
    key="theory_claim_card",
    kind="assertion",
    label="Consilience: theory claim (claim card)",
    description=(
        "One claim of a scientific theory, introduced with its own IRI, which stays the same "
        "if a corrected card supersedes this one: the theory, the claim statement, the "
        "dimension of commitment it is on and the position it takes there (all IRIs), and "
        "the source locations it rests on (document and page). The statement is a "
        "paraphrase of the source that a person has reviewed; it is not a quotation. Who "
        "reviewed it, and what drafted it, are in the provenance. A page is the page of the "
        "PDF that was read, which can differ from the printed page number."
    ),
    statements=(
        St("st01", _TCLAIM, RDF.type, CV.TheoryClaim),
        St("st02", _TCLAIM, DCT.identifier, _lit("claimId", "claim identifier in the source repository")),
        St("st03", _TCLAIM, CV.theory, _ext("theory", "theory")),
        St("st04", _TCLAIM, CV.claimStatement,
           _long("statement", "claim statement (a reviewed paraphrase, not a quotation)")),
        St("st05", _TCLAIM, CV.statementForm, CV.ReviewedParaphrase),
        St("st06", _TCLAIM, CV.dimension, _ext("dimension", "dimension of commitment")),
        St("st07", _TCLAIM, CV.position, _ext("position", "position taken on that dimension")),
        St("st08", _TCLAIM, CV.polarity, _choice("polarity", "polarity", (CV.Asserts, CV.Denies)),
           optional=True),
        St("st09", _TCLAIM, CV.restsOn, _LOCATION),
        St("st10", _LOCATION, DCT.source, _ext("document", "source document")),
        St("st11", _LOCATION, CV.pageLocator, _lit("page", "page in the PDF read (e.g. p.4)")),
    ),
    groups=(Group("st20", ("st09", "st10", "st11"), optional=True, repeatable=True),),
    label_pattern="Theory claim ${claimId}",
    target_type=CV.TheoryClaim,
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
        "vocabulary the two claims share. Claim A and claim B are the claim IRIs their "
        "claim-card nanopublications introduce."
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
# (c) disagreement, with its testability (replaces v1's "testable disagreement")

_DIS = _local("disagreement", "this disagreement")
DISAGREEMENT = TemplateSpec(
    key="disagreement",
    kind="assertion",
    label="Consilience: claims A and B disagree on a dimension; testability and reason",
    description=(
        "Two claims take different values on the same dimension. The record names the "
        "dimension of disagreement, the observables the disagreement bears on and the "
        "instruments that could measure them (separate fields; either may be absent if the "
        "source names none), and a testability status: testable now, testable under a "
        "stated assumption, or not yet testable, always with the reason. For measured "
        "claims, the margin and the floor are given in one unit. Claim A and claim B are "
        "the claim IRIs their claim-card nanopublications introduce. A disagreement is a "
        "statement about two claims, not a verdict on either."
    ),
    statements=(
        St("st01", _DIS, RDF.type, CV.Disagreement),
        St("st02", _DIS, DCT.identifier, IDENT),
        St("st03", _DIS, CV.claimA, CLAIM_A),
        St("st04", _DIS, CV.claimB, CLAIM_B),
        St("st05", _DIS, CV.dimension, _ext("dimension", "dimension of disagreement")),
        St("st06", _DIS, CV.observable, _ext("observable", "observable it bears on"),
           optional=True, repeatable=True),
        St("st07", _DIS, CV.instrument, _ext("instrument", "instrument or technique that could test it"),
           optional=True, repeatable=True),
        St("st08", _DIS, CV.testability, _choice("testability", "testability", TESTABILITY)),
        St("st09", _DIS, CV.testabilityReason, _long("reason", "why (the reason for this testability)")),
        St("st10", _DIS, CV.assumption, _long("assumption", "the assumption (if testable under one)"),
           optional=True),
        St("st11", _DIS, CV.margin, _lit("margin", "margin", XSD.decimal)),
        St("st12", _DIS, CV.floor, _lit("floor", "floor applied", XSD.decimal)),
        St("st13", _DIS, QUDT.unit, _ext("unit", "unit of margin and floor")),
    ),
    groups=(Group("st20", ("st11", "st12", "st13"), optional=True),),
    label_pattern="Disagreement: ${identifier}",
    target_type=CV.Disagreement,
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
    tags=(),  # the provenance meta-template has no nt:hasTag
    label="Consilience: receipt",
    description=(
        "Where a Consilience record comes from and how to check it: the receipt (the "
        "record at a pinned commit of a public repository), the content hash and the "
        "method that reproduces it, and the code, rule and map versions that produced "
        "the record. For statements a person reviewed, who reviewed them and what drafted "
        "them."
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
        St("st12", ASSERTION, CV.reviewedBy,
           PH("reviewer", ("AgentPlaceholder", "ExternalUriPlaceholder"), "reviewer (ORCID iD)"),
           optional=True),
        St("st13", ASSERTION, CV.draftedBy, _lit("draftedBy", "drafted by (in words)"), optional=True),
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


def _matches(term, slot, ns: str, assertion_iri, carried=None) -> bool:
    if isinstance(slot, URIRef):
        if slot == ASSERTION:
            return term == assertion_iri
        return term == slot
    ph: PH = slot
    if carried and ph.name in carried:
        # a superseding version keeps the IRI that the first version introduced
        return term == carried[ph.name]
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


def check_conformance(spec: TemplateSpec, graph: Graph, np_namespace: str, assertion_iri,
                      carried: dict | None = None) -> Conformance:
    """Match each triple of ``graph`` against the spec's statements.

    ``np_namespace`` is the namespace local resources live in (the temp namespace for
    unsigned output, ``https://w3id.org/np/RA…/`` once signed). ``carried`` maps the name
    of an introduced resource to the IRI an earlier version introduced, for a version that
    supersedes it (the IRI stays; it is not in this nanopub's namespace).
    """
    res = Conformance()
    hits: dict[str, int] = {s.id: 0 for s in spec.statements}
    for s, p, o in graph:
        found = None
        for st in spec.statements:
            if st.p == p and _matches(s, st.s, np_namespace, assertion_iri, carried) \
                    and _matches(o, st.o, np_namespace, assertion_iri, carried):
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
