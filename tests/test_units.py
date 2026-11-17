"""The units and number module refuses anything it cannot read exactly (fail closed).

Ported from the WP1 refusal tests of lab-gate (`wp2-release`,
tests/test_malformed_numbers.py) and consilience-ledger (`wp1-public-truth`,
tests/test_input_hardening.py and tests/test_units.py). Each refused input below was
misread or accepted by an earlier parser ("1 200" read as 200, "3,14" as 314,
"1.2.3" as 0.36, "5M" as 5 molar, "(1,234)" as +1234, NaN accepted); here every one is
refused with a named reason.
"""

from __future__ import annotations

import math

import pytest

from consilience.units import (
    UnitError,
    as_quantity,
    convert,
    convert_difference,
    is_offset_unit,
    parse_number,
    parse_unit,
)

# (input, reason code that must appear in the refusal)
REFUSED_STRINGS = [
    ("1 200", "space_separated_digits"),
    ("1 200 degC", "space_separated_digits"),
    ("416 161", "space_separated_digits"),
    ("1 200 mA/cm^2", "space_separated_digits"),
    ("3,14", "ambiguous_separator"),
    ("1,200 degC", "ambiguous_separator"),
    ("1,234 mL", "ambiguous_separator"),
    ("1.2.3", "second_decimal_point"),
    ("1.2.3 degC", "second_decimal_point"),
    ("nan", "non_finite"),
    ("NaN V", "non_finite"),
    ("nan degC", "non_finite"),
    ("inf", "non_finite"),
    ("-inf degC", "non_finite"),
    ("+Infinity", "non_finite"),
    ("1e400 degC", "non_finite"),
    ("5M", "ambiguous_scale_suffix"),
    ("5k", "ambiguous_scale_suffix"),
    ("5K", "ambiguous_scale_suffix"),
    ("5bn", "ambiguous_scale_suffix"),
    ("(1,234)", "parenthesised_number"),
    ("(1200) degC", "parenthesised_number"),
    ("5-10", "malformed_number"),
    ("5-10 min", "malformed_number"),
    ("1/2", "malformed_number"),
    ("1/2 min", "malformed_number"),
    ("2*3 min", "malformed_number"),
    ("1 h 30 min", "compound_quantity"),
    ("5 ft 3 in", "compound_quantity"),
    ("", "empty"),
    ("   ", "empty"),
    ("banana", "not_a_number"),
    ("The answer is 42", "not_a_number"),
    ("−5", "not_a_number"),          # Unicode minus sign
    ("5 banana", "unknown_unit"),
    ("25 C", "ambiguous_unit"),           # pint reads bare C as coulomb
    ("5 B", "ambiguous_unit"),            # pint reads B as byte (dimensionless)
    ("10 mA/cm2", "unit_contains_number"),  # write cm^2
]


@pytest.mark.parametrize("text,reason", REFUSED_STRINGS)
def test_misreadable_strings_are_refused_with_named_reason(text, reason):
    with pytest.raises(UnitError) as exc:
        as_quantity(text)
    assert exc.value.reason == reason, str(exc.value)
    assert reason in str(exc.value)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_are_refused_in_every_form(bad):
    with pytest.raises(UnitError, match="non_finite"):
        as_quantity(bad)
    with pytest.raises(UnitError, match="non_finite"):
        as_quantity(bad, "V")
    with pytest.raises(UnitError, match="non_finite"):
        as_quantity({"value": bad, "unit": "V"})
    with pytest.raises(UnitError, match="non_finite"):
        parse_number(bad)


@pytest.mark.parametrize("value", [True, False, None, [1], {"value": 1}])
def test_non_numbers_are_refused(value):
    with pytest.raises(UnitError):
        as_quantity(value)


def test_unit_inside_the_value_and_beside_it_is_refused():
    with pytest.raises(UnitError, match="unit_given_twice"):
        as_quantity("350 degC", "degC")
    with pytest.raises(UnitError, match="unit_given_twice"):
        as_quantity({"value": "350 degC", "unit": "degC"})


def test_mapping_value_must_be_a_plain_number():
    with pytest.raises(UnitError, match="space_separated_digits"):
        as_quantity({"value": "1 200", "unit": "degC"})
    with pytest.raises(UnitError, match="not_a_quantity"):
        as_quantity({"value": True, "unit": "degC"})
    with pytest.raises(UnitError, match="unit_contains_number"):
        as_quantity({"value": 5, "unit": "200 degC"})
    with pytest.raises(UnitError, match="missing_unit"):
        as_quantity({"value": 5})


@pytest.mark.parametrize("unit", ["", "  ", None])
def test_empty_unit_is_refused(unit):
    with pytest.raises(UnitError, match="missing_unit"):
        parse_unit(unit)


@pytest.mark.parametrize("unit,reason", [
    ("banana", "unknown_unit"),
    ("C", "ambiguous_unit"),
    ("F", "ambiguous_unit"),
    ("k", "ambiguous_unit"),
    ("cm2", "unit_contains_number"),
    ("1/s", "unit_contains_number"),
])
def test_bad_units_are_refused(unit, reason):
    with pytest.raises(UnitError) as exc:
        parse_unit(unit)
    assert exc.value.reason == reason


@pytest.mark.parametrize("text,unit,expected", [
    ("42", None, 42.0),
    ("3.14", None, 3.14),
    ("42.", None, 42.0),
    (".5 mL", "milliliter", 0.5),
    ("1.2e-3", None, 0.0012),
    ("1.2E-3 V", "volt", 0.0012),
    ("7e2 degC", "degree_Celsius", 700.0),
    ("350 degC", "degree_Celsius", 350.0),
    ("350degC", "degree_Celsius", 350.0),
    ("-0.5 V", "volt", -0.5),
    ("+5 V", "volt", 5.0),
    ("5 K", "kelvin", 5.0),               # spaced: an explicit unit, not a scale suffix
    ("10 mA/cm^2", "milliampere / centimeter ** 2", 10.0),
    ("10 mA cm^-2", "milliampere / centimeter ** 2", 10.0),
    ("1 cm**3", "centimeter ** 3", 1.0),
    ("90 %", "percent", 90.0),
    ("0.5 mol/L", "mole / liter", 0.5),
])
def test_well_formed_strings_still_parse(text, unit, expected):
    q = as_quantity(text)
    assert math.isclose(q.magnitude, expected, rel_tol=1e-12)
    assert str(q.units) == (unit or "dimensionless")


def test_number_with_separate_unit():
    q = as_quantity(330, "mV")
    assert q.magnitude == 330 and str(q.units) == "millivolt"
    q = as_quantity("330", "mV")
    assert q.magnitude == 330.0


def test_conversion_and_dimension_mismatch():
    assert math.isclose(convert(as_quantity("330 mV"), "V"), 0.33)
    assert math.isclose(convert(as_quantity("900 kelvin"), "degC"), 626.85)
    assert math.isclose(convert(as_quantity("90 %"), "dimensionless"), 0.9)
    with pytest.raises(UnitError, match="dimension_mismatch"):
        convert(as_quantity("300 mA"), "V")


def test_differences_in_offset_units_convert_as_differences():
    # a 1 degC difference is a 1 kelvin difference, not 274.15 kelvin
    assert math.isclose(convert_difference(1.0, "degC", "kelvin"), 1.0)
    assert math.isclose(convert_difference(5.0, "mV", "V"), 0.005)
    assert is_offset_unit("degC") and not is_offset_unit("kelvin") and not is_offset_unit("V")


def test_parse_number_is_strict():
    assert parse_number("12.5") == 12.5
    assert parse_number(3) == 3.0
    for bad, reason in [("12 V", "unit_in_number"), ("1,5", "ambiguous_separator"),
                        ("", "empty"), ("n/a", "not_a_number"), ("nan", "non_finite")]:
        with pytest.raises(UnitError) as exc:
            parse_number(bad)
        assert exc.value.reason == reason
