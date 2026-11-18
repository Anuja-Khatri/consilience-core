"""Export Consilience records as nanopublications.

A record envelope (see ``consilience.receipts``) becomes one nanopublication:

- **assertion**: the record's statement, shaped exactly as the matching template in
  ``consilience.export.spec`` says. Claims (measured claims and theory claims) are
  *introduced* with their own IRI (``<nanopub>/claim``); refusals, disagreements and
  correspondences name their claim A and claim B by those IRIs. Axes, conditions, units,
  techniques, theories and positions are IRIs (``consilience.export.mapping``);
- **provenance**: the receipt: the source repository and pinned commit, a link to the
  record at that commit (the GitHub receipt), the content hash and the method that
  reproduces it, the code, rule and map versions, and, for statements a person reviewed,
  the reviewer and what drafted them;
- **publication info**: the software agent as creator, the CC BY 4.0 licence, a label,
  what the nanopub introduces, links to the templates, and ``npx:supersedes`` for a
  corrected version.

Every record is checked against its receipt before anything is built; a record whose
hash does not reproduce is refused. So is every string with no IRI.

**Supersession.** A corrected claim card is published as a new nanopub that
``npx:supersedes`` the old one and introduces the *same* claim IRI (written out in full,
not as ``sub:claim``), so refusals and disagreements that point at the claim stay valid.
See ``record_nanopub(..., supersedes=...)``.

Signing uses the ``nanopub`` package with the agent's local key. Publishing goes to the
Knowledge Pixels **test** registry only.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import requests
from rdflib import Dataset, Graph, Literal, URIRef

from .. import __version__
from ..agent import REPO_ROOT, TEST_REGISTRY_URL
from ..receipts import Envelope, ReceiptError, load_envelope, verify
from . import mapping as M
from . import spec as S
from .vocab import (
    CC_BY_4, CV, DCT, FOAF, FRBR, META_ASSERTION_TEMPLATE, META_PROVENANCE_TEMPLATE, NP, NPX,
    NT, OBO, PROV, PROV_TEMPLATE_ATTRIBUTED, PUBINFO_TEMPLATE_CREATOR, PUBINFO_TEMPLATE_LICENSE,
    PUBINFO_TEMPLATE_SUPERSEDES, QK, QUDT, RDF, RDFS, SKOS, UNIT, WD, XSD,
)

SUB = S.TEMP_NS
THIS = URIRef(str(SUB))  # the nanopub itself, before signing
EXPORTER = f"consilience {__version__} (github.com/Anuja-Khatri/consilience-core)"

AGENT_INTRO_TEMPLATE = URIRef("https://w3id.org/np/RAbn04KkfbV5PK2UDGkp-j7RUghs_y75DL4qWl_8zQQ3w")

_OUTCOMES = {"not_comparable": CV.NotComparable, "axis_mismatch": CV.AxisMismatch}
_OTHER_DEFECTS = {"type_mismatch": CV.TypeMismatch, "quantity_refused": CV.QuantityRefused}
_TESTABILITY = {
    "measurable_now": CV.TestableNow,
    "testable_now": CV.TestableNow,
    "testable_under_assumption": CV.TestableUnderAssumption,
    "not_yet_testable": CV.NotYetTestable,
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


def _map(table, key, what) -> URIRef:
    try:
        return M.iri(table, key, what)
    except M.MappingError as exc:
        raise ExportError(str(exc)) from None


def _local(name: str, i: int) -> URIRef:
    """Local resource names follow Nanodash's repeat convention: name, name__1, name__2..."""
    return SUB[name if i == 0 else f"{name}__{i}"]


def _short(text: str, n: int = 200) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def _words(snake: str) -> str:
    return snake.replace("_", " ")


_SHORT = {UNIT.HR: "h", UNIT.V: "V", UNIT.MilliV: "mV", UNIT["A-PER-GM"]: "A/g",
          UNIT["A-PER-CentiM2"]: "A/cm²", UNIT["MOL-PER-L"]: "mol/L", UNIT.DEG_C: "°C",
          CV["MilliA-PER-CentiM2"]: "mA/cm²", WD.Q6042884: "IIT"}


def _label_of(term: URIRef) -> str:
    from .vocab import LABELS
    if term in _SHORT:
        return _SHORT[term]
    return LABELS.get(term, str(term))


def _num(v) -> str:
    return f"{v:g}" if isinstance(v, float) else str(v)


# ---------------------------------------------------------------------------------------
# Claim IRIs: which IRI each claim card introduced

class Claims:
    """Which claim IRI each claim card introduced, keyed by the card's receipt URL.

    Read from ``pilot/claims.json`` (written as claim cards are published). An entry holds
    ``claim_id``, ``claim_iri``, ``nanopub`` and ``envelope`` (the card's envelope file,
    relative to the repository, or an ``Envelope`` object in tests).
    """

    def __init__(self, entries: dict, root: Path = REPO_ROOT):
        self.entries = entries
        self.root = root

    @classmethod
    def load(cls, path: str | Path) -> "Claims":
        p = Path(path)
        return cls(json.loads(p.read_text(encoding="utf-8")) if p.exists() else {})

    def iri(self, receipt_url: str) -> URIRef:
        e = self.entries.get(receipt_url)
        _need(e is not None and e.get("claim_iri"),
              f"claim_not_published_yet: {receipt_url} (publish its claim card first)")
        return URIRef(e["claim_iri"])

    def card(self, receipt_url: str) -> Envelope:
        e = self.entries.get(receipt_url)
        _need(e is not None and e.get("envelope") is not None, f"no_claim_card_envelope_for: {receipt_url}")
        env = e["envelope"]
        if not isinstance(env, Envelope):
            env = load_envelope(self.root / env)
        _need(env.receipt_url == receipt_url, f"claim_card_envelope_does_not_match: {receipt_url}")
        try:
            verify(env)
        except ReceiptError as exc:
            raise ExportError(f"claim_card_receipt_does_not_verify: {exc}") from None
        return env


NO_CLAIMS = Claims({})


# ---------------------------------------------------------------------------------------
# Assertions

@dataclass
class Built:
    spec: S.TemplateSpec
    assertion: Graph
    main: URIRef           # the record's main resource
    introduced: bool       # whether the nanopub introduces ``main``
    label: str
    note: str | None = None  # plain-words note for the publication info (dct:description)
    carried: dict = field(default_factory=dict)  # introduced IRIs kept from a superseded version


def _pair(env: Envelope, claims: Claims) -> tuple[URIRef, URIRef]:
    a = env.context.get("claim_a_receipt_url")
    b = env.context.get("claim_b_receipt_url")
    _need(isinstance(a, str) and isinstance(b, str), "missing_claim_receipt_urls_in_context")
    return claims.iri(a), claims.iri(b)


def _card_conditions(card: Envelope) -> dict:
    conds = card.record.get("conditions") or {}
    _need(isinstance(conds, dict), "conditions_not_object")
    return conds


def _quantity_condition(card: Envelope, cond: URIRef):
    """The (number, unit IRI) a card states for ``cond``, or None."""
    for name, val in _card_conditions(card).items():
        if val == "unstated":
            continue
        try:
            items = M.quantity_conditions(name, val)
        except M.MappingError as exc:
            raise ExportError(str(exc)) from None
        for kind, item in items:
            if kind == "quantity" and item[0] == cond:
                return item[1], item[2]
    return None


def _categorical_conditions(card: Envelope) -> set:
    out = set()
    for name, val in _card_conditions(card).items():
        if val == "unstated":
            continue
        try:
            items = M.quantity_conditions(name, val)
        except M.MappingError as exc:
            raise ExportError(str(exc)) from None
        out |= {item for kind, item in items if kind == "categorical"}
    return out


def _refusal(env: Envelope, claims: Claims, main=None) -> Built:
    r = env.record
    _need(r.get("kind") == "rejection", f"not_a_rejection_record: kind={r.get('kind')!r}")
    outcome = _OUTCOMES.get(r.get("outcome"))
    _need(outcome is not None, f"unsupported_outcome: {r.get('outcome')!r}")
    defects = r.get("defects") or []
    _need(isinstance(defects, list) and defects, "refusal_without_defects")
    url_a, url_b = env.context.get("claim_a_receipt_url"), env.context.get("claim_b_receipt_url")
    a, b = _pair(env, claims)
    card_a, card_b = claims.card(url_a), claims.card(url_b)
    _need(card_a.record.get("claim_id") == r.get("claim_a_id")
          and card_b.record.get("claim_id") == r.get("claim_b_id"),
          "claim_cards_do_not_match_the_refusal's_claim_ids")
    rules = env.context.get("condition_rules") or {}
    _need(isinstance(rules, dict), "condition_rules_not_object")
    rule_of_field = {f: rid for rid, fields in rules.items() for f in fields}

    g = Graph()
    me = main or SUB["refusal"]
    g.add((me, RDF.type, CV.ComparisonRefusal))
    g.add((me, DCT.identifier, _lit(r["pair_id"])))
    g.add((me, CV.claimA, a))
    g.add((me, CV.claimB, b))
    if r.get("axis") is not None and outcome != CV.AxisMismatch:
        g.add((me, CV.axis, _map(M.AXES, r["axis"], "axis")))
    g.add((me, CV.outcome, outcome))

    words_unstated: dict[str, list[str]] = {}
    words_differs, words_other = [], []
    nu = nm = no = 0
    for d in defects:
        dtype, target = d.get("defect_type"), d.get("target")
        if dtype == "condition_unstated":
            cond = _map(M.CONDITIONS, target, "condition")
            _need(target in rule_of_field, f"no_rule_requires_condition: {target!r}")
            lacking = [(iri_, which) for iri_, which, card in ((a, "A", card_a), (b, "B", card_b))
                       if _card_conditions(card).get(target, "unstated") == "unstated"]
            _need(lacking, f"unstated_defect_not_supported_by_claim_cards: {target!r}")
            for iri_, which in lacking:
                node = _local("unstated", nu)
                nu += 1
                g.add((me, CV.hasUnstatedCondition, node))
                g.add((node, CV.condition, cond))
                g.add((node, CV.unstatedIn, iri_))
                g.add((node, CV.rule, _lit(rule_of_field[target])))
            who = "A and B" if len(lacking) == 2 else lacking[0][1]
            words_unstated.setdefault(who, []).append(_label_of(cond))
        elif dtype == "condition_mismatch":
            fields = rules.get(target)
            _need(isinstance(fields, list) and len(fields) == 1,
                  f"mismatch_rule_must_name_one_field: {target!r}")
            cond = _map(M.CONDITIONS, fields[0], "condition")
            va, vb = _quantity_condition(card_a, cond), _quantity_condition(card_b, cond)
            _need(va is not None and vb is not None,
                  f"mismatch_condition_not_quantitative_in_both_claims: {fields[0]!r}")
            _need(va[1] == vb[1], f"mismatch_values_in_different_units: {va[1]} vs {vb[1]}")
            _need(va[0] != vb[0], f"mismatch_values_are_equal: {fields[0]!r}")
            if cond == CV.CurrentDensity:
                # values in one record are only comparable if both use the same normalisation
                na = {c for c in _categorical_conditions(card_a) if c[0] == CV.CurrentDensityNormalization}
                nb = {c for c in _categorical_conditions(card_b) if c[0] == CV.CurrentDensityNormalization}
                _need(na == nb, "unsupported_mismatch: current-density normalisation also differs")
            node = _local("mismatch", nm)
            nm += 1
            g.add((me, CV.hasConditionMismatch, node))
            g.add((node, CV.condition, cond))
            g.add((node, CV.rule, _lit(target)))
            g.add((node, CV.valueInClaimA, _dec(va[0])))
            g.add((node, CV.valueInClaimB, _dec(vb[0])))
            g.add((node, QUDT.unit, va[1]))
            words_differs.append(f"{_label_of(cond)} differs ({_num(va[0])} vs {_num(vb[0])} "
                                 f"{_label_of(va[1])}, rule {target})")
        elif dtype == "axis_mismatch":
            _need(outcome == CV.AxisMismatch, "axis_mismatch_defect_without_axis_mismatch_outcome")
            ax_a = _map(M.AXES, card_a.record.get("axis"), "axis")
            ax_b = _map(M.AXES, card_b.record.get("axis"), "axis")
            _need(ax_a != ax_b, "axis_mismatch_but_the_cards_share_an_axis")
            _need(card_a.record["axis"] in str(target) and card_b.record["axis"] in str(target),
                  f"axis_mismatch_target_does_not_name_the_cards'_axes: {target!r}")
            g.add((me, CV.axisOfClaimA, ax_a))
            g.add((me, CV.axisOfClaimB, ax_b))
            words_other.append(f"different quantity axes ({_label_of(ax_a)} vs {_label_of(ax_b)})")
        elif dtype in _OTHER_DEFECTS:
            node = _local("defect", no)
            no += 1
            g.add((me, CV.hasDefect, node))
            g.add((node, CV.defectType, _OTHER_DEFECTS[dtype]))
            g.add((node, CV.defectTarget, _lit(target)))
            words_other.append(f"{_words(dtype)} ({target})")
        else:
            raise ExportError(f"unsupported_defect_type: {dtype!r}")
    if r.get("claim_a_sentence"):
        g.add((me, CV.claimASentence, _lit(r["claim_a_sentence"])))
    if r.get("claim_b_sentence"):
        g.add((me, CV.claimBSentence, _lit(r["claim_b_sentence"])))
    parts = words_other + words_differs
    for who in ("A", "B", "A and B"):
        if who in words_unstated:
            parts.append(f"not stated in claim {who}: " + ", ".join(words_unstated[who])
                         if who != "A and B" else "not stated in either claim: " + ", ".join(words_unstated[who]))
    label = f"Comparison refused, {r['claim_a_id']} vs {r['claim_b_id']}: " + "; ".join(parts)
    return Built(S.REFUSAL, g, me, True, _short(label, 300))


def _claim_card(env: Envelope, claims: Claims, main=None) -> Built:
    c = env.record
    q = c.get("quantity")
    _need(isinstance(q, dict), "claim_card_without_quantity")
    _need(q.get("uncertainty") is None,
          "stated_uncertainty_not_supported_by_claim_card_template_v2")
    me = main or SUB["claim"]
    doc = _iri(env.context.get("source_document_url"), "context.source_document_url")
    g = Graph()
    g.add((me, RDF.type, CV.MeasuredClaim))
    g.add((me, DCT.identifier, _lit(c["claim_id"])))
    g.add((me, CV.sourceSentence, _lit(c["source_sentence"])))
    g.add((me, DCT.source, doc))
    g.add((me, CV.subjectName, _lit(c["subject"])))
    g.add((me, CV.claimKind, _map(M.CLAIM_KINDS, c.get("claim_kind"), "claim_kind")))
    axis = _map(M.AXES, c.get("axis"), "axis")
    g.add((me, CV.axis, axis))
    qn = SUB["quantity"]
    unit = _map(M.UNITS, q.get("unit"), "unit")
    g.add((me, CV.hasQuantity, qn))
    g.add((qn, RDF.type, QUDT.QuantityValue))
    g.add((qn, QUDT.numericValue, _dec(q.get("value"))))
    g.add((qn, QUDT.unit, unit))
    g.add((qn, CV.bound, _map(M.BOUNDS, q.get("bound"), "bound")))
    g.add((qn, CV.unitAsWritten, _lit(q.get("unit"))))
    conds = _card_conditions(env)
    iq = ic = 0
    for name in sorted(conds):
        val = conds[name]
        if val == "unstated":
            g.add((me, CV.conditionUnstated, _map(M.CONDITIONS, name, "condition")))
            continue
        try:
            items = M.quantity_conditions(name, val)
        except M.MappingError as exc:
            raise ExportError(str(exc)) from None
        for kind, item in items:
            if kind == "quantity":
                node = _local("quantityCondition", iq)
                iq += 1
                g.add((me, CV.statesQuantityCondition, node))
                g.add((node, CV.condition, item[0]))
                g.add((node, QUDT.numericValue, _dec(item[1])))
                g.add((node, QUDT.unit, item[2]))
            else:
                node = _local("categoricalCondition", ic)
                ic += 1
                g.add((me, CV.statesCategoricalCondition, node))
                g.add((node, CV.condition, item[0]))
                g.add((node, CV.conditionValue, item[1]))
    if c.get("measurability"):
        g.add((me, CV.measurability, _map(M.MEASURABILITY, c["measurability"], "measurability")))
    if c.get("measurable_with"):
        g.add((me, CV.measurableWith, _map(M.TECHNIQUES, c["measurable_with"], "technique")))
    bound = "" if q.get("bound") == "exact" else f" ({_label_of(_map(M.BOUNDS, q['bound'], 'bound'))})"
    label = (f"Measured claim {c['claim_id']}: {c['subject']}, {_label_of(axis)} "
             f"{_num(q.get('value'))} {q.get('unit')}{bound}")
    return Built(S.CLAIM_CARD, g, me, True, _short(label))


def _correspondence(env: Envelope, claims: Claims, main=None) -> Built:
    r = env.record
    _need(r.get("kind") == "correspondence", f"not_a_correspondence_record: kind={r.get('kind')!r}")
    a, b = _pair(env, claims)
    g = Graph()
    me = main or SUB["correspondence"]
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


DEMO_FORK = "consilience-demo/fork-v0"


def demo_observables(fork: dict) -> list[URIRef]:
    """The observables a demo fork names (its sketch's shared observables), as IRIs."""
    obs = (fork.get("sketch") or {}).get("shared_observables") or []
    _need(obs, "demo_fork_names_no_shared_observable")
    return [_map(M.OBSERVABLES, o, "observable") for o in obs]


def demo_reason(fork: dict) -> str:
    """Why a demo fork is testable now, in words, from the record alone."""
    names = " and ".join(_label_of(o) for o in demo_observables(fork))
    return (f"The demo's check rules this disagreement decidable now: both claims bear on a shared "
            f"observable ({names}) that current methods measure. The demo names no specific "
            f"instrument, so none is recorded.")


def _demo_disagreement(env: Envelope, claims: Claims, main=None) -> Built:
    """A disagreement (fork) from the cross-theory demo's judge output."""
    r = env.record
    _need(r.get("decidability") == "now",
          f"demo_fork_not_decidable_now: {r.get('decidability')!r}")
    left, right = r.get("left_ids") or [], r.get("right_ids") or []
    _need(len(left) == 1 and len(right) == 1, "demo_fork_is_not_a_single_claim_pair")
    _need(env.context.get("testability") == "testable_now",
          f"demo_fork_testability_must_be_testable_now: {env.context.get('testability')!r}")
    _need("instrument" not in env.context and "instruments" not in env.context,
          "instrument_not_named_by_the_record: the demo names observables, not instruments")
    a, b = _pair(env, claims)
    card_a = claims.card(env.context["claim_a_receipt_url"])
    card_b = claims.card(env.context["claim_b_receipt_url"])
    _need((card_a.record.get("claim_id"), card_b.record.get("claim_id")) == (left[0], right[0]),
          "claim_cards_do_not_match_the_fork's_claim_ids")
    dim = _map(M.DIMENSIONS, r.get("axis"), "dimension")
    g = Graph()
    me = main or SUB["disagreement"]
    g.add((me, RDF.type, CV.Disagreement))
    g.add((me, DCT.identifier, _lit(f"{left[0]}|{right[0]}")))
    g.add((me, CV.claimA, a))
    g.add((me, CV.claimB, b))
    g.add((me, CV.dimension, dim))
    for o in demo_observables(r):
        g.add((me, CV.observable, o))
    g.add((me, CV.testability, CV.TestableNow))
    g.add((me, CV.testabilityReason, _lit(demo_reason(r))))
    obs = " and ".join(_label_of(o) for o in demo_observables(r))
    label = (f"Disagreement {left[0]} vs {right[0]} on {_label_of(dim)}: testable now "
             f"(observable: {obs})")
    return Built(S.DISAGREEMENT, g, me, True, _short(label))


def _theory_claim_card(env: Envelope, claims: Claims, main=None) -> Built:
    c = env.record
    _need(c.get("status") == "approved", f"claim_card_not_approved: {c.get('status')!r}")
    me = main or SUB["claim"]
    docs = env.context.get("documents") or {}
    g = Graph()
    theory = _map(M.THEORIES, c.get("theory"), "theory")
    dim = _map(M.DIMENSIONS, c.get("axis"), "dimension")
    pos = _map(M.POSITIONS, c.get("value"), "position")
    g.add((me, RDF.type, CV.TheoryClaim))
    g.add((me, DCT.identifier, _lit(c.get("claim_id"))))
    g.add((me, CV.theory, theory))
    g.add((me, CV.claimStatement, _lit(c.get("statement"))))
    g.add((me, CV.statementForm, CV.ReviewedParaphrase))
    g.add((me, CV.dimension, dim))
    g.add((me, CV.position, pos))
    if c.get("polarity"):
        g.add((me, CV.polarity, _map(M.POLARITY, c["polarity"], "polarity")))
    seen = []
    for p in c.get("prov") or []:
        prefix = str(p.get("id", "")).rsplit("_", 1)[0]
        _need(prefix in docs, f"no_document_for_passage: {p.get('id')!r}")
        key = (docs[prefix], p.get("locator"))
        if key not in seen:
            seen.append(key)
    for i, (doc, page) in enumerate(seen):
        node = _local("location", i)
        g.add((me, CV.restsOn, node))
        g.add((node, DCT.source, _iri(doc, "context.documents")))
        g.add((node, CV.pageLocator, _lit(page)))
    label = (f"Theory claim {c['claim_id']} ({c['theory']}): "
             f"{_label_of(dim)} = {_label_of(pos)}")
    return Built(S.THEORY_CLAIM_CARD, g, me, True, _short(label))


def _disagreement(env: Envelope, claims: Claims, main=None) -> Built:
    if env.context.get("record_format") == DEMO_FORK:
        return _demo_disagreement(env, claims, main)
    r = env.record
    _need(r.get("kind") == "fork", f"not_a_fork_record: kind={r.get('kind')!r}")
    t = _TESTABILITY.get(env.context.get("testability"))
    _need(t is not None, f"unsupported_testability: {env.context.get('testability')!r} "
                         f"(one of {sorted(_TESTABILITY)})")
    reason = env.context.get("testability_reason")
    _need(isinstance(reason, str) and reason.strip(), "testability_needs_a_reason")
    if t == CV.TestableUnderAssumption:
        _need(env.context.get("assumption"), "testable_under_assumption_needs_the_assumption")
    a, b = _pair(env, claims)
    g = Graph()
    me = main or SUB["disagreement"]
    g.add((me, RDF.type, CV.Disagreement))
    g.add((me, DCT.identifier, _lit(r["pair_id"])))
    g.add((me, CV.claimA, a))
    g.add((me, CV.claimB, b))
    g.add((me, CV.dimension, _map(M.AXES, r.get("axis"), "axis")))
    for o in env.context.get("observables") or []:
        g.add((me, CV.observable, _iri(o, "context.observables")))
    for i in env.context.get("instruments") or []:
        g.add((me, CV.instrument, _map(M.TECHNIQUES, i, "technique")))
    g.add((me, CV.testability, t))
    g.add((me, CV.testabilityReason, _lit(reason)))
    if env.context.get("assumption"):
        g.add((me, CV.assumption, _lit(env.context["assumption"])))
    if r.get("margin") is not None:
        g.add((me, CV.margin, _dec(r["margin"])))
        g.add((me, CV.floor, _dec(r.get("floor_applied"))))
        g.add((me, QUDT.unit, _map(M.UNITS, r.get("canonical_unit"), "unit")))
    label = f"Disagreement {r['claim_a_id']} vs {r['claim_b_id']}: {_label_of(t)}"
    return Built(S.DISAGREEMENT, g, me, True, _short(label))


def _data_quality(env: Envelope, claims: Claims, main=None) -> Built:
    r = env.record
    _need(r.get("kind") == "data_quality_finding", f"not_a_finding_record: kind={r.get('kind')!r}")
    n_checked, n_flagged = r.get("n_checked"), r.get("n_flagged")
    _need(isinstance(n_checked, int) and isinstance(n_flagged, int) and 0 <= n_flagged <= n_checked,
          "flagged_count_must_be_between_0_and_checked_count")
    g = Graph()
    me = main or SUB["finding"]
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
    "disagreement": _disagreement,
    "testable_disagreement": _disagreement,   # envelope type name used in v1
    "data_quality_finding": _data_quality,
    "theory_claim_card": _theory_claim_card,
}

_MAIN_NAME = {S.REFUSAL.key: "refusal", S.CLAIM_CARD.key: "claim", S.THEORY_CLAIM_CARD.key: "claim",
              S.CORRESPONDENCE.key: "correspondence", S.DISAGREEMENT.key: "disagreement",
              S.DATA_QUALITY.key: "finding"}


def build_assertion(env: Envelope, claims: Claims = NO_CLAIMS, supersedes: dict | None = None) -> Built:
    """Verify the receipt, then map the record to its assertion graph.

    ``supersedes``, for a corrected version, is ``{"nanopub": <old URI>, "introduces":
    <IRI the old version introduced>}``: the new version introduces that same IRI.
    """
    try:
        verify(env)
    except ReceiptError as exc:
        raise ExportError(f"receipt_does_not_verify: {exc}") from None
    main = None
    if supersedes:
        main = _iri(supersedes.get("introduces"), "supersedes.introduces")
        _need(str(main).startswith(str(supersedes.get("nanopub", "")) + "/"),
              "supersedes.introduces_must_be_the_old_nanopub's_introduced_IRI")
    built = _BUILDERS[env.record_type](env, claims, main)
    if main is not None:
        built.carried = {_MAIN_NAME[built.spec.key]: main}
    note = env.context.get("pubinfo_note")
    if note:
        built.note = _lit(note).toPython()
    return built


# ---------------------------------------------------------------------------------------
# Provenance and publication info

def build_provenance(env: Envelope, agent_iri: URIRef, review: dict | None = None) -> Graph:
    """The receipt. ``review`` (``{"reviewer": ORCID IRI, "drafted_by": words}``) is added
    for theory claim cards, whose statements were drafted and then reviewed by a person."""
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
    if env.record_type == "theory_claim_card":
        _need(review and review.get("reviewer") and review.get("drafted_by"),
              "theory_claim_card_needs_reviewer_and_drafted_by (config/review.json)")
        g.add((a, CV.reviewedBy, _iri(review["reviewer"], "review.reviewer")))
        g.add((a, CV.draftedBy, _lit(review["drafted_by"])))
    return g


def _created(created: str | None) -> Literal:
    if created is None:
        created = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return Literal(created, datatype=XSD.dateTime)


def _common_pubinfo(g: Graph, creator: URIRef, label: str, created: str | None) -> None:
    g.add((THIS, DCT.created, _created(created)))
    g.add((THIS, DCT.creator, creator))
    g.add((THIS, DCT.license, CC_BY_4))
    g.add((THIS, RDFS.label, Literal(label)))


def build_pubinfo(built: Built, agent_iri: URIRef, templates: dict, created: str | None,
                  supersedes: dict | None = None, example: bool = False,
                  prov_template: URIRef | None = None) -> Graph:
    g = Graph()
    _common_pubinfo(g, agent_iri, ("Example: " if example else "") + built.label, created)
    g.add((THIS, NPX.hasNanopubType, built.spec.target_type))
    if example:
        g.add((THIS, NPX.hasNanopubType, NPX.ExampleNanopub))
    if built.note:
        g.add((THIS, DCT.description, Literal(built.note)))
    if built.introduced:
        g.add((THIS, NPX.introduces, built.main))
    tmpl = templates.get(built.spec.key)
    _need(tmpl, f"template_not_published: {built.spec.key} (publish templates first)")
    if prov_template is None:
        prov_template = templates.get(S.RECEIPT_PROVENANCE.key)
        _need(prov_template, "template_not_published: receipt_provenance (publish templates first)")
    g.add((THIS, NT.wasCreatedFromTemplate, URIRef(tmpl)))
    g.add((THIS, NT.wasCreatedFromProvenanceTemplate, URIRef(prov_template)))
    g.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_LICENSE))
    g.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_CREATOR))
    if supersedes:
        g.add((THIS, NPX.supersedes, _iri(supersedes["nanopub"], "supersedes.nanopub")))
        g.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_SUPERSEDES))
    return g


# ---------------------------------------------------------------------------------------
# Whole nanopubs (unsigned, temp namespace)

def assemble(assertion: Graph, provenance: Graph, pubinfo: Graph) -> Dataset:
    ds = Dataset()
    for prefix, ns in (("this", str(SUB)), ("sub", str(SUB)), ("np", str(NP)), ("npx", str(NPX)),
                       ("nt", str(NT)), ("cv", "https://theconsilience.io/ns/cv#"), ("dct", str(DCT)),
                       ("prov", str(PROV)), ("rdfs", str(RDFS)), ("xsd", str(XSD)),
                       ("qudt", str(QUDT)), ("unit", str(UNIT)), ("quantitykind", str(QK)),
                       ("obo", str(OBO)), ("wd", str(WD)), ("skos", str(SKOS)),
                       ("foaf", str(FOAF)), ("frbr", str(FRBR)), ("orcid", "https://orcid.org/")):
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


def record_nanopub(env: Envelope, agent_iri: str, templates: dict, created: str | None = None,
                   claims: Claims = NO_CLAIMS, review: dict | None = None,
                   supersedes: dict | None = None) -> Dataset:
    built = build_assertion(env, claims, supersedes)
    agent = URIRef(agent_iri)
    return assemble(built.assertion, build_provenance(env, agent, review),
                    build_pubinfo(built, agent, templates, created, supersedes))


def example_nanopub(env: Envelope, agent_iri: str, templates: dict, created: str | None = None,
                    claims: Claims = NO_CLAIMS) -> Dataset:
    """An ``npx:ExampleNanopub`` for a template that has no real instance yet, so that the
    network sets up the type. Its label starts "Example: "; its data is made up and says so;
    its provenance only attributes it to the agent (there is no receipt to cite)."""
    built = build_assertion(env, claims)
    agent = URIRef(agent_iri)
    prov = Graph()
    prov.add((SUB["assertion"], PROV.wasAttributedTo, agent))
    pub = build_pubinfo(built, agent, templates, created, example=True,
                        prov_template=PROV_TEMPLATE_ATTRIBUTED)
    return assemble(built.assertion, prov, pub)


def template_nanopub(spec: S.TemplateSpec, agent_iri: str, creator_iri: str, creator_name: str,
                     created: str | None = None) -> Dataset:
    """A template, attributed to the person who designed it (``creator_iri``, an ORCID iD)
    and signed by the agent's key."""
    creator = URIRef(creator_iri)
    prov = Graph()
    prov.add((SUB["assertion"], PROV.wasAttributedTo, creator))
    pub = Graph()
    _common_pubinfo(pub, creator, spec.label, created)
    pub.add((creator, FOAF.name, Literal(creator_name)))
    pub.add((THIS, NPX.embeds, SUB["templateVersion"]))
    meta = META_ASSERTION_TEMPLATE if spec.kind == "assertion" else META_PROVENANCE_TEMPLATE
    pub.add((THIS, NT.wasCreatedFromTemplate, meta))
    pub.add((THIS, NT.wasCreatedFromProvenanceTemplate, PROV_TEMPLATE_ATTRIBUTED))
    pub.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_LICENSE))
    pub.add((THIS, NT.wasCreatedFromPubinfoTemplate, PUBINFO_TEMPLATE_CREATOR))
    _ = agent_iri  # the signer; recorded by the signature as npx:signedBy
    return assemble(S.template_assertion_graph(spec), prov, pub)


def introduction_nanopub(name: str, local_name: str, public_key: str, responsible_name: str,
                         responsible_orcid: str, created: str | None = None) -> Dataset:
    """Self-signed introduction of the engine as a software agent, owned by a person
    (``frbr:owner`` their ORCID iD). Sign with signer = the temp sub-IRI of the agent."""
    _need(isinstance(responsible_orcid, str) and responsible_orcid.strip(),
          "introduction_needs_the_owner's_orcid")
    agent = SUB[local_name]
    decl = SUB["decl"]
    owner = URIRef(f"https://orcid.org/{responsible_orcid}")
    a = Graph()
    a.add((agent, RDF.type, NPX.SoftwareAgent))
    a.add((agent, RDF.type, NPX.SoftwareTool))
    a.add((agent, FOAF.name, Literal(name)))
    a.add((agent, FRBR.owner, owner))
    a.add((decl, NPX.declaredBy, agent))
    a.add((decl, NPX.hasAlgorithm, Literal("RSA")))
    a.add((decl, NPX.hasPublicKey, Literal(public_key)))
    prov = Graph()
    prov.add((SUB["assertion"], PROV.wasAttributedTo, owner))
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
