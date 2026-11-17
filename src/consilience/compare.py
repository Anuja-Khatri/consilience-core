"""Compare two measurements: value, unit, optional uncertainty, and conditions.

Verdicts (a closed set):

    agree                       |a - b| <= tolerance
    within_floor                not within tolerance, but |a - b| <= floor
    disagree                    |a - b| is larger than both
    not_comparable(<what>)      a condition differs, or the units measure different things
    not_stated(<what>)          a value, unit or condition is missing on one or both sides
    unparseable(<what>: <why>)  something could not be read exactly (named reason)
    undecidable_bounds          both values are one-sided bounds ("< 1e-6", "< 1e-5")
                                that can both hold: there is no single value to compare

A value may be a one-sided bound: "<1e-6", "<= 0.30 V", "≤ 0.30 V", "> 5", ">= 5 mV",
"≥ 5 mV" (see ``consilience.units.parse_bound``; "<<1" and "< nan" are unparseable).
A bound has no uncertainty. Value against bound: ``agree`` if the value satisfies the
bound within tolerance + implied precision, ``within_floor`` if only within floor +
implied precision, else ``disagree``. Bound against bound: ``disagree`` if they cannot
both hold (beyond the larger of tolerance and floor, + implied precision), else
``undecidable_bounds`` (exit 2). With no tolerance at all, ``<`` needs the value clearly
below the bound and ``<=`` allows it to equal the bound.

tolerance = max(abs_tol, rel_tol * max(|a|, |b|)) in the unit of measurement a.
floor     = max(floor option, uncertainty of a, uncertainty of b).
implied   = the precision implied by how each value is written, added to both.

Stated precision (the default; ``precision="exact"`` or ``--exact`` turns it off). A
value with no stated uncertainty that is written with k decimal places carries an
implied half-unit in its last place: "0.777" means 0.7765 to 0.7775 (see
``consilience.units.implied_precision``). The two half-units (b's converted to a's
unit) are added to the tolerance and to the floor:

    agree         |a - b| <= tolerance + implied
    within_floor  |a - b| <= floor + implied   (floor > 0)

Numbers without a decimal point ("1200", 17) are exact. A value given as text keeps its
digits; a JSON number read from a file keeps the digits written in the file (1.50 is two
places); a number given as a Python float has no written form and is exact.
Differences below one part in 10^9 of the values are treated as rounding from unit
conversion. When several problems are found, all are listed; the verdict is the first by
rank: unparseable, then not_comparable, then not_stated.

Conditions. With a domain pack, only the conditions the pack names are checked, by the
pack's rules; other conditions are listed as ignored. Without a pack, every condition
present on either side must be present on both and equal: text exactly (case and
spelling count), numbers exactly, quantities after unit conversion, records key by key.
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

import pint

from . import __version__
from .hashing import sha256_json
from .rules import RuleSet, load_rules
from .units import _NON_FINITE  # noqa: F401  (shared grammar)
from .units import (
    UREG,
    UnitError,
    as_quantity,
    convert,
    convert_difference,
    implied_precision,
    is_bound_text,
    is_offset_unit,
    legacy,
    number_text,
    parse_bound,
    parse_number,
    parse_unit,
    split_quantity,
    unit_text,
)

RECEIPT_SCHEMA = "consilience-receipt/v1"
PRECISION_MODES = ("stated", "exact")
PINT_VERSION = pint.__version__
ROUNDING = 1e-9
MEASUREMENT_KEYS = {"value", "unit", "uncertainty", "conditions", "label", "note", "source"}
RANK = {"unparseable": 0, "not_comparable": 1, "not_stated": 2}
EXIT = {"agree": 0, "within_floor": 0, "disagree": 1, "not_comparable": 2, "not_stated": 2,
        "undecidable_bounds": 2, "unparseable": 3}
UNSTATED = object()


class InputError(ValueError):
    """The input files or options themselves are unusable (exit code 64)."""


@dataclass
class CompareResult:
    verdict: str
    label: str
    defects: list
    a: dict
    b: dict
    unit: Optional[str]
    difference: Optional[float]
    tolerance: Optional[float]
    floor: Optional[float]
    conditions: dict
    pack: Optional[dict]
    receipt: dict = field(repr=False)
    precision: Optional[dict] = None

    @property
    def exit_code(self) -> int:
        return EXIT[self.verdict]

    def to_dict(self) -> dict:
        return copy.deepcopy(self.receipt)


class WrittenFloat(float):
    """A float read from a JSON file that remembers how it was written ("1.50").

    JSON parsers drop trailing zeros; this keeps them so that the stated precision of a
    number in a measurement file is not lost. It behaves as a float everywhere and is
    written back to JSON as a plain float.
    """

    __slots__ = ("text",)

    def __new__(cls, text):
        v = super().__new__(cls, text)
        v.text = str(text)
        return v

    def __getnewargs__(self):
        return (self.text,)


# ----------------------------------------------------------------- helpers
def _jsonable(obj):
    """Copy of ``obj`` safe for strict JSON: non-finite floats become their text."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return "nan" if math.isnan(obj) else ("inf" if obj > 0 else "-inf")
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    raise InputError(f"unsupported value of type {type(obj).__name__}: {obj!r}")


def _refuse_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise InputError(f"duplicate key {k!r} in a JSON object")
        out[k] = v
    return out


def read_json(path: Union[str, Path]):
    """Read a JSON file. Duplicate keys are refused; NaN/Infinity literals become text
    (and are then refused as ``non_finite`` wherever a number is needed). Numbers with
    a decimal point or exponent become ``WrittenFloat``, which keeps the written digits."""
    p = Path(path)
    if not p.is_file():
        raise InputError(f"file not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=_refuse_pairs,
                          parse_constant=lambda c: c, parse_float=WrittenFloat)
    except UnicodeDecodeError:
        raise InputError(f"{path}: not UTF-8 text") from None
    except json.JSONDecodeError as exc:
        raise InputError(f"{path}: not valid JSON: {exc}") from None


def _measurement(obj, side: str) -> dict:
    if isinstance(obj, (str, Path)):
        obj = read_json(obj)
    if not isinstance(obj, dict):
        raise InputError(f"measurement {side} must be a JSON object")
    extra = sorted(set(obj) - MEASUREMENT_KEYS)
    if extra:
        raise InputError(f"measurement {side}: unknown field(s) {extra}; allowed: "
                         f"{sorted(MEASUREMENT_KEYS)}")
    cond = obj.get("conditions", {})
    if cond is None:
        cond = {}
    if not isinstance(cond, dict):
        raise InputError(f"measurement {side}: 'conditions' must be an object")
    return _jsonable(obj)


def _defect(verdict, target, reason, detail="", rule=None) -> dict:
    return {"verdict": verdict, "target": target, "reason": reason, "detail": detail,
            "rule": rule}


def _label(d: dict) -> str:
    if d["verdict"] == "unparseable":
        return f"unparseable({d['target']}: {d['reason']})"
    return f"{d['verdict']}({d['target']})"


def _close(x: float, y: float, slack_scale: float, tol: float = 0.0) -> bool:
    return abs(x - y) <= tol + ROUNDING * slack_scale


# ------------------------------------------------------------- quantities
def _written_text(value, recorded: Optional[str]) -> Optional[str]:
    """How a numeric value was written, or None for a float with no written form."""
    if isinstance(value, str):
        return parse_bound(value).number_text if is_bound_text(value) else \
            number_text(value)
    if isinstance(value, int):
        return str(value)
    if recorded is not None:   # verify: the digits recorded in the receipt
        try:
            if float(recorded) == float(value):
                return recorded
        except ValueError:
            pass
    return getattr(value, "text", None)


def _read_value(m: dict, side: str, defects: list):
    """(pint quantity, unit text, bound sign or None) or None for one measurement's
    value and unit. Outside the 0.1.0 rules, a value written "< 1e-6" is a bound."""
    if "value" not in m or m["value"] is None or m["value"] == "":
        defects.append(_defect("not_stated", f"{side}.value", "missing"))
        return None
    value = m["value"]
    unit = m.get("unit")
    if isinstance(unit, str) and not unit.strip():
        unit = None
    op = None
    try:
        if isinstance(value, str) and not legacy() and is_bound_text(value):
            b = parse_bound(value)
            number, inline = b.number, b.unit
            op = b.op
        elif isinstance(value, str):
            number, inline = split_quantity(value)
        elif isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UnitError("not_a_quantity", value, "the value must be a number")
        else:
            number, inline = parse_number(value), None
    except UnitError as exc:
        defects.append(_defect("unparseable", f"{side}.value", exc.reason, exc.detail))
        return None
    if inline is not None and unit is not None:
        defects.append(_defect("unparseable", f"{side}.value", "unit_given_twice",
                               f"the value carries {inline!r} and 'unit' says {unit!r}"))
        return None
    text = inline if inline is not None else unit
    if text is None:
        defects.append(_defect("not_stated", f"{side}.unit", "missing",
                               "write 'dimensionless' for a pure number"))
        return None
    try:
        return UREG.Quantity(number, parse_unit(text)), text.strip(), op
    except UnitError as exc:
        where = f"{side}.value" if inline is not None else f"{side}.unit"
        defects.append(_defect("unparseable", where, exc.reason, exc.detail))
        return None


def _read_uncertainty(m: dict, side: str, q, defects: list) -> Optional[float]:
    """Uncertainty as a difference in the unit of this side's own value ``q``, or None.
    A bare number is in the measurement's own unit."""
    if m.get("uncertainty") is None:
        return 0.0
    u = m["uncertainty"]
    where = f"{side}.uncertainty"
    try:
        if isinstance(u, bool) or not isinstance(u, (int, float, str, dict)):
            raise UnitError("not_a_quantity", u, "an uncertainty is a number or a quantity")
        if isinstance(u, (int, float)) or (isinstance(u, str) and split_quantity(u)[1] is None):
            mag = parse_number(u)
            if mag < 0:
                raise UnitError("negative", u, "an uncertainty cannot be negative")
            return mag if q is not None else None   # in the measurement's own unit
        uq = as_quantity(u)
        if uq.magnitude < 0:
            raise UnitError("negative", u, "an uncertainty cannot be negative")
        if q is None:
            return None
        return convert_difference(uq.magnitude, uq.units, q.units)
    except UnitError as exc:
        defects.append(_defect("unparseable", where, exc.reason, exc.detail))
        return None


# -------------------------------------------------------------- conditions
def _leaf(v):
    """Normalise one condition value to (kind, payload). Raises UnitError."""
    if v is None:
        return ("unstated", None)
    if isinstance(v, bool):
        return ("bool", v)
    if isinstance(v, (int, float)):
        return ("number", parse_number(v))
    if isinstance(v, str):
        s = " ".join(v.split())
        if not s or s.casefold() == "unstated":
            return ("unstated", None)
        if s[0].isdigit() or s[0] in "+-.(":
            number, unit = split_quantity(s)
            if unit is None:
                return ("number", number)
            return ("quantity", UREG.Quantity(number, parse_unit(unit)), {})
        if _NON_FINITE.search(s):
            split_quantity(s)   # raises non_finite: "nan degC" is not text
        return ("text", s)
    if isinstance(v, dict):
        if "value" in v:
            q = as_quantity({"value": v["value"], "unit": v.get("unit")}) \
                if "unit" in v else as_quantity({"value": v["value"]})
            rest = {k: x for k, x in v.items() if k not in ("value", "unit")}
            return ("quantity", q, rest)
        return ("record", v)
    if isinstance(v, list):
        return ("list", v)
    raise UnitError("not_a_quantity", v, f"unsupported condition type {type(v).__name__}")


def _qmatch(qa, qb, tol_q=None) -> tuple[bool, str]:
    """Are two quantities equal (within an optional tolerance quantity)?"""
    try:
        b = convert(qb, qa.units)
    except UnitError as exc:
        return False, exc.reason
    tol = 0.0
    if tol_q is not None and tol_q.magnitude != 0:
        tol = convert_difference(tol_q.magnitude, tol_q.units, qa.units)
    ok = _close(float(qa.magnitude), b, max(abs(float(qa.magnitude)), abs(b)), tol)
    return ok, "differs"


class _Cmp:
    """Collects condition defects for one comparison."""

    def __init__(self):
        self.defects: list[dict] = []

    def unparseable(self, side, path, exc, rule=None):
        self.defects.append(_defect("unparseable", f"{side}.conditions.{path}", exc.reason,
                                    exc.detail, rule))

    def leaves(self, path, va, vb, rule=None):
        out = []
        for side, v in (("a", va), ("b", vb)):
            try:
                out.append(_leaf(v))
            except UnitError as exc:
                self.unparseable(side, path, exc, rule)
                out.append(None)
        return out

    # ---- generic comparison (no pack)
    def generic(self, path, va, vb, present_a=True, present_b=True):
        if not (present_a and present_b):
            missing = "a" if not present_a else "b"
            self.defects.append(_defect("not_stated", path, "missing",
                                        f"stated on one side only (missing on {missing})"))
            return
        la, lb = self.leaves(path, va, vb)
        if la is None or lb is None:
            return
        if la[0] == "unstated" or lb[0] == "unstated":
            self.defects.append(_defect("not_stated", path, "unstated"))
            return
        if la[0] != lb[0]:
            kinds = {la[0], lb[0]}
            reason = ("unit_on_one_side" if kinds == {"number", "quantity"} else
                      "different_kinds")
            self.defects.append(_defect("not_comparable", path, reason,
                                        f"{la[0]} on a, {lb[0]} on b"))
            return
        kind = la[0]
        if kind in ("text", "bool"):
            if la[1] != lb[1]:
                self.defects.append(_defect("not_comparable", path, "differs",
                                            f"{_raw(va)} vs {_raw(vb)}"))
        elif kind == "number":
            if not _close(la[1], lb[1], max(abs(la[1]), abs(lb[1]))):
                self.defects.append(_defect("not_comparable", path, "differs",
                                            f"{_raw(va)} vs {_raw(vb)}"))
        elif kind == "quantity":
            ok, reason = _qmatch(la[1], lb[1])
            if not ok:
                self.defects.append(_defect("not_comparable", path, reason,
                                            f"{_raw(va)} vs {_raw(vb)}"))
            self.record(path, la[2], lb[2])
        elif kind == "record":
            self.record(path, la[1], lb[1])
        elif kind == "list":
            if len(la[1]) != len(lb[1]):
                self.defects.append(_defect("not_comparable", path, "differs",
                                            "lists of different length"))
                return
            for i, (xa, xb) in enumerate(zip(la[1], lb[1])):
                self.generic(f"{path}[{i}]", xa, xb)

    def record(self, path, ra: dict, rb: dict):
        for k in sorted(set(ra) | set(rb)):
            self.generic(f"{path}.{k}" if path else k, ra.get(k), rb.get(k),
                         k in ra, k in rb)

    # ---- pack rules
    def rule(self, rule: dict, path: str, va, vb, present_a: bool, present_b: bool):
        rid = rule.get("id")
        if not (present_a and present_b):
            self.defects.append(_defect("not_stated", path, "missing",
                                        "not stated on " + ("both sides" if not
                                                            (present_a or present_b) else
                                                            ("a" if not present_a else "b")),
                                        rid))
            return
        pred = rule["predicate"]
        if pred == "record":
            if not isinstance(va, dict) or not isinstance(vb, dict):
                for side, v in (("a", va), ("b", vb)):
                    if not isinstance(v, dict) and _leaf_safe(v) != "unstated":
                        self.defects.append(_defect(
                            "unparseable", f"{side}.conditions.{path}", "expected_record",
                            "expected an object with parts " + ", ".join(rule["parts"]), rid))
                        return
                self.defects.append(_defect("not_stated", path, "unstated", rule=rid))
                return
            for pname, prule in rule["parts"].items():
                prule = dict(prule, id=rid)
                self.rule(prule, f"{path}.{pname}", va.get(pname), vb.get(pname),
                          pname in va and va.get(pname) is not None,
                          pname in vb and vb.get(pname) is not None)
            return
        la, lb = self.leaves(path, va, vb, rid)
        if la is None or lb is None:
            return
        if la[0] == "unstated" or lb[0] == "unstated":
            self.defects.append(_defect("not_stated", path, "unstated", rule=rid))
            return
        if pred == "equal":
            def canon(leaf):
                if leaf[0] != "text":
                    return leaf
                s = leaf[1].casefold() if rule.get("ignore_case") else leaf[1]
                return ("text", rule.get("aliases", {}).get(s, s))
            ca, cb = canon(la), canon(lb)
            if ca[0] in ("quantity", "record", "list") or cb[0] in ("quantity", "record",
                                                                    "list"):
                self.defects.append(_defect("not_comparable", path, "different_kinds",
                                            "'equal' compares text, numbers and true/false",
                                            rid))
            elif ca != cb:
                self.defects.append(_defect("not_comparable", path, "differs",
                                            f"{_raw(va)} vs {_raw(vb)}", rid))
            return
        # quantity_equal
        words = set(rule.get("words", []))
        wa = la[0] == "text" and la[1] in words
        wb = lb[0] == "text" and lb[1] in words
        if wa or wb:
            if not (wa and wb and la[1] == lb[1]):
                self.defects.append(_defect("not_comparable", path, "differs",
                                            f"{_raw(va)} vs {_raw(vb)}", rid))
            return
        for side, leaf in (("a", la), ("b", lb)):
            if leaf[0] != "quantity":
                reason = "missing_unit" if leaf[0] == "number" else "not_a_quantity"
                self.defects.append(_defect("unparseable", f"{side}.conditions.{path}",
                                            reason, "expected a quantity with a unit", rid))
                return
        tol = rule.get("tolerance", 0)
        tol_q = as_quantity(tol) if tol not in (0, 0.0) else None
        ok, reason = _qmatch(la[1], lb[1], tol_q)
        if not ok:
            self.defects.append(_defect("not_comparable", path, reason,
                                        f"{_raw(va)} vs {_raw(vb)}", rid))
        ra, rb = la[2], lb[2]
        for key in rule.get("also_equal", []):
            self.rule({"id": rid, "predicate": "equal"}, f"{path}.{key}", ra.get(key),
                      rb.get(key), ra.get(key) is not None, rb.get(key) is not None)


def _leaf_safe(v):
    try:
        return _leaf(v)[0]
    except UnitError:
        return "unparseable"


def _raw(v) -> str:
    """A condition value exactly as written (compact JSON), for details in results."""
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(", ", ": "))


def _check_conditions(ca: dict, cb: dict, pack: Optional[RuleSet]) -> tuple[list, dict]:
    c = _Cmp()
    keys = sorted(set(ca) | set(cb))
    if pack is None:
        c.record("", ca, cb)
        summary = {"mode": "all conditions on either side", "checked": keys, "ignored": []}
    else:
        fields = [r["field"] for r in pack.rules]
        for r in pack.rules:
            f = r["field"]
            c.rule(r, f, ca.get(f), cb.get(f), ca.get(f) is not None, cb.get(f) is not None)
        summary = {"mode": f"pack {pack.name}", "checked": fields,
                   "ignored": [k for k in keys if k not in fields]}
    return c.defects, summary


# ------------------------------------------------------------------ options
def _options(abs_tol, rel_tol, floor) -> tuple[dict, dict]:
    """Parse options. Returns (as given, for the receipt) and parsed values."""
    given = {"abs_tol": abs_tol, "rel_tol": rel_tol, "floor": floor}
    parsed: dict[str, Any] = {}
    for name in ("abs_tol", "floor"):
        v = given[name]
        if v is None:
            parsed[name] = None
            continue
        try:
            q = as_quantity(v)
        except UnitError as exc:
            raise InputError(f"--{name.replace('_', '-')} {v!r}: {exc}") from None
        if q.magnitude < 0:
            raise InputError(f"--{name.replace('_', '-')} must not be negative: {v!r}")
        parsed[name] = q
    if rel_tol is None:
        parsed["rel_tol"] = 0.0
    else:
        try:
            r = parse_number(rel_tol)
        except UnitError as exc:
            raise InputError(f"--rel-tol {rel_tol!r}: {exc} (give a fraction, e.g. 0.01 "
                             "for 1%)") from None
        if r < 0:
            raise InputError(f"--rel-tol must not be negative: {rel_tol!r}")
        parsed["rel_tol"] = r
    return given, parsed


def _option_in(q, unit, name) -> float:
    """A tolerance or floor option, as a difference in ``unit``. A bare number is in
    the unit of measurement a."""
    if q is None:
        return 0.0
    if q.dimensionless and str(q.units) == "dimensionless":
        return float(q.magnitude)
    try:
        return convert_difference(q.magnitude, q.units, unit)
    except UnitError:
        raise InputError(f"--{name.replace('_', '-')} {q:~P} is not in the same kind of "
                         f"unit as the measurements ({unit_text(unit)})") from None


# --------------------------------------------------------------------- main
def _satisfies(d: float, strict: bool, slack: float, scale: float) -> bool:
    """Is a value that lies ``d`` past a bound (d <= 0: inside it) acceptable with
    ``slack``? Strictness matters only when there is no slack: then ``<`` needs the
    value clearly below the bound, ``<=`` allows it to equal the bound."""
    r = ROUNDING * scale
    if strict and slack == 0:
        return d < -r
    return d <= slack + r


def _bounded(a_val, opa, b_val, opb, scale, tolerance, floor, implied):
    """Verdict and difference when one or both sides are one-sided bounds.

    Value against bound: d is how far the value lies past the bound (0 or less: it
    satisfies it). agree if acceptable with tolerance + implied; within_floor if only
    with floor + implied (the floor includes the value's uncertainty); else disagree.
    The difference reported is max(d, 0).

    Bound against bound: bounds in the same direction always both hold, and opposite
    bounds both hold unless the lower one lies above the upper one by more than the
    larger of tolerance and floor, plus implied. When both can hold there is no single
    value to compare: undecidable_bounds (exit 2). When they cannot: disagree, and the
    difference is the gap between them.
    """
    if opa is not None and opb is not None:
        if (opa in ("<", "<=")) == (opb in ("<", "<=")):
            return "undecidable_bounds", None
        (tu, su), (tl, sl) = (((a_val, opa), (b_val, opb)) if opa in ("<", "<=") else
                              ((b_val, opb), (a_val, opa)))
        d = tl - tu
        strict = su in ("<", ">") or sl in ("<", ">")
        ok = _satisfies(d, strict, max(tolerance, floor) + implied, scale)
        return ("undecidable_bounds" if ok else "disagree"), max(d, 0.0)
    value, (t, op) = (a_val, (b_val, opb)) if opb is not None else (b_val, (a_val, opa))
    d = value - t if op in ("<", "<=") else t - value
    strict = op in ("<", ">")
    if _satisfies(d, strict, tolerance + implied, scale):
        verdict = "agree"
    elif floor > 0 and _satisfies(d, strict, floor + implied, scale):
        verdict = "within_floor"
    else:
        verdict = "disagree"
    return verdict, max(d, 0.0)


def _side_precision(m: dict, written: Optional[str]) -> dict:
    """Implied precision of one side, in that side's own unit."""
    if m.get("uncertainty") is not None:
        return {"written": written, "implied": 0.0, "rule": "uncertainty stated"}
    if written is None:
        return {"written": None, "implied": 0.0,
                "rule": "a number with no written form (a Python float): exact"}
    half, rule = implied_precision(written)
    return {"written": written, "implied": half, "rule": rule}


def compare(a, b, *, pack: Union[str, Path, RuleSet, None] = None, abs_tol=None,
            rel_tol=None, floor=None, precision: str = "stated",
            _written: Optional[dict] = None) -> CompareResult:
    """Compare measurement ``a`` with measurement ``b``.

    ``a`` and ``b`` are dicts or paths to JSON files with ``value``, ``unit``, and
    optionally ``uncertainty``, ``conditions`` (an object), ``label``, ``note``,
    ``source``. ``pack`` is a bundled pack name, a path, or a loaded RuleSet.
    ``abs_tol`` and ``floor`` are quantities ("5 mV"; a bare number is in a's unit);
    ``rel_tol`` is a fraction. ``precision`` is ``"stated"`` (default: a value written
    with k decimal places carries an implied half-unit in its last place) or
    ``"exact"``. Raises ``InputError`` for unusable input or options.
    ``_written`` is for ``verify``: the written digits recorded in a receipt.
    """
    old = legacy()   # re-running a 0.1.0 receipt: 0.1.0 rules and receipt shape
    if precision not in PRECISION_MODES:
        raise InputError(f"precision must be one of {PRECISION_MODES}, not {precision!r}")
    if old:
        precision = "exact"
    _written = _written or {}
    ma, mb = _measurement(a, "a"), _measurement(b, "b")
    ps = load_rules(pack) if pack is not None else None
    if ps is not None and ps.kind != "compare-pack":
        raise InputError(f"{ps.origin} is a {ps.kind} file, not a compare pack")
    given, opts = _options(abs_tol, rel_tol, floor)
    if not old:
        given["precision"] = precision

    defects: list[dict] = []
    ra = _read_value(ma, "a", defects)
    rb = _read_value(mb, "b", defects)
    qa, ta, opa = ra if ra is not None else (None, None, None)
    qb, tb, opb = rb if rb is not None else (None, None, None)
    ua = _read_uncertainty(ma, "a", qa, defects)
    ub = _read_uncertainty(mb, "b", qb, defects)
    for sd, op, m in (("a", opa, ma), ("b", opb, mb)):
        if op is not None and m.get("uncertainty") is not None:
            defects.append(_defect("unparseable", f"{sd}.uncertainty", "uncertainty_on_bound",
                                   "a bound has no uncertainty; give it on a value"))

    a_val = b_val = None
    unit = None
    if qa is not None and qb is not None:
        try:
            b_val = convert(qb, qa.units)
            a_val = float(qa.magnitude)
            unit = qa.units
            if ub is not None:   # b's uncertainty is in b's unit until here
                ub = convert_difference(ub, qb.units, qa.units)
        except UnitError as exc:
            defects.append(_defect("not_comparable", "unit", exc.reason,
                                   f"{_raw(ta)} vs {_raw(tb)}"))
    if qa is not None:
        unit = qa.units
        if opts["rel_tol"] > 0 and is_offset_unit(qa.units):
            raise InputError(f"--rel-tol cannot be used with {ta}: its zero "
                             "is arbitrary, so a percentage of it means nothing; use --abs-tol")
        abs_t = _option_in(opts["abs_tol"], qa.units, "abs_tol")
        floor_t = _option_in(opts["floor"], qa.units, "floor")

    cond_defects, cond_summary = _check_conditions(ma.get("conditions") or {},
                                                   mb.get("conditions") or {}, ps)
    defects.extend(cond_defects)

    difference = tolerance = floor_applied = None
    prec: dict = {"mode": precision, "implied": 0.0 if precision == "exact" else None}
    if defects:
        defects.sort(key=lambda d: RANK[d["verdict"]])
        verdict, label = defects[0]["verdict"], _label(defects[0])
    else:
        implied = 0.0
        if precision == "stated":
            pa = _side_precision(ma, _written_text(ma["value"], _written.get("a")))
            pb = _side_precision(mb, _written_text(mb["value"], _written.get("b")))
            if pb["implied"]:
                pb["implied"] = convert_difference(pb["implied"], qb.units, qa.units)
            implied = pa["implied"] + pb["implied"]
            prec = {"mode": precision, "implied": implied, "a": pa, "b": pb}
        scale = max(abs(a_val), abs(b_val))
        tolerance = max(abs_t, opts["rel_tol"] * scale)
        floor_applied = max(floor_t, ua, ub)
        if opa is None and opb is None:
            difference = abs(a_val - b_val)
            if _close(a_val, b_val, scale, tolerance + implied):
                verdict = "agree"
            elif floor_applied > 0 and _close(a_val, b_val, scale, floor_applied + implied):
                verdict = "within_floor"
            else:
                verdict = "disagree"
        else:
            verdict, difference = _bounded(a_val, opa, b_val, opb, scale, tolerance,
                                           floor_applied, implied)
        label = verdict

    def side(m, q, val, unc, op):
        out = {"label": m.get("label"), "as_given": {k: m.get(k) for k in
                                                       ("value", "unit", "uncertainty")
                                                       if k in m}}
        if q is not None:
            out["value"] = val
            out["uncertainty"] = unc
            if op is not None:
                out["bound"] = op
        return out

    a_out = side(ma, qa, a_val if a_val is not None else
                 (float(qa.magnitude) if qa is not None else None), ua, opa)
    b_out = side(mb, qb, b_val, ub, opb)
    result = {
        "verdict": verdict,
        "label": label,
        "defects": defects,
        "unit": ta if unit is not None else None,
        "a": a_out,
        "b": b_out,
        "difference": difference,
        "tolerance": tolerance,
        "floor": floor_applied,
        "conditions": cond_summary,
    }
    if not old:
        result["comparison"] = ("values" if opa is None and opb is None else
                                "bounds" if opa is not None and opb is not None else
                                "value_vs_bound")
        result["precision"] = prec
    receipt = {
        "receipt": RECEIPT_SCHEMA,
        "command": "compare",
        "consilience_version": __version__,
        "pint_version": PINT_VERSION,
        "inputs": {"a": ma, "b": mb},
        "options": given,
        "pack": (dict(ps.describe(), content=ps.content) if ps is not None else None),
        "result": result,
    }
    receipt["sha256"] = sha256_json(receipt)
    return CompareResult(
        verdict=verdict, label=label, defects=defects, a=a_out, b=b_out,
        unit=result["unit"], difference=difference, tolerance=tolerance,
        floor=floor_applied, conditions=cond_summary,
        pack=ps.describe() if ps is not None else None, receipt=receipt,
        precision=None if old else prec)


__all__ = ["CompareResult", "InputError", "WrittenFloat", "compare", "read_json",
           "RECEIPT_SCHEMA", "PRECISION_MODES"]
