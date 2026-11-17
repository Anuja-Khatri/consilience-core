# Vocabulary

## Reused vocabularies

| Prefix | Namespace | Used for |
|---|---|---|
| `np`, `npx`, `nt` | nanopub schema, nanopub extensions, nanopub templates | nanopub structure, agent introduction, signatures, templates |
| `prov` | `http://www.w3.org/ns/prov#` | `prov:wasAttributedTo` (the software agent), `prov:wasDerivedFrom` (the receipt) |
| `dct` | `http://purl.org/dc/terms/` | `dct:identifier` (record id in its source repository), `dct:source` (source document), `dct:creator`, `dct:license`, `dct:created`, `dct:description` |
| `schema` | `https://schema.org/` | `schema:QuantitativeValue`, `schema:value`, `schema:unitText` for a claim's quantity |
| `foaf`, `frbr` | FOAF, FRBR core | agent name and responsible person in the introduction, as in the Knowledge Pixels "Introducing a software agent" template |

## Terms defined here (`cv`)

Nothing existing fits a *refused comparison with named defects*, a *graded
correspondence with a ceiling*, a *testable disagreement* or a *receipt* (content hash
plus the method that reproduces it), so minimal terms are defined under

    https://theconsilience.io/ns/cv#      (prefix cv)

That domain belongs to the project owner. The terms are listed with labels and comments in
[`vocab/cv.ttl`](../vocab/cv.ttl) (generated from `src/consilience/export/vocab.py`). They
are **not yet served** at that address; making them resolvable, or minting them as
nanopublications, is a decision for before live publication.

Classes: `cv:ClaimCard`, `cv:TheoryClaimCard`, `cv:ComparisonRefusal`,
`cv:GradedCorrespondence`, `cv:TestableDisagreement`, `cv:DataQualityFinding`.

Fixed values: outcomes `cv:NotComparable`, `cv:AxisMismatch`; defect types
`cv:ConditionUnstated`, `cv:ConditionMismatch`, `cv:AxisMismatch`, `cv:TypeMismatch`,
`cv:QuantityRefused`; testability `cv:TestableNow`, `cv:TestableUnderAssumption`,
`cv:NotTestable`; statement form `cv:ReviewedParaphrase`.

Properties: record links (`cv:claimA`, `cv:claimB`, `cv:hasDefect`, `cv:defectType`,
`cv:defectTarget`, `cv:outcome`, `cv:axis`, `cv:grade`, `cv:gradeCeiling`,
`cv:equivocation`, `cv:testability`, `cv:instrument`, `cv:assumption`, `cv:margin`,
`cv:floor`, `cv:canonicalUnit`, `cv:dataset`, `cv:check`, `cv:recordsChecked`,
`cv:recordsFlagged`), claim-card fields (`cv:sourceSentence`, `cv:subjectName`,
`cv:objectName`, `cv:relation`, `cv:claimKind`, `cv:hasQuantity`, `cv:bound`,
`cv:hasCondition`, `cv:conditionName`, `cv:conditionValueJson`, `cv:conditionUnstated`,
`cv:measurability`, `cv:measurableWith`, `cv:claimASentence`, `cv:claimBSentence`),
theory-claim-card fields (`cv:theory`, `cv:claimStatement`, `cv:statementForm`,
`cv:polarity`, `cv:restsOn`, `cv:pageLocator`; the value on the axis uses `rdf:value`) and
receipt fields (`cv:sourceRepository`, `cv:sourceCommit`, `cv:contentHash`,
`cv:hashMethod`, `cv:codeVersion`, `cv:rulesVersion`, `cv:mapVersion`, `cv:ledgerHash`,
`cv:exportedWith`).

## Identifiers for claims

A claim is identified by the link to its claim card at a pinned commit of the public
repository, for example
`https://github.com/Anuja-Khatri/consilience-ledger/blob/7c1f9235…/ledger/claims.json#L623-L668`.
The claim-card nanopub describes that IRI, and refusals name their two claims by the same
IRIs, so the records join without a separate identifier scheme. Following the link shows
the card itself.

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

## Theory claim cards

Claims of scientific theories (for example IIT and GNWT in the consciousness-science
demo) state a commitment, not a measured quantity, so the measured-quantity claim card
does not fit them. A theory claim card (`cv:TheoryClaimCard`) gives the theory, a claim
statement, the axis of the commitment and its value there, and the source locations it
rests on (`cv:restsOn`, each with `dct:source` and `cv:pageLocator`). Every theory claim
card states `cv:statementForm cv:ReviewedParaphrase`: the statement is a paraphrase that a
person has reviewed, **not a quotation**.
