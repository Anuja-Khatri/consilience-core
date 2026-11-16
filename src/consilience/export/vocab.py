"""Vocabulary used by the nanopublication exporter.

Existing vocabularies are reused where they fit:

- PROV-O (``prov:``) for attribution and derivation,
- Dublin Core terms (``dct:``) for identifiers, sources, creators, licences,
- schema.org (``https://schema.org/``) for a quantity's value and unit text,
- the nanopub vocabularies (``np:``, ``npx:``, ``nt:``) for nanopub structure,
  agent introductions and templates.

Where nothing existing fits honestly (comparison refusals, defects, grades, receipts),
minimal terms are defined under ``https://theconsilience.io/ns/cv#`` (prefix ``cv``).
That namespace is on a domain the project owner controls; the terms are documented in
``vocab/cv.ttl`` and ``docs/VOCABULARY.md``. They are not yet served at that address.
"""

from rdflib import Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, PROV, RDF, RDFS, XSD

CV = Namespace("https://theconsilience.io/ns/cv#")
NP = Namespace("http://www.nanopub.org/nschema#")
NPX = Namespace("http://purl.org/nanopub/x/")
NT = Namespace("https://w3id.org/np/o/ntemplate/")
SCHEMA = Namespace("https://schema.org/")
FRBR = Namespace("http://purl.org/vocab/frbr/core#")

DCT = DCTERMS

CC_BY_4 = URIRef("https://creativecommons.org/licenses/by/4.0/")

# Templates published by others that ours reference (all on the live network).
META_ASSERTION_TEMPLATE = URIRef(
    "https://w3id.org/np/RAgeON_vGgJCt5E4DPMi0eOPaGwNv9tbfFTRZtBwdQL0w/templateVersion")
META_PROVENANCE_TEMPLATE = URIRef(
    "https://w3id.org/np/RA-yPZEYODCS39dWOWm7NA_ClOGFHzPi8iYhLzoZf19GI/templateVersion")
PROV_TEMPLATE_ATTRIBUTED = URIRef("https://w3id.org/np/RA7lSq6MuK_TIC6JMSHvLtee3lpLoZDOqLJCLXevnrPoU")
PUBINFO_TEMPLATE_LICENSE = URIRef("https://w3id.org/np/RACJ58Gvyn91LqCKIO9zu1eijDQIeEff28iyDrJgjSJF8")
PUBINFO_TEMPLATE_CREATOR = URIRef("https://w3id.org/np/RA-N4_kFxcruvBTlo1yJv29E4SLOXsx5KO_th69PprMrA")

# Human-readable labels for every predicate and fixed value the templates use, so that
# Nanodash can render the forms. Kept here so templates and docs agree.
LABELS = {
    RDF.type: "is a",
    RDF.value: "has the value",
    DCT.identifier: "has the identifier",
    DCT.source: "comes from the source document",
    DCT.description: "is described as",
    PROV.wasAttributedTo: "is attributed to",
    PROV.wasDerivedFrom: "was derived from the receipt",
    SCHEMA.value: "has the numeric value",
    SCHEMA.unitText: "has the unit",
    SCHEMA.QuantitativeValue: "quantitative value",
    CV.ClaimCard: "claim card",
    CV.ComparisonRefusal: "comparison refusal",
    CV.GradedCorrespondence: "graded correspondence",
    CV.TestableDisagreement: "testable disagreement",
    CV.DataQualityFinding: "data-quality finding",
    CV.claimA: "compares claim A",
    CV.claimB: "with claim B",
    CV.claimASentence: "claim A's source sentence",
    CV.claimBSentence: "claim B's source sentence",
    CV.axis: "is on the quantity axis",
    CV.outcome: "has the outcome",
    CV.hasDefect: "has the defect",
    CV.defectType: "is of defect type",
    CV.defectTarget: "concerns",
    CV.NotComparable: "not comparable",
    CV.AxisMismatch: "different quantity axes",
    CV.ConditionUnstated: "condition not stated",
    CV.ConditionMismatch: "condition differs",
    CV.TypeMismatch: "different claim kinds",
    CV.QuantityRefused: "quantity could not be read",
    CV.sourceSentence: "has the source sentence",
    CV.subjectName: "is about the subject",
    CV.objectName: "measures",
    CV.relation: "has the relation",
    CV.claimKind: "is of claim kind",
    CV.hasQuantity: "states the quantity",
    CV.bound: "with bound",
    CV.hasCondition: "states the condition",
    CV.conditionName: "has the condition name",
    CV.conditionValueJson: "has the condition value (JSON)",
    CV.conditionUnstated: "does not state the condition",
    CV.measurability: "has measurability",
    CV.measurableWith: "is measurable with",
    CV.grade: "has the grade",
    CV.gradeCeiling: "with the ceiling",
    CV.equivocation: "has the equivocation-check result",
    CV.testability: "has testability",
    CV.TestableNow: "testable now",
    CV.TestableUnderAssumption: "testable under a named assumption",
    CV.NotTestable: "not testable",
    CV.instrument: "is testable with the instrument",
    CV.assumption: "under the assumption",
    CV.margin: "differs by the margin",
    CV.floor: "beyond the floor",
    CV.canonicalUnit: "in the unit",
    CV.dataset: "concerns the dataset",
    CV.check: "applies the check",
    CV.recordsChecked: "checked this many records",
    CV.recordsFlagged: "flagged this many records",
    CV.sourceRepository: "comes from the repository",
    CV.sourceCommit: "at the commit",
    CV.contentHash: "has the content hash",
    CV.hashMethod: "hashed with the method",
    CV.codeVersion: "was computed by the code version",
    CV.rulesVersion: "under the rule version",
    CV.mapVersion: "with the axis map version",
    CV.ledgerHash: "is covered by the ledger hash",
    CV.exportedWith: "was exported with",
}

__all__ = [
    "CV", "NP", "NPX", "NT", "SCHEMA", "FRBR", "DCT", "FOAF", "PROV", "RDF", "RDFS", "XSD",
    "CC_BY_4", "LABELS",
    "META_ASSERTION_TEMPLATE", "META_PROVENANCE_TEMPLATE", "PROV_TEMPLATE_ATTRIBUTED",
    "PUBINFO_TEMPLATE_LICENSE", "PUBINFO_TEMPLATE_CREATOR",
]
