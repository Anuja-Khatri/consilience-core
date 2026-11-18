"""Vocabulary used by the nanopublication exporter.

Existing vocabularies are reused where they fit honestly (each choice is documented in
``docs/VOCABULARY.md``):

- PROV-O (``prov:``) for attribution and derivation,
- Dublin Core terms (``dct:``) for identifiers, sources, creators, licences,
- QUDT (``qudt:``, ``unit:``, ``quantitykind:``) for numeric values, units and the kind of
  quantity an axis or condition measures,
- ChEBI (``obo:CHEBI_…``) for chemicals such as electrolytes,
- CHMO (``obo:CHMO_…``) for measurement techniques,
- Wikidata (``wd:``) where an item names the thing exactly (a theory),
- SKOS (``skos:``) to map our own terms to those above when the match is not exact,
- the nanopub vocabularies (``np:``, ``npx:``, ``nt:``) for nanopub structure, agent
  introductions and templates.

Where nothing existing fits honestly (comparison refusals, defects, grades, receipts, the
ledger's axes and conditions, the positions theories take), terms are minted under
``https://theconsilience.io/ns/cv#`` (prefix ``cv``), each with a label, a comment and,
where possible, a SKOS mapping. ``TERMS`` below is the single source: ``vocab/cv.ttl`` is
written from it by ``scripts/write_vocab.py`` and a test checks that the two agree. The
namespace is on a domain the project owner controls and is served there (a page with one
anchor per term at https://theconsilience.io/ns/cv; Turtle at https://theconsilience.io/ns/cv.ttl).
"""

from rdflib import Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, OWL, PROV, RDF, RDFS, SKOS, XSD

CV = Namespace("https://theconsilience.io/ns/cv#")
CV_ONTOLOGY = URIRef("https://theconsilience.io/ns/cv")
NP = Namespace("http://www.nanopub.org/nschema#")
NPX = Namespace("http://purl.org/nanopub/x/")
NT = Namespace("https://w3id.org/np/o/ntemplate/")
SCHEMA = Namespace("https://schema.org/")
FRBR = Namespace("http://purl.org/vocab/frbr/core#")
QUDT = Namespace("http://qudt.org/schema/qudt/")
UNIT = Namespace("http://qudt.org/vocab/unit/")
QK = Namespace("http://qudt.org/vocab/quantitykind/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
WD = Namespace("http://www.wikidata.org/entity/")
ORCID = Namespace("https://orcid.org/")

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
PUBINFO_TEMPLATE_SUPERSEDES = URIRef("https://w3id.org/np/RAoTD7udB2KtUuOuAe74tJi1t3VzK0DyWS7rYVAq1GRvw")

# ---------------------------------------------------------------------------------------
# Terms minted under cv. Each entry: local name -> dict with
#   kind: "class" | "property" | "individual" | "unit"
#   label, comment
#   optional: type (extra rdf:type), sub (rdfs:subClassOf), qk (qudt quantity kind),
#             unit_qk/multiplier (for units), and SKOS mappings exact/close/broad/narrow/related
#             (lists of IRIs), deprecated (text saying what replaces it).
# ---------------------------------------------------------------------------------------

_LEDGER = "Used by the claim cards of the consilience-ledger (electrocatalysis)."
_DEMO = "Used by the cross-theory demo's claim cards (consciousness science)."

TERMS: dict[str, dict] = {
    # --- record classes
    "Claim": dict(kind="class", label="claim",
                  comment="A claim, identified by the IRI that its claim-card nanopublication introduces. "
                          "The IRI stays the same when a corrected card supersedes the first one."),
    "MeasuredClaim": dict(kind="class", sub=CV.Claim, label="measured claim",
                          comment="A claim that states a measured quantity on an axis, with its unit, the "
                                  "conditions stated for it and the conditions not stated."),
    "TheoryClaim": dict(kind="class", sub=CV.Claim, label="theory claim",
                        comment="A claim of a scientific theory: the position the theory takes on one "
                                "dimension of commitment. It states no measured quantity."),
    "ComparisonRefusal": dict(kind="class", label="comparison refusal",
                              comment="A comparison between two claims that was refused, with each reason named: "
                                      "which condition is not stated in which claim, which condition differs and "
                                      "its two values, or which axes differ."),
    "Disagreement": dict(kind="class", label="disagreement",
                         comment="Two claims take different values on the same dimension. Records the dimension, "
                                 "the observables and instruments that bear on it, and whether the "
                                 "disagreement is testable now, testable under a stated assumption, or not yet "
                                 "testable, with the reason."),
    "GradedCorrespondence": dict(kind="class", label="graded correspondence",
                                 comment="Two claims judged to correspond at a grade on a four-rung ladder (rung 1 "
                                         "strongest, 4 weakest), with a ceiling stating what the grade does not license."),
    "DataQualityFinding": dict(kind="class", label="data-quality finding",
                               comment="A check run over a dataset and how many records it flagged out of how many it "
                                       "checked. Credits the dataset; not a statement about its authors."),
    "QuantityAxis": dict(kind="class", label="quantity axis",
                         comment="What a measured claim's number is a value of (for example, the overpotential at a "
                                 "stated current density). Mapped to a QUDT quantity kind with cv:quantityKind."),
    "ConditionType": dict(kind="class", label="condition",
                          comment="A condition under which a measured claim was made (for example, the electrolyte "
                                  "or the current density)."),
    "CommitmentDimension": dict(kind="class", label="dimension of commitment",
                                comment="A dimension on which a theory commits to a position (for example, where "
                                        "consciousness is located). Not a quantity."),
    "TheoryPosition": dict(kind="class", label="position of a theory",
                           comment="A position a theory's claim takes on a dimension of commitment."),
    "Observable": dict(kind="class", label="observable",
                       comment="Something that can be measured and that a disagreement bears on (for example, "
                               "regional decoding of conscious content). Not an instrument."),
    "MeasurementTechnique": dict(kind="class", label="measurement technique",
                                 comment="A technique a quantity is measured with."),

    # --- outcomes, defect types, testability, forms, bounds, polarity
    "NotComparable": dict(kind="individual", label="not comparable",
                          comment="Outcome: the two claims cannot be compared under the rule set."),
    "AxisMismatch": dict(kind="individual", label="different quantity axes",
                         comment="Outcome and defect type: the two claims are on different quantity axes."),
    "ConditionUnstated": dict(kind="individual", label="condition not stated",
                              comment="Defect type: a condition the rule set requires is not stated in a claim."),
    "ConditionMismatch": dict(kind="individual", label="condition differs",
                              comment="Defect type: a condition is stated in both claims with different values."),
    "TypeMismatch": dict(kind="individual", label="different claim kinds",
                         comment="Defect type: the two claims are of different kinds."),
    "QuantityRefused": dict(kind="individual", label="quantity could not be read",
                            comment="Defect type: a claim's quantity could not be read."),
    "TestableNow": dict(kind="individual", label="testable now",
                        comment="Testability: the disagreement can be tested with observables and instruments that exist today."),
    "TestableUnderAssumption": dict(kind="individual", label="testable under a stated assumption",
                                    comment="Testability: the disagreement can be tested if the stated assumption holds."),
    "NotYetTestable": dict(kind="individual", label="not yet testable",
                           comment="Testability: no observable or instrument that exists today can settle the "
                                   "disagreement; the reason says why."),
    "ReviewedParaphrase": dict(kind="individual", label="a paraphrase reviewed by a person, not a quotation",
                               comment="Statement form: the claim statement paraphrases its source and was reviewed "
                                       "by a person. It is not a quotation."),
    "ExactValue": dict(kind="individual", label="exact value",
                       comment="Bound: the value is stated as exact."),
    "ApproximateValue": dict(kind="individual", label="approximate value",
                             comment="Bound: the value is stated as approximate (for example, \"about 470 h\")."),
    "LowerBound": dict(kind="individual", label="lower bound",
                       comment="Bound: the true value is at least this (for example, \">40 h\")."),
    "UpperBound": dict(kind="individual", label="upper bound",
                       comment="Bound: the true value is at most this."),
    "Asserts": dict(kind="individual", label="asserts", comment="Polarity: the theory asserts the position."),
    "Denies": dict(kind="individual", label="denies", comment="Polarity: the theory denies the position."),
    "PerformanceValue": dict(kind="individual", label="performance value",
                             comment="Claim kind: a measured performance figure. " + _LEDGER),
    "StabilityValue": dict(kind="individual", label="stability value",
                           comment="Claim kind: a measured stability figure. " + _LEDGER),
    "MeasurableNow": dict(kind="individual", label="measurable now",
                          comment="Measurability: the quantity can be measured with techniques that exist today."),

    # --- quantity axes of the ledger
    "OperationalStabilityDuration": dict(kind="individual", type=CV.QuantityAxis, qk=QK.Time,
                                         label="operational stability duration",
                                         comment="How long a catalyst operated stably in a test. " + _LEDGER),
    "HoursToThreshold": dict(kind="individual", type=CV.QuantityAxis, qk=QK.Time,
                             label="time to a potential threshold",
                             comment="How long a catalyst operated before its potential reached a stated "
                                     "threshold. A different axis from operational stability duration, though "
                                     "both are times. " + _LEDGER),
    "OverpotentialAtCurrentDensity": dict(kind="individual", type=CV.QuantityAxis, qk=QK.ElectricPotential,
                                          label="overpotential at a stated current density",
                                          close=[WD.Q333853],
                                          comment="The overpotential needed to reach a stated current density. " + _LEDGER),
    "CellVoltageAtCurrentDensity": dict(kind="individual", type=CV.QuantityAxis, qk=QK.Voltage,
                                        label="cell voltage at a stated current density",
                                        comment="The voltage of a whole electrolysis cell at a stated current "
                                                "density. " + _LEDGER),
    "MassActivity": dict(kind="individual", type=CV.QuantityAxis, qk=QK.SpecificElectricCurrent,
                         label="mass activity",
                         comment="Current per mass of catalyst. " + _LEDGER),

    # --- conditions of the ledger
    "CurrentDensity": dict(kind="individual", type=CV.ConditionType, qk=QK.ElectricCurrentDensity,
                           label="current density",
                           comment="The current density at which the claim was measured. Comparability rule CR2. " + _LEDGER),
    "CurrentDensityNormalization": dict(kind="individual", type=CV.ConditionType,
                                        label="current-density normalisation",
                                        comment="What area the current density is normalised to (geometric "
                                                "electrode area or electrochemically active surface area). "
                                                "Part of rule CR2. " + _LEDGER),
    "GeometricArea": dict(kind="individual", label="normalised to the geometric electrode area",
                          comment="Value of cv:CurrentDensityNormalization."),
    "Electrolyte": dict(kind="individual", type=CV.ConditionType, label="electrolyte",
                        comment="The electrolyte the claim was measured in; its value is a ChEBI entity. "
                                "Comparability rule CR1, together with cv:ElectrolyteConcentration. " + _LEDGER),
    "ElectrolyteConcentration": dict(kind="individual", type=CV.ConditionType,
                                     qk=QK.AmountOfSubstanceConcentration,
                                     label="electrolyte concentration",
                                     comment="The concentration of the electrolyte. Part of rule CR1. " + _LEDGER),
    "Temperature": dict(kind="individual", type=CV.ConditionType, qk=QK.Temperature,
                        label="temperature",
                        comment="The temperature of measurement. Comparability rule CR3. " + _LEDGER),
    "IRCorrection": dict(kind="individual", type=CV.ConditionType, label="iR correction",
                         comment="Whether the reported potential is corrected for the ohmic (iR) drop. "
                                 "Comparability rule CR4. " + _LEDGER),
    "IRCorrected": dict(kind="individual", label="iR-corrected", comment="Value of cv:IRCorrection."),
    "NotIRCorrected": dict(kind="individual", label="not iR-corrected", comment="Value of cv:IRCorrection."),
    "PriorOperationDuration": dict(kind="individual", type=CV.ConditionType, qk=QK.Time,
                                   label="prior operation duration",
                                   comment="How long the catalyst had operated before the measurement. " + _LEDGER),
    "AnnealTemperature": dict(kind="individual", type=CV.ConditionType, qk=QK.Temperature,
                              label="anneal temperature",
                              comment="The temperature at which the catalyst was annealed. " + _LEDGER),
    "CatalystLoading": dict(kind="individual", type=CV.ConditionType, label="catalyst loading",
                            comment="The mass of catalyst per electrode area. " + _LEDGER),
    "PH": dict(kind="individual", type=CV.ConditionType, label="pH",
               comment="The pH of the electrolyte. " + _LEDGER),
    "ProtocolTier": dict(kind="individual", type=CV.ConditionType, label="protocol tier",
                         comment="Which tier of a stated testing protocol was followed. " + _LEDGER),
    "Substrate": dict(kind="individual", type=CV.ConditionType, label="substrate",
                      comment="The substrate the catalyst is supported on. " + _LEDGER),

    # --- a unit QUDT does not have
    "MilliA-PER-CentiM2": dict(kind="unit", unit_qk=QK.ElectricCurrentDensity, multiplier="10.0",
                               label="milliampere per square centimetre",
                               comment="mA/cm²: QUDT has A/cm² (unit:A-PER-CentiM2) but no mA/cm². One mA/cm² "
                                       "is 10 A/m² (the conversion multiplier to the SI unit)."),

    # --- measurement techniques with no clean existing term
    "PolarizationCurve": dict(kind="individual", type=CV.MeasurementTechnique,
                              label="polarisation curve of an electrolysis cell",
                              comment="Cell voltage recorded against current density for a whole cell. " + _LEDGER),
    "CVOrLSV": dict(kind="individual", type=CV.MeasurementTechnique,
                    label="cyclic or linear-sweep voltammetry",
                    narrow=[OBO.CHMO_0000025, OBO.CHMO_0000028],
                    comment="Either cyclic voltammetry or linear-sweep voltammetry; the source does not say "
                            "which. " + _LEDGER),
    "RDEMassActivity": dict(kind="individual", type=CV.MeasurementTechnique,
                            label="mass activity from rotating-disk-electrode measurements",
                            related=[OBO.CHMO_0002631],
                            comment="Mass activity measured with a rotating-disk electrode. " + _LEDGER),

    # --- the cross-theory demo
    "GlobalNeuronalWorkspaceTheory": dict(kind="individual", label="Global Neuronal Workspace Theory (GNWT)",
                                          close=[WD.Q5252204], broad=[WD.Q5570791],
                                          comment="The theory of consciousness of Dehaene, Changeux and colleagues. "
                                                  "Wikidata's 'Dehaene–Changeux model' item is a close match; "
                                                  "'Global Workspace Theory' is broader. " + _DEMO),
    "Locus": dict(kind="individual", type=CV.CommitmentDimension, label="locus",
                  comment="Where consciousness is located (which system or brain regions). " + _DEMO),
    "TemporalProfile": dict(kind="individual", type=CV.CommitmentDimension, label="time course",
                            comment="How conscious content unfolds in time. " + _DEMO),
    "Connectivity": dict(kind="individual", type=CV.CommitmentDimension, label="connectivity",
                         comment="What pattern of connections consciousness requires. " + _DEMO),
    "RegionalDecoding": dict(kind="individual", type=CV.Observable, label="regional decoding",
                             broad=[WD.Q7002049],
                             comment="Decoding conscious content from the activity of particular brain regions. " + _DEMO),
    "ConnectivityMetrics": dict(kind="individual", type=CV.Observable, label="connectivity metrics",
                                broad=[WD.Q66812725], related=[WD.Q56711521],
                                comment="Measures of how brain regions are connected, structurally or "
                                        "functionally. " + _DEMO),
    "IgnitionSignature": dict(kind="individual", type=CV.Observable, label="ignition signature",
                              comment="A sudden, sustained, widespread rise of activity when content becomes "
                                      "conscious. " + _DEMO),
    "TemporalGeneralization": dict(kind="individual", type=CV.Observable, label="temporal generalisation",
                                   comment="Whether a decoder trained at one time point also decodes at others, "
                                           "which shows whether a representation is sustained. " + _DEMO),
    # positions taken by the eleven published theory claims
    "SingleMaximalComplex": dict(kind="individual", type=CV.TheoryPosition, label="a single maximal complex",
                                 comment="Locus: one maximally irreducible system, not any subset or superset. " + _DEMO),
    "MaximalIrreducibleComplex": dict(kind="individual", type=CV.TheoryPosition,
                                      label="a bounded maximal irreducible complex",
                                      comment="Locus: a bounded complex of elements with maximal integrated "
                                              "information. " + _DEMO),
    "IntrinsicNotBroadcast": dict(kind="individual", type=CV.TheoryPosition, label="intrinsic, not broadcast",
                                  comment="Locus: intrinsic to the physical substrate, not a relay or global "
                                          "broadcast. " + _DEMO),
    "PosteriorHotZone": dict(kind="individual", type=CV.TheoryPosition, label="a posterior cortical hot zone",
                             comment="Locus: posterior cortex rather than prefrontal regions. " + _DEMO),
    "PrefrontalParietalCorticalNetwork": dict(kind="individual", type=CV.TheoryPosition,
                                              label="a prefrontal-parietal cortical network",
                                              related=[OBO.UBERON_0000451, OBO.UBERON_0001872],
                                              comment="Locus: a large-scale network of prefrontal and parietal "
                                                      "(and cingulate and temporal) cortex. " + _DEMO),
    "SustainedMaintenance": dict(kind="individual", type=CV.TheoryPosition, label="sustained maintenance",
                                 comment="Time course: sustained over tens to hundreds of milliseconds, not "
                                         "transient. " + _DEMO),
    "LateOnsetThreshold": dict(kind="individual", type=CV.TheoryPosition, label="late onset past a threshold",
                               comment="Time course: a late (>300 ms) all-or-none onset. " + _DEMO),
    "GradualBuildup": dict(kind="individual", type=CV.TheoryPosition, label="gradual build-up",
                           comment="Time course: builds up gradually across cortical areas. " + _DEMO),
    "SerialAllOrNone": dict(kind="individual", type=CV.TheoryPosition, label="serial and all-or-none",
                            comment="Time course: one interpretation at a time reaches consciousness. " + _DEMO),
    "HeterogeneousConnectivityRequired": dict(kind="individual", type=CV.TheoryPosition,
                                              label="heterogeneous connectivity required",
                                              comment="Connectivity: diverse, specialised causal connections "
                                                      "are required. " + _DEMO),
    "GlobalWorkspaceConnectivityRequired": dict(kind="individual", type=CV.TheoryPosition,
                                                label="global-workspace connectivity required",
                                                comment="Connectivity: a functional global neuronal workspace is "
                                                        "required. " + _DEMO),

    # --- properties: claims
    "sourceSentence": dict(kind="property", label="has the source sentence",
                           comment="The exact sentence of the source document the claim is extracted from."),
    "subjectName": dict(kind="property", label="is about the subject",
                        comment="What the claim is about (for example, a catalyst), as named in the source."),
    "claimKind": dict(kind="property", label="is of claim kind", comment="The kind of claim (an IRI)."),
    "axis": dict(kind="property", label="is on the quantity axis",
                 comment="The quantity axis (a cv:QuantityAxis) a measured claim's number is a value of."),
    "quantityKind": dict(kind="property", label="has the quantity kind",
                         comment="The QUDT quantity kind of an axis or condition."),
    "hasQuantity": dict(kind="property", label="states the quantity",
                        comment="The stated quantity (a qudt:QuantityValue with qudt:numericValue and qudt:unit)."),
    "bound": dict(kind="property", label="with bound",
                  comment="Whether the value is exact, approximate, a lower bound or an upper bound."),
    "unitAsWritten": dict(kind="property", label="has the unit as written",
                          comment="The unit exactly as the source wrote it, next to its qudt:unit IRI."),
    "statesQuantityCondition": dict(kind="property", label="states the quantitative condition",
                                    comment="A stated condition with a number and a unit (cv:condition, "
                                            "qudt:numericValue, qudt:unit)."),
    "statesCategoricalCondition": dict(kind="property", label="states the categorical condition",
                                       comment="A stated condition whose value is an IRI (cv:condition, "
                                               "cv:conditionValue), for example the electrolyte as a ChEBI entity."),
    "condition": dict(kind="property", label="concerns the condition",
                      comment="Which condition (a cv:ConditionType) a node is about."),
    "conditionValue": dict(kind="property", label="has the condition value",
                           comment="The value of a categorical condition (an IRI)."),
    "conditionUnstated": dict(kind="property", label="does not state the condition",
                              comment="A condition (a cv:ConditionType) the claim's source sentence does not state."),
    "measurability": dict(kind="property", label="has measurability",
                          comment="Whether the quantity can be measured today (an IRI)."),
    "measurableWith": dict(kind="property", label="is measurable with the technique",
                           comment="A technique the quantity is measured with (an IRI)."),
    "theory": dict(kind="property", label="is a claim of the theory", comment="The theory (an IRI)."),
    "claimStatement": dict(kind="property", label="has the claim statement",
                           comment="The claim in words. For theory claims, a reviewed paraphrase, not a quotation."),
    "statementForm": dict(kind="property", label="has a statement that is",
                          comment="What kind of text the claim statement is (for example, a reviewed paraphrase)."),
    "dimension": dict(kind="property", label="concerns the dimension",
                      comment="The dimension of commitment of a theory claim, or the dimension two claims "
                              "disagree on (an IRI)."),
    "position": dict(kind="property", label="takes the position",
                     comment="The position a theory claim takes on its dimension (an IRI)."),
    "polarity": dict(kind="property", label="has the polarity", comment="Asserts or denies (an IRI)."),
    "restsOn": dict(kind="property", label="rests on the source location",
                    comment="A source location (dct:source and cv:pageLocator) the claim rests on."),
    "pageLocator": dict(kind="property", label="at the page",
                        comment="A page of the PDF that was read, which can differ from the printed page number."),

    # --- properties: pairs of claims
    "claimA": dict(kind="property", label="compares claim A", comment="Claim A: a claim IRI."),
    "claimB": dict(kind="property", label="with claim B", comment="Claim B: a claim IRI."),
    "claimASentence": dict(kind="property", label="claim A's source sentence", comment="Copied for readability."),
    "claimBSentence": dict(kind="property", label="claim B's source sentence", comment="Copied for readability."),
    "outcome": dict(kind="property", label="has the outcome", comment="The outcome of a refused comparison."),
    "hasUnstatedCondition": dict(kind="property", label="is refused because a condition is not stated",
                                 comment="A node naming the condition (cv:condition), the claim that does not "
                                         "state it (cv:unstatedIn) and the rule that requires it (cv:rule). "
                                         "One node per claim: if both claims lack a condition, there are two."),
    "unstatedIn": dict(kind="property", label="is not stated in the claim", comment="A claim IRI."),
    "hasConditionMismatch": dict(kind="property", label="is refused because a condition differs",
                                 comment="A node naming the condition (cv:condition), the rule (cv:rule), the "
                                         "value in each claim (cv:valueInClaimA, cv:valueInClaimB) and their unit "
                                         "(qudt:unit)."),
    "rule": dict(kind="property", label="under the rule",
                 comment="The identifier of a rule in the rule set named in the provenance (for example, CR2)."),
    "valueInClaimA": dict(kind="property", label="has in claim A the value", comment="A number, in the node's qudt:unit."),
    "valueInClaimB": dict(kind="property", label="has in claim B the value", comment="A number, in the node's qudt:unit."),
    "axisOfClaimA": dict(kind="property", label="claim A is on the axis", comment="A cv:QuantityAxis."),
    "axisOfClaimB": dict(kind="property", label="claim B is on the axis", comment="A cv:QuantityAxis."),
    "hasDefect": dict(kind="property", label="has the defect",
                      comment="A defect of a kind with no more specific statement (cv:defectType, cv:defectTarget)."),
    "defectType": dict(kind="property", label="is of defect type", comment="The kind of defect."),
    "defectTarget": dict(kind="property", label="concerns",
                         comment="What a defect of a kind with no more specific statement concerns, in words."),
    "grade": dict(kind="property", label="has the grade", comment="Rung 1 (strongest) to 4 (weakest)."),
    "gradeCeiling": dict(kind="property", label="with the ceiling", comment="What the grade does not license."),
    "equivocation": dict(kind="property", label="has the equivocation-check result",
                         comment="Whether the correspondence survives removing the vocabulary the two claims share."),
    "observable": dict(kind="property", label="bears on the observable", comment="A cv:Observable or other IRI."),
    "instrument": dict(kind="property", label="can be tested with the instrument",
                       comment="An instrument or technique (an IRI). Not an observable."),
    "testability": dict(kind="property", label="has testability",
                        comment="Testable now, testable under a stated assumption, or not yet testable."),
    "testabilityReason": dict(kind="property", label="for the reason", comment="Why the testability is what it is."),
    "assumption": dict(kind="property", label="under the assumption",
                       comment="The assumption under which a disagreement is testable."),
    "margin": dict(kind="property", label="differs by the margin", comment="In the node's qudt:unit."),
    "floor": dict(kind="property", label="beyond the floor", comment="In the node's qudt:unit."),
    "dataset": dict(kind="property", label="concerns the dataset", comment="A persistent link to the dataset."),
    "check": dict(kind="property", label="applies the check", comment="The check, in plain words."),
    "recordsChecked": dict(kind="property", label="checked this many records", comment="An integer."),
    "recordsFlagged": dict(kind="property", label="flagged this many records", comment="An integer."),

    # --- properties: receipts (provenance)
    "sourceRepository": dict(kind="property", label="comes from the repository", comment="A public repository."),
    "sourceCommit": dict(kind="property", label="at the commit", comment="A full 40-hex commit."),
    "contentHash": dict(kind="property", label="has the content hash", comment="SHA-256, hex."),
    "hashMethod": dict(kind="property", label="hashed with the method",
                       comment="How the content hash is recomputed (see docs/VOCABULARY.md)."),
    "codeVersion": dict(kind="property", label="was computed by the code version", comment="A version string."),
    "rulesVersion": dict(kind="property", label="under the rule version", comment="A version string."),
    "mapVersion": dict(kind="property", label="with the axis map version", comment="A version string."),
    "ledgerHash": dict(kind="property", label="is covered by the ledger hash", comment="SHA-256, hex."),
    "exportedWith": dict(kind="property", label="was exported with", comment="Exporter and version."),
    "reviewedBy": dict(kind="property", label="was reviewed by",
                       comment="The person who reviewed the record's statement (an ORCID iD)."),
    "draftedBy": dict(kind="property", label="was drafted by",
                      comment="What drafted the statement before review, in words (for example, \"a large "
                              "language model\")."),

    # --- v1 terms (test registry only), kept so that v1 records stay readable
    "ClaimCard": dict(kind="class", label="claim card (v1)", deprecated="cv:MeasuredClaim",
                      comment="v1: the claim card identified by its GitHub line range."),
    "TheoryClaimCard": dict(kind="class", label="theory claim card (v1)", deprecated="cv:TheoryClaim",
                            comment="v1: the theory claim card identified by its GitHub line range."),
    "TestableDisagreement": dict(kind="class", label="testable disagreement (v1)", deprecated="cv:Disagreement",
                                 comment="v1: a disagreement said to be testable now with an instrument."),
    "NotTestable": dict(kind="individual", label="not testable (v1)", deprecated="cv:NotYetTestable",
                        comment="v1 testability value."),
    "conditionName": dict(kind="property", label="has the condition name (v1)", deprecated="cv:condition",
                          comment="v1: a condition name as a string."),
    "conditionValueJson": dict(kind="property", label="has the condition value as JSON (v1)",
                               deprecated="cv:statesQuantityCondition and cv:statesCategoricalCondition",
                               comment="v1: a condition value as a JSON string."),
    "hasCondition": dict(kind="property", label="states the condition (v1)",
                         deprecated="cv:statesQuantityCondition and cv:statesCategoricalCondition",
                         comment="v1: a stated condition node."),
    "objectName": dict(kind="property", label="measures (v1)", deprecated="cv:axis",
                       comment="v1: what is measured, as a string."),
    "relation": dict(kind="property", label="has the relation (v1)", deprecated="cv:axis",
                     comment="v1: the relation, as a string."),
    "canonicalUnit": dict(kind="property", label="in the unit (v1)", deprecated="qudt:unit",
                          comment="v1: a unit as a string."),
}

# Labels for reused terms that appear in templates, so that forms render readably.
_EXTERNAL_LABELS = {
    RDF.type: "is a",
    RDF.value: "has the value",
    DCT.identifier: "has the identifier",
    DCT.source: "comes from the source document",
    DCT.description: "is described as",
    PROV.wasAttributedTo: "is attributed to",
    PROV.wasDerivedFrom: "was derived from the receipt",
    QUDT.QuantityValue: "quantity value",
    QUDT.numericValue: "has the numeric value",
    QUDT.unit: "in the unit",
}

LABELS = {**_EXTERNAL_LABELS, **{CV[k]: v["label"] for k, v in TERMS.items()}}

__all__ = [
    "CV", "CV_ONTOLOGY", "NP", "NPX", "NT", "SCHEMA", "FRBR", "QUDT", "UNIT", "QK", "OBO", "WD",
    "ORCID", "DCT", "FOAF", "OWL", "PROV", "RDF", "RDFS", "SKOS", "XSD", "CC_BY_4", "LABELS", "TERMS",
    "META_ASSERTION_TEMPLATE", "META_PROVENANCE_TEMPLATE", "PROV_TEMPLATE_ATTRIBUTED",
    "PUBINFO_TEMPLATE_LICENSE", "PUBINFO_TEMPLATE_CREATOR", "PUBINFO_TEMPLATE_SUPERSEDES",
]


def vocab_graph():
    """The cv vocabulary as an RDF graph (written to vocab/cv.ttl)."""
    from rdflib import Graph, Literal

    g = Graph()
    for prefix, ns in (("cv", str(CV)), ("dct", str(DCT)), ("owl", str(OWL)), ("rdfs", str(RDFS)),
                       ("skos", str(SKOS)), ("qudt", str(QUDT)), ("unit", str(UNIT)),
                       ("quantitykind", str(QK)), ("obo", str(OBO)), ("wd", str(WD))):
        g.bind(prefix, ns)
    g.add((CV_ONTOLOGY, RDF.type, OWL.Ontology))
    g.add((CV_ONTOLOGY, RDFS.label, Literal("Consilience verdict vocabulary (cv)")))
    g.add((CV_ONTOLOGY, DCT.license, CC_BY_4))
    g.add((CV_ONTOLOGY, DCT.creator, ORCID["0009-0008-3375-7858"]))
    g.add((CV_ONTOLOGY, RDFS.comment, Literal(
        "Terms for Consilience records published as nanopublications: claims, refused "
        "comparisons, disagreements, receipts, and the axes, conditions, observables and "
        "positions the records refer to. Existing vocabularies (QUDT, ChEBI, CHMO, Wikidata, "
        "PROV-O, Dublin Core) are used directly where they fit; terms here map to them with "
        "SKOS where possible.")))
    kinds = {"class": OWL.Class, "property": RDF.Property, "individual": OWL.NamedIndividual,
             "unit": QUDT.Unit}
    for local, t in TERMS.items():
        s = CV[local]
        g.add((s, RDF.type, kinds[t["kind"]]))
        if t.get("type") is not None:
            g.add((s, RDF.type, t["type"]))
        g.add((s, RDFS.label, Literal(t["label"], lang="en")))
        g.add((s, RDFS.comment, Literal(t["comment"], lang="en")))
        g.add((s, RDFS.isDefinedBy, CV_ONTOLOGY))
        if t.get("sub") is not None:
            g.add((s, RDFS.subClassOf, t["sub"]))
        if t.get("qk") is not None:
            g.add((s, CV.quantityKind, t["qk"]))
        if t.get("unit_qk") is not None:
            g.add((s, QUDT.hasQuantityKind, t["unit_qk"]))
            g.add((s, QUDT.conversionMultiplier, Literal(t["multiplier"], datatype=XSD.decimal)))
        for key, pred in (("exact", SKOS.exactMatch), ("close", SKOS.closeMatch),
                          ("broad", SKOS.broadMatch), ("narrow", SKOS.narrowMatch),
                          ("related", SKOS.relatedMatch)):
            for o in t.get(key, ()):
                g.add((s, pred, o))
        if t.get("deprecated"):
            g.add((s, OWL.deprecated, Literal(True)))
            g.add((s, RDFS.comment, Literal(f"Not used from v2 on; see {t['deprecated']}.", lang="en")))
    return g
