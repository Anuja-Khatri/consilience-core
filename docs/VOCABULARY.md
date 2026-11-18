# Vocabulary

Since v2 (18 Nov 2026), every axis, condition, unit, technique, theory, dimension, position
and observable in a Consilience nanopublication is an **IRI**, not a string, so the same
condition or axis can be queried across records. Strings remain only where the value is
text: identifiers, source sentences, claim statements, page locators, rule ids and reasons.

The closed table from the source records' strings to IRIs is
[`src/consilience/export/mapping.py`](../src/consilience/export/mapping.py). A string with
no IRI there is refused, never guessed.

## Reused vocabularies

| Prefix | Namespace | Used for |
|---|---|---|
| `np`, `npx`, `nt` | nanopub schema, nanopub extensions, nanopub templates | structure, agent introduction, `npx:introduces`, `npx:supersedes`, templates |
| `prov` | `http://www.w3.org/ns/prov#` | `prov:wasAttributedTo` (the engine for records; the owner for templates and the agent introduction), `prov:wasDerivedFrom` (the GitHub receipt) |
| `dct` | `http://purl.org/dc/terms/` | `dct:identifier`, `dct:source`, `dct:creator`, `dct:license`, `dct:created`, `dct:description` |
| `foaf`, `frbr` | FOAF, FRBR core | agent name and owner (`frbr:owner` an ORCID iD), as in the Knowledge Pixels "Introducing a software agent" template |
| `qudt` | `http://qudt.org/schema/qudt/` | `qudt:QuantityValue`, `qudt:numericValue`, `qudt:unit` for every number with a unit |
| `unit`, `quantitykind` | `http://qudt.org/vocab/unit/`, `http://qudt.org/vocab/quantitykind/` | units, and the quantity kind of each axis and condition |
| `obo` | `http://purl.obolibrary.org/obo/` | ChEBI (chemicals), CHMO (measurement techniques), UBERON (brain regions, as SKOS mappings only) |
| `wd` | `http://www.wikidata.org/entity/` | a theory where an item names it exactly; otherwise as SKOS mappings |
| `skos` | SKOS | mappings from `cv` terms to the vocabularies above when the match is not exact |

(v1 used `schema:QuantitativeValue` and `schema:unitText`; v2 uses QUDT, which gives units
as IRIs.)

## Vocabulary choices, one by one

Each choice was checked against the vocabulary itself on 18 Nov 2026 (QUDT and Wikidata
pages, EBI OLS for ChEBI, CHMO and UBERON).

### Units (QUDT; one minted)

| As written in the ledger | IRI | Note |
|---|---|---|
| `h` | `unit:HR` | |
| `V` | `unit:V` | |
| `mV` | `unit:MilliV` | |
| `A/g` | `unit:A-PER-GM` | QUDT quantity kind `SpecificElectricCurrent` |
| `A/cm^2` | `unit:A-PER-CentiM2` | |
| `mol/L` | `unit:MOL-PER-L` | |
| `degC` | `unit:DEG_C` | |
| `mA/cm^2` | **`cv:MilliA-PER-CentiM2`** (minted) | QUDT has no mA/cm²; the minted unit is a `qudt:Unit` with quantity kind `ElectricCurrentDensity`, conversion multiplier 10 (to A/m²). It has no SKOS link to `unit:A-PER-CentiM2`: that is another unit of the same quantity, not a broader concept, and the quantity kind already says what is needed. If QUDT adds mA/cm², an `skos:exactMatch` to it will be added. Converting to A/cm² would change the number the source states, so the unit is kept. |

Every quantity also keeps `cv:unitAsWritten`, the unit exactly as the source wrote it.

### Chemicals (ChEBI)

| Ledger | IRI |
|---|---|
| electrolyte `HClO4` | `obo:CHEBI_29221` (perchloric acid) |

Only identities checked against ChEBI are in the table; any other electrolyte is refused
until it is added.

### Measurement techniques (CHMO where clean; otherwise minted)

| Ledger | IRI | Why |
|---|---|---|
| `cp_chronopotentiometry` | `obo:CHMO_0000017` (chrono-potentiometry) | exact |
| `cv_or_lsv` | `cv:CVOrLSV`, `skos:narrowMatch obo:CHMO_0000025` (cyclic voltammetry), `obo:CHMO_0000028` (linear-sweep voltammetry) | the source does not say which of the two |
| `rde_mass_activity` | `cv:RDEMassActivity`, `skos:relatedMatch obo:CHMO_0002631` (rotating-disk voltammetry) | a quantity derived from RDE measurements, not the technique itself |
| `polarization_curve` | `cv:PolarizationCurve` | no clean CHMO or Wikidata term for a whole-cell polarisation curve |

### Quantity axes (minted, with QUDT quantity kinds)

The ledger's axes are more specific than any quantity kind (an overpotential *at a stated
current density*), so they are minted as `cv:QuantityAxis` individuals, each with
`cv:quantityKind`:

| Ledger axis | IRI | Quantity kind | Mapping |
|---|---|---|---|
| `operational_stability_duration` | `cv:OperationalStabilityDuration` | `quantitykind:Time` | |
| `hours_to_threshold` | `cv:HoursToThreshold` | `quantitykind:Time` | |
| `overpotential_at_current_density` | `cv:OverpotentialAtCurrentDensity` | `quantitykind:ElectricPotential` | `skos:closeMatch wd:Q333853` (overpotential) |
| `cell_voltage_at_current_density` | `cv:CellVoltageAtCurrentDensity` | `quantitykind:Voltage` | |
| `mass_activity` | `cv:MassActivity` | `quantitykind:SpecificElectricCurrent` | |

### Conditions (minted, with QUDT quantity kinds)

A condition is a `cv:ConditionType` individual. A stated condition is a node on the claim:
`cv:statesQuantityCondition [ cv:condition <IRI>; qudt:numericValue …; qudt:unit <IRI> ]`
or `cv:statesCategoricalCondition [ cv:condition <IRI>; cv:conditionValue <IRI> ]`. An
unstated condition is `cv:conditionUnstated <IRI>`.

| Ledger condition | IRI(s) | Quantity kind / values | Rule |
|---|---|---|---|
| `current_density` | `cv:CurrentDensity` (number and unit) and `cv:CurrentDensityNormalization` (value `cv:GeometricArea`) | `quantitykind:ElectricCurrentDensity` | CR2 |
| `electrolyte` | `cv:Electrolyte` (value: a ChEBI entity) and `cv:ElectrolyteConcentration` (number and unit) | `quantitykind:AmountOfSubstanceConcentration` | CR1 |
| `temperature` | `cv:Temperature` | `quantitykind:Temperature` | CR3 |
| `ir_correction` | `cv:IRCorrection` (value `cv:IRCorrected` or `cv:NotIRCorrected`) | | CR4 |
| `prior_operation_duration` | `cv:PriorOperationDuration` | `quantitykind:Time` | |
| `anneal_temperature`, `loading`, `ph`, `protocol_tier`, `substrate` | `cv:AnnealTemperature`, `cv:CatalystLoading`, `cv:PH`, `cv:ProtocolTier`, `cv:Substrate` | | |

Claim kinds (`cv:PerformanceValue`, `cv:StabilityValue`), bounds (`cv:ExactValue`,
`cv:ApproximateValue`, `cv:LowerBound`, `cv:UpperBound`) and measurability
(`cv:MeasurableNow`) are minted individuals.

### Theories, dimensions, positions, observables (the cross-theory demo)

| Demo string | IRI | Why |
|---|---|---|
| `IIT` | `wd:Q6042884` (integrated information theory) | the Wikidata item names it exactly |
| `GNWT` | `cv:GlobalNeuronalWorkspaceTheory`, `skos:closeMatch wd:Q5252204` (Dehaene–Changeux model), `skos:broadMatch wd:Q5570791` (Global Workspace Theory) | no item is exactly GNWT |
| `locus`, `temporal_profile`, `connectivity` | `cv:Locus`, `cv:TemporalProfile`, `cv:Connectivity` (`cv:CommitmentDimension`) | dimensions of commitment, not quantities |
| eleven positions, e.g. `posterior_hot_zone`, `prefrontal_parietal_cortical_network` | `cv:PosteriorHotZone`, `cv:PrefrontalParietalCorticalNetwork`, … (`cv:TheoryPosition`) | positions of theories have no external vocabulary; the prefrontal-parietal position has `skos:relatedMatch obo:UBERON_0000451` (prefrontal cortex), `obo:UBERON_0001872` (parietal lobe) |
| `regional_decoding` | `cv:RegionalDecoding`, `skos:broadMatch wd:Q7002049` (neural decoding) | |
| `connectivity_metrics` | `cv:ConnectivityMetrics`, `skos:broadMatch wd:Q66812725` (brain connectivity), `skos:relatedMatch wd:Q56711521` (functional connectivity) | |
| `ignition_signature`, `temporal_generalization` | `cv:IgnitionSignature`, `cv:TemporalGeneralization` | no clean external term |
| polarity `asserts` | `cv:Asserts` | |

These are **observables** (`cv:observable`). The demo names no instrument, so the theory
disagreements record none (`cv:instrument` is empty), and say so in the testability reason.

## Terms defined here (`cv`)

Terms that nothing existing fits are minted under

    https://theconsilience.io/ns/cv#      (prefix cv)

That domain belongs to the project owner. Every term has an English label and comment, and
SKOS mappings where possible. The single source is the `TERMS` table in
[`src/consilience/export/vocab.py`](../src/consilience/export/vocab.py);
[`vocab/cv.ttl`](../vocab/cv.ttl) is written from it by `scripts/write_vocab.py`, and a test
checks they agree. The terms are served at that address: https://theconsilience.io/ns/cv
is a readable page with one anchor per term (for example `#claimA`), and the Turtle file is at
https://theconsilience.io/ns/cv.ttl.

- **Record classes**: `cv:Claim`, with `cv:MeasuredClaim` and `cv:TheoryClaim`;
  `cv:ComparisonRefusal`, `cv:Disagreement`, `cv:GradedCorrespondence`,
  `cv:DataQualityFinding`.
- **Refusals**: `cv:hasUnstatedCondition` (a node: `cv:condition`, `cv:unstatedIn` the
  claim IRI that lacks it, `cv:rule`; if both claims lack it, one node each),
  `cv:hasConditionMismatch` (a node: `cv:condition`, `cv:rule`, `cv:valueInClaimA`,
  `cv:valueInClaimB`, `qudt:unit`), `cv:axisOfClaimA`, `cv:axisOfClaimB` (different
  axes), `cv:hasDefect` (`cv:defectType`, `cv:defectTarget`) for other defects; outcomes
  `cv:NotComparable`, `cv:AxisMismatch`.
- **Disagreements**: `cv:dimension`, `cv:observable`, `cv:instrument`, `cv:testability`
  (`cv:TestableNow`, `cv:TestableUnderAssumption`, `cv:NotYetTestable`),
  `cv:testabilityReason`, `cv:assumption`, `cv:margin`, `cv:floor`.
- **Receipts**: `cv:sourceRepository`, `cv:sourceCommit`, `cv:contentHash`,
  `cv:hashMethod`, `cv:codeVersion`, `cv:rulesVersion`, `cv:mapVersion`, `cv:ledgerHash`,
  `cv:exportedWith`, and for reviewed statements `cv:reviewedBy` (an ORCID iD) and
  `cv:draftedBy` (in words: "a large language model"; no model name is recorded, by the
  owner's decision).
- **v1 terms** (`cv:ClaimCard`, `cv:TheoryClaimCard`, `cv:TestableDisagreement`,
  `cv:NotTestable`, `cv:conditionName`, `cv:conditionValueJson`, `cv:hasCondition`,
  `cv:objectName`, `cv:relation`, `cv:canonicalUnit`) stay defined, marked
  `owl:deprecated`, so that the v1 test records remain readable. No v2 record uses them.

## Identifiers for claims

A claim is identified by the IRI its claim-card nanopublication **introduces**:
`<https://w3id.org/np/RA…/claim>` (`npx:introduces` in the publication info). Refusals,
disagreements and correspondences name claim A and claim B by these IRIs. The GitHub
receipt (the card's record at a pinned commit, its line range and content hash) is in the
claim card's provenance (`prov:wasDerivedFrom`, `cv:contentHash`), not in its identity.

A corrected card is a new nanopublication that `npx:supersedes` the old one and introduces
the **same** claim IRI, written in full; links to the claim stay valid. See `PILOT.md`,
"Correcting a claim card".

## Hash methods

- `verdict-sha256-v0`: SHA-256 over `json.dumps(record without content_hash, sort_keys=True,
  default=str)`. This is the hasher the ledger's judge uses, so a verdict's committed
  `content_hash` reproduces from the record alone.
- `card-sha256-v0`: SHA-256 over `json.dumps(card, sort_keys=True, default=str)`. The ledger
  stores no per-card content hash, so the exporter computes one with the same hasher. The
  card's own `provenance_hash` (over its source document and sentence) is also checked, and
  the full card set is covered by the ledger's `ledger.hash` (given as `cv:ledgerHash`).
- `json-sha256-v0`: SHA-256 over `json.dumps(record, sort_keys=True, default=str)`, the same
  formula as `card-sha256-v0`, for records copied from a receipt file that stores no hash of
  its own (the cross-theory demo's claim cards and disagreements). The receipt file itself is
  covered by its SHA-256 in the source repository's manifest.

## Theory claims

Claims of scientific theories (for example IIT and GNWT in the consciousness-science
demo) state a commitment, not a measured quantity. A theory claim (`cv:TheoryClaim`) gives
the theory, a claim statement, the **dimension** of the commitment and the **position** it
takes there (all IRIs; v1 misnamed the dimension a "quantity axis"), and the source
locations it rests on (`cv:restsOn`, each with `dct:source` and `cv:pageLocator`). Every
theory claim states `cv:statementForm cv:ReviewedParaphrase`: the statement is a paraphrase
drafted by a large language model and reviewed by a person (named by `cv:reviewedBy` in the
provenance), **not a quotation**.
