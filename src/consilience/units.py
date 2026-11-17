"""Numbers and units, read strictly. Anything ambiguous is refused, never guessed.

One module for the whole package. A quantity arrives as

- a bare number (``int`` or ``float``), with the unit given separately;
- a string such as ``"350 degC"`` or ``"0.32"``;
- a mapping ``{"value": 350, "unit": "degC"}``.

The number is read by a fixed grammar (sign, digits, one decimal point, optional
exponent), never by pint's expression evaluator. Only the unit text is handed to pint.
Every refusal raises :class:`UnitError` whose ``reason`` is one short code:

==========================  ==============================================================
reason                      example input
==========================  ==============================================================
``empty``                   ``""``, ``"   "``
``not_a_number``            ``"banana"``, ``"n/a"``, ``"−5"`` (Unicode minus)
``not_a_quantity``          ``True``, ``None``, a list
``non_finite``              ``"nan"``, ``"-inf degC"``, ``float("nan")``, ``"1e400"``
``ambiguous_separator``     ``"3,14"``, ``"1,200"`` (decimal or thousands comma?)
``space_separated_digits``  ``"1 200"`` (one number or two?)
``second_decimal_point``    ``"1.2.3"``
``parenthesised_number``    ``"(1,234)"`` (accounting negative?)
``malformed_number``        ``"5-10"``, ``"1/2"``, ``"2*3"`` (ranges and arithmetic)
``compound_quantity``       ``"1 h 30 min"`` (more than one number)
``ambiguous_scale_suffix``  ``"5M"``, ``"5k"`` (scale word or unit?)
``missing_unit``            a mapping without a unit, an empty unit
``unit_given_twice``        ``"350 degC"`` with a separate unit as well
``unit_in_number``          ``"12 V"`` where a plain number is required
``unit_contains_number``    ``"cm2"`` (write ``cm^2``), ``"1/s"`` (write ``s^-1``)
``ambiguous_unit``          ``"C"`` (Celsius or coulomb?), ``"F"``, ``"k"``, ``"B"``, ...
``unknown_unit``            ``"banana"`` as a unit
``dimension_mismatch``      converting ``"300 mA"`` to volts
==========================  ==============================================================

Unit names are pint's (case matters: ``m`` is metre, ``M`` is molar; ``K`` is kelvin).
There is no alias table that rewrites spellings; ``degC`` is Celsius.
"""

from __future__ import annotations

import math
import re
from typing import Optional, Union

import pint

UREG = pint.UnitRegistry()
Number = Union[int, float]


class UnitError(ValueError):
    """A number or unit that cannot be read exactly. ``reason`` is a short code."""

    def __init__(self, reason: str, value, detail: str = ""):
        self.reason = reason
        self.value = value
        self.detail = detail
        msg = f"{reason}: {value!r}"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)


# A plain decimal number: sign, digits, at most one decimal point, optional exponent.
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_NON_FINITE = re.compile(r"(?<![A-Za-z])(nan|inf|infinity)(?![A-Za-z])", re.IGNORECASE)
# The start of a unit name (letter, degree sign, micro signs, angstrom, ohm, percent).
_UNIT_START = re.compile(r"[A-Za-z°µμÅΩ%]")
# Glued directly to a number, these read as scale words as often as units ("5M", "5k").
_SCALE_SUFFIXES = frozenset({"k", "K", "M", "m", "B", "b", "G", "T", "bn", "mn"})
# Whole-unit spellings that pint accepts but that usually mean something else.
_AMBIGUOUS_UNITS = {
    "C": "pint reads C as coulomb; write degC for Celsius or coulomb for charge",
    "F": "pint reads F as farad; write degF for Fahrenheit or farad",
    "k": "pint reads k as the Boltzmann constant",
    "B": "pint reads B as byte",
    "b": "pint reads b as barn",
    "G": "pint reads G as gauss",
    "bn": "a scale word, not a unit",
    "mn": "a scale word, not a unit",
}
# Digits are allowed in a unit only as exponents: cm^2, cm**3, s^-1.
_UNIT_EXPONENT = re.compile(r"(?:\^|\*\*)[+-]?\d+")


def _finite(x: float, value) -> float:
    if not math.isfinite(x):
        raise UnitError("non_finite", value, "NaN and infinity are not measurements")
    return x


def _split(text: str, original=None):
    """Split a string into (number, unit text or None) under the strict grammar."""
    original = text if original is None else original
    s = text.strip()
    if not s:
        raise UnitError("empty", original)
    if _NON_FINITE.search(s):
        raise UnitError("non_finite", original, "NaN and infinity are not measurements")
    if s.startswith("("):
        raise UnitError("parenthesised_number", original,
                        "an accounting negative or a grouping is ambiguous")
    m = _NUMBER.match(s)
    if not m:
        raise UnitError("not_a_number", original, "it does not start with a plain number")
    if "," in s:
        raise UnitError("ambiguous_separator", original,
                        "a comma may be a decimal or a thousands separator")
    number = _finite(float(m.group()), original)
    rest = s[m.end():]
    if rest.startswith("."):
        raise UnitError("second_decimal_point", original)
    unit = rest.strip()
    if not unit:
        return number, None
    if rest[0].isspace() and (unit[0].isdigit() or unit[0] in "+-."):
        raise UnitError("space_separated_digits", original,
                        "digits separated by a space may be one number or two")
    if not _UNIT_START.match(unit):
        raise UnitError("malformed_number", original,
                        f"unexpected {unit[0]!r} after the number (ranges and arithmetic "
                        "are refused)")
    if re.search(r"\s[+-]?\d", unit):
        raise UnitError("compound_quantity", original, "more than one number in one quantity")
    if not rest[0].isspace() and unit in _SCALE_SUFFIXES:
        raise UnitError("ambiguous_scale_suffix", original,
                        f"{unit!r} glued to a number may be a unit or a scale word")
    return number, unit


def split_quantity(text: str):
    """Split a quantity string into (number, unit text or None), fail closed."""
    if not isinstance(text, str):
        raise UnitError("not_a_quantity", text, "expected text")
    return _split(text)


def parse_number(value) -> float:
    """A plain finite number from an int, float or string. No unit is allowed."""
    if isinstance(value, bool):
        raise UnitError("not_a_quantity", value, "a boolean is not a number")
    if isinstance(value, (int, float)):
        return _finite(float(value), value)
    if isinstance(value, str):
        number, unit = _split(value)
        if unit is not None:
            raise UnitError("unit_in_number", value,
                            "a plain number is expected here; the unit is declared separately")
        return number
    raise UnitError("not_a_quantity", value, f"{type(value).__name__} is not a number")


def parse_unit(unit) -> pint.Unit:
    """Parse unit text on its own. No number may hide inside it."""
    if unit is None or (isinstance(unit, str) and not unit.strip()):
        raise UnitError("missing_unit", unit, "write 'dimensionless' for a pure number")
    if not isinstance(unit, str):
        raise UnitError("missing_unit", unit, "a unit must be text")
    u = unit.strip()
    if u in _AMBIGUOUS_UNITS:
        raise UnitError("ambiguous_unit", unit, _AMBIGUOUS_UNITS[u])
    if re.search(r"\d", _UNIT_EXPONENT.sub("", u)):
        raise UnitError("unit_contains_number", unit,
                        "digits are allowed only as exponents, e.g. cm^2 or s^-1")
    try:
        return UREG.parse_units(u)
    except pint.UndefinedUnitError:
        raise UnitError("unknown_unit", unit, "not a unit pint knows") from None
    except Exception as exc:  # pint syntax errors
        raise UnitError("unknown_unit", unit, f"cannot be read: {exc}") from None


def as_quantity(value, unit: Optional[str] = None) -> pint.Quantity:
    """A pint Quantity from a number, a string or a {value, unit} mapping, fail closed.

    ``unit`` may be given separately for a bare number or a number-only string. A unit
    in both places is refused (``unit_given_twice``) rather than one being chosen.
    A string without any unit and no separate unit gives a dimensionless quantity.
    """
    if isinstance(value, dict):
        if unit is not None:
            raise UnitError("unit_given_twice", value, "the mapping carries its own unit")
        if "value" not in value:
            raise UnitError("not_a_quantity", value, "a quantity mapping needs 'value'")
        if "unit" not in value:
            raise UnitError("missing_unit", value, "a quantity mapping needs 'unit'")
        return as_quantity(value["value"], value["unit"])
    if isinstance(value, bool) or value is None or not isinstance(value, (int, float, str)):
        raise UnitError("not_a_quantity", value,
                        f"{type(value).__name__} is not a number or a quantity")
    if isinstance(value, str):
        number, inline = _split(value)
        if inline is not None and unit is not None:
            raise UnitError("unit_given_twice", value,
                            f"the value carries {inline!r} and the unit field says {unit!r}")
        unit_text = inline if inline is not None else unit
    else:
        number = _finite(float(value), value)
        unit_text = unit
    if unit_text is None:
        return UREG.Quantity(number)
    return UREG.Quantity(number, parse_unit(unit_text))


def convert(q: pint.Quantity, target) -> float:
    """Magnitude of ``q`` in ``target`` (a unit string or pint unit), fail closed."""
    tgt = parse_unit(target) if isinstance(target, str) else target
    try:
        out = float(q.to(tgt).magnitude)
    except pint.DimensionalityError:
        raise UnitError("dimension_mismatch", f"{q:~P}",
                        "the two units measure different things") from None
    return _finite(out, f"{q:~P}")


def is_offset_unit(unit) -> bool:
    """True for units with a shifted zero (degC, degF), where 2 x is not twice as much."""
    u = parse_unit(unit) if isinstance(unit, str) else unit
    one = UREG.Quantity(1.0, u) - UREG.Quantity(0.0, u)
    return one.units != u


def _delta_unit(u):
    return (UREG.Quantity(1.0, u) - UREG.Quantity(0.0, u)).units


def convert_difference(magnitude: float, from_unit, to_unit) -> float:
    """Convert a *difference* (tolerance, uncertainty, spread) between units.

    A difference of 1 degC is 1 kelvin, not 274.15 kelvin; this handles that.
    """
    fu = parse_unit(from_unit) if isinstance(from_unit, str) else from_unit
    tu = parse_unit(to_unit) if isinstance(to_unit, str) else to_unit
    d = UREG.Quantity(magnitude, fu) - UREG.Quantity(0.0, fu)
    try:
        out = float(d.to(_delta_unit(tu)).magnitude)
    except pint.DimensionalityError:
        raise UnitError("dimension_mismatch", f"{magnitude} {fu}",
                        "the two units measure different things") from None
    return _finite(out, f"{magnitude} {fu}")


def unit_text(u) -> str:
    """Short printable form of a unit (pint's abbreviated format)."""
    u = parse_unit(u) if isinstance(u, str) else u
    s = f"{u:~P}"
    return s if s else "dimensionless"


__all__ = [
    "UREG",
    "UnitError",
    "as_quantity",
    "convert",
    "convert_difference",
    "is_offset_unit",
    "parse_number",
    "parse_unit",
    "split_quantity",
    "unit_text",
]
