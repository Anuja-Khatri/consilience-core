"""`compare`: two measurements, a closed set of verdicts, named refusals.

The refusal cases port the comparator findings of consilience-ledger WP1
(tests/test_input_hardening.py): NaN once returned `within_floor`; values on axes with
no canonical unit were compared as raw numbers ("90 %" against "0.9"); "1 200",
"3,14", "5M" and "(1,234)" were misread. Here each is refused or handled by units.
"""

from __future__ import annotations

import copy
import json

import pytest

from consilience.compare import InputError, compare
from consilience.rules import load_rules

PACK = "electrochemistry"
COND = {
    "electrolyte": {"identity": "H2SO4", "concentration": "0.5 mol/L"},
    "current_density": {"value": 10, "unit": "mA/cm^2", "normalization": "geometric"},
    "temperature": "25 degC",
    "ir_correction": True,
}


def m(value, unit="V", uncertainty=None, conditions=None, **extra):
    d = {"value": value, "unit": unit, "conditions": copy.deepcopy(COND if conditions is None
                                                                 else conditions)}
    if uncertainty is not None:
        d["uncertainty"] = uncertainty
    d.update(extra)
    return d


# ------------------------------------------------------------------ numeric verdicts
def test_identical_values_agree():
    r = compare(m(0.32), m(0.32))
    assert r.verdict == "agree" and r.label == "agree" and r.exit_code == 0


def test_units_are_converted_before_comparing():
    r = compare(m(0.32), m(320, "mV"))
    assert r.verdict == "agree"
    assert r.unit == "V" and r.difference == pytest.approx(0.0, abs=1e-12)


def test_difference_beyond_tolerance_disagrees():
    r = compare(m(0.32), m(0.331))
    assert r.verdict == "disagree" and r.exit_code == 1
    assert r.difference == pytest.approx(0.011)


def test_absolute_and_relative_tolerance():
    assert compare(m(0.32), m(0.331), abs_tol="15 mV").verdict == "agree"
    assert compare(m(0.32), m(0.331), abs_tol="5 mV").verdict == "disagree"
    assert compare(m(100.0, "mV"), m(104.0, "mV"), rel_tol=0.05).verdict == "agree"
    assert compare(m(100.0, "mV"), m(106.0, "mV"), rel_tol=0.05).verdict == "disagree"


def test_tolerance_exactly_at_the_difference_agrees_despite_rounding():
    # 0.331 - 0.32 is 0.011000000000000003 in floating point
    assert compare(m(0.32), m(0.331), abs_tol="11 mV").verdict == "agree"


def test_floor_and_uncertainty_give_within_floor():
    assert compare(m(0.32), m(0.331), floor="13 mV").verdict == "within_floor"
    r = compare(m(0.32, uncertainty="12 mV"), m(0.331))
    assert r.verdict == "within_floor" and r.exit_code == 0
    assert r.floor == pytest.approx(0.012)
    assert compare(m(0.32, uncertainty=0.004), m(0.331, uncertainty="3 mV")).verdict == "disagree"


def test_percent_and_fraction_compare_by_unit_not_raw_number():
    # ledger WP1: "90 %" against 0.9 was a fork of 89.1
    r = compare(m(90, "%"), m(0.9, "dimensionless"))
    assert r.verdict == "agree"


def test_temperature_difference_tolerance_is_a_difference():
    a = m(25.0, "degC", conditions={})
    b = m(298.65, "K", conditions={})
    assert compare(a, b, abs_tol="1 delta_degC").verdict == "agree"
    assert compare(a, b, abs_tol="1 K").verdict == "agree"
    with pytest.raises(InputError, match="rel"):
        compare(a, b, rel_tol=0.01)


# ------------------------------------------------------------------ refusals
@pytest.mark.parametrize("value,reason", [
    ("1 200", "space_separated_digits"),
    ("3,14", "ambiguous_separator"),
    ("1.2.3", "second_decimal_point"),
    ("(1,234)", "parenthesised_number"),
    ("5-10", "malformed_number"),
    ("nan", "non_finite"),
    (float("nan"), "non_finite"),
    (float("inf"), "non_finite"),
    ("-inf", "non_finite"),
    (True, "not_a_quantity"),
])
def test_unparseable_values_are_refused(value, reason):
    r = compare(m(value), m(0.32))
    assert r.verdict == "unparseable", r.to_dict()
    assert r.label == f"unparseable(a.value: {reason})"
    assert r.exit_code == 3


def test_nan_is_never_within_floor():
    r = compare(m(float("nan")), m(0.3), floor="1 V")
    assert r.verdict == "unparseable"


def test_unknown_and_ambiguous_units_are_refused():
    assert compare(m(0.3, "banana"), m(0.3)).label == "unparseable(a.unit: unknown_unit)"
    assert compare(m(25, "C"), m(25, "C")).label == "unparseable(a.unit: ambiguous_unit)"
    assert compare(m("5M", None), m(5, "mol/L")).label == \
        "unparseable(a.value: ambiguous_scale_suffix)"


def test_uncertainty_must_be_readable_and_not_negative():
    assert compare(m(0.3, uncertainty="nan"), m(0.3)).label == \
        "unparseable(a.uncertainty: non_finite)"
    assert compare(m(0.3, uncertainty=-0.01), m(0.3)).label == \
        "unparseable(a.uncertainty: negative)"
    assert compare(m(0.3, uncertainty="5 degC"), m(0.3)).label == \
        "unparseable(a.uncertainty: dimension_mismatch)"


def test_missing_value_or_unit_is_not_stated():
    a = m(0.3)
    del a["value"]
    assert compare(a, m(0.3)).label == "not_stated(a.value)"
    b = m(0.3)
    del b["unit"]
    r = compare(m(0.3), b)
    assert r.label == "not_stated(b.unit)" and r.exit_code == 2


def test_different_dimensions_are_not_comparable():
    r = compare(m(300, "mA"), m(0.4, "V"))
    assert r.verdict == "not_comparable" and r.label == "not_comparable(unit)"


def test_unit_given_twice_is_refused():
    r = compare(m("0.32 V", "V"), m(0.32))
    assert r.label == "unparseable(a.value: unit_given_twice)"


def test_unknown_measurement_field_is_an_input_error():
    with pytest.raises(InputError, match="uncertainity"):
        compare(m(0.3, uncertainity=0.01), m(0.3))


def test_bad_options_are_input_errors():
    with pytest.raises(InputError):
        compare(m(0.3), m(0.3), abs_tol="1,5 mV")
    with pytest.raises(InputError):
        compare(m(0.3), m(0.3), abs_tol="5 degC")
    with pytest.raises(InputError):
        compare(m(0.3), m(0.3), rel_tol="nan")
    with pytest.raises(InputError):
        compare(m(0.3), m(0.3), floor="-1 mV")


# ------------------------------------------------------------------ conditions, no pack
def test_without_a_pack_every_condition_must_match():
    b = copy.deepcopy(COND)
    b["temperature"] = "298.15 K"
    b["current_density"] = {"value": 0.01, "unit": "A/cm^2", "normalization": "geometric"}
    b["electrolyte"]["concentration"] = "500 mmol/L"
    assert compare(m(0.3), m(0.3, conditions=b)).verdict == "agree"


def test_without_a_pack_a_condition_on_one_side_only_is_not_stated():
    b = copy.deepcopy(COND)
    b["stirring"] = "400 rpm"
    r = compare(m(0.3), m(0.3, conditions=b))
    assert r.label == "not_stated(stirring)" and r.exit_code == 2


def test_without_a_pack_text_must_match_exactly():
    b = copy.deepcopy(COND)
    b["electrolyte"]["identity"] = "sulfuric acid"
    assert compare(m(0.3), m(0.3, conditions=b)).label == \
        "not_comparable(electrolyte.identity)"
    b["electrolyte"]["identity"] = "h2so4"     # case carries meaning: Co is not CO
    assert compare(m(0.3), m(0.3, conditions=b)).label == \
        "not_comparable(electrolyte.identity)"


def test_unstated_is_not_a_match():
    b = copy.deepcopy(COND)
    b["temperature"] = "unstated"
    assert compare(m(0.3), m(0.3, conditions=b)).label == "not_stated(temperature)"
    c = copy.deepcopy(COND)
    c["temperature"] = None
    assert compare(m(0.3, conditions=c), m(0.3, conditions=c)).label == \
        "not_stated(temperature)"


def test_unparseable_condition_is_refused_not_coerced():
    b = copy.deepcopy(COND)
    b["temperature"] = "1 200 degC"
    assert compare(m(0.3), m(0.3, conditions=b)).label == \
        "unparseable(b.conditions.temperature: space_separated_digits)"
    b["temperature"] = "nan degC"
    assert compare(m(0.3), m(0.3, conditions=b)).label == \
        "unparseable(b.conditions.temperature: non_finite)"


def test_number_against_quantity_is_not_comparable():
    a = m(0.3, conditions={"ph": 7})
    b = m(0.3, conditions={"ph": "7 degC"})
    assert compare(a, b).label == "not_comparable(ph)"


# ------------------------------------------------------------------ conditions, pack
def test_pack_knows_spellings_and_units():
    b = {"electrolyte": {"identity": "Sulfuric acid", "concentration": "500 mmol/L"},
         "current_density": {"value": 0.01, "unit": "A/cm^2", "normalization": "geometric"},
         "temperature": "298.15 K", "ir_correction": True, "stirring": "400 rpm"}
    r = compare(m(0.32), m(0.32, conditions=b), pack=PACK)
    assert r.verdict == "agree"
    assert r.pack["name"] == "electrochemistry" and len(r.pack["sha256"]) == 64
    assert r.conditions["ignored"] == ["stirring"]


def test_pack_names_the_condition_that_differs():
    b = copy.deepcopy(COND)
    b["current_density"]["value"] = 100
    r = compare(m(0.32), m(0.41, conditions=b), pack=PACK)
    assert r.label == "not_comparable(current_density)"
    assert r.defects[0]["rule"] == "EC2"


def test_pack_normalisation_must_be_stated_and_equal():
    b = copy.deepcopy(COND)
    b["current_density"]["normalization"] = "ecsa"
    assert compare(m(0.3), m(0.3, conditions=b), pack=PACK).label == \
        "not_comparable(current_density.normalization)"
    del b["current_density"]["normalization"]
    assert compare(m(0.3), m(0.3, conditions=b), pack=PACK).label == \
        "not_stated(current_density.normalization)"


def test_pack_unstated_conditions_are_named():
    b = copy.deepcopy(COND)
    del b["temperature"]
    b["electrolyte"] = {"identity": "H2SO4"}
    r = compare(m(0.3), m(0.3, conditions=b), pack=PACK)
    assert r.verdict == "not_stated"
    assert {d["target"] for d in r.defects} == {"temperature", "electrolyte.concentration"}


def test_pack_room_temperature_matches_only_itself():
    a = copy.deepcopy(COND)
    a["temperature"] = "room_temperature"
    assert compare(m(0.3, conditions=a), m(0.3, conditions=a), pack=PACK).verdict == "agree"
    assert compare(m(0.3, conditions=a), m(0.3), pack=PACK).label == \
        "not_comparable(temperature)"


def test_pack_iR_correction():
    b = copy.deepcopy(COND)
    b["ir_correction"] = False
    assert compare(m(0.3), m(0.3, conditions=b), pack=PACK).label == \
        "not_comparable(ir_correction)"


def test_mismatch_outranks_not_stated_and_unparseable_outranks_both():
    b = copy.deepcopy(COND)
    b["ir_correction"] = False
    del b["temperature"]
    r = compare(m(0.3), m(0.3, conditions=b), pack=PACK)
    assert r.verdict == "not_comparable"
    r = compare(m("1,5"), m(0.3, conditions=b), pack=PACK)
    assert r.verdict == "unparseable"
    assert len(r.defects) == 3


# ------------------------------------------------------------------ receipts
def test_result_carries_a_receipt_with_hash():
    r = compare(m(0.32), m(0.331), pack=PACK)
    rec = r.receipt
    assert rec["receipt"] == "consilience-receipt/v1" and rec["command"] == "compare"
    assert len(rec["sha256"]) == 64
    assert rec["pack"]["sha256"] == load_rules(PACK).sha256
    json.dumps(rec, allow_nan=False)


def test_receipt_is_deterministic_and_argument_order_is_kept():
    r1 = compare(m(0.32), m(0.331))
    r2 = compare(m(0.32), m(0.331))
    assert r1.receipt["sha256"] == r2.receipt["sha256"]
    assert compare(m(0.331), m(0.32)).receipt["sha256"] != r1.receipt["sha256"]


def test_nan_input_still_gives_a_json_safe_receipt():
    r = compare(m(float("nan")), m(0.3))
    json.dumps(r.receipt, allow_nan=False)


def test_uncertainty_of_b_is_converted_to_the_unit_of_a():
    # found in the quickstart: b in mV with "3 mV" uncertainty was used as 3 V
    r = compare(m(0.32, uncertainty="4 mV"), m(331, "mV", uncertainty="3 mV"))
    assert r.floor == pytest.approx(0.004)
    assert r.verdict == "disagree"
    r = compare(m(0.32), m(331, "mV", uncertainty=12))   # bare number: b's own unit (mV)
    assert r.floor == pytest.approx(0.012) and r.verdict == "within_floor"
