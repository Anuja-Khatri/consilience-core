"""Gap 1 (WP5 feedback on 0.1.0): the unit "1" was refused; it is the SI way of writing
"dimensionless" and is now read as exactly that. No other digit is allowed in a unit."""

from __future__ import annotations

import pytest

from consilience import compare
from consilience.units import UnitError, as_quantity, parse_unit, unit_text


def test_one_is_dimensionless():
    assert parse_unit("1") == parse_unit("dimensionless")
    assert parse_unit(" 1 ") == parse_unit("dimensionless")
    assert unit_text("1") == "dimensionless"
    assert as_quantity("0.5", "1").magnitude == 0.5


@pytest.mark.parametrize("unit", ["1/s", "10", "2", "1 m", "m^1.5", "11", "1.0", "01"])
def test_other_digits_still_refused(unit):
    with pytest.raises(UnitError) as e:
        parse_unit(unit)
    assert e.value.reason in ("unit_contains_number", "unknown_unit")


def test_compare_with_unit_one():
    a = {"value": 0.5, "unit": "1"}
    assert compare(a, {"value": 0.5, "unit": "dimensionless"}).verdict == "agree"
    assert compare(a, {"value": "50 %"}).verdict == "agree"
    assert compare(a, {"value": 0.6, "unit": "1"}).verdict == "disagree"
    r = compare(a, {"value": "0.5 V"})
    assert r.label == "not_comparable(unit)"


def test_unit_one_in_a_rule_file(tmp_path):
    from consilience import check
    (tmp_path / "d.csv").write_text("x\n0.4\n1.2\n", encoding="utf-8")
    (tmp_path / "r.yaml").write_text(
        "kind: check-rules\nname: t\nversion: t-v1\nplain_english: t\n"
        "columns:\n  x: {unit: '1'}\n"
        "rules:\n  - {id: B, kind: bound, column: x, max: 1, plain_english: at most 1}\n",
        encoding="utf-8")
    c = check(tmp_path / "d.csv", tmp_path / "r.yaml")
    assert c.summary["violations"] == 1 and c.summary["unparseable_cells"] == 0


def test_receipt_with_unit_one_verifies():
    from consilience import verify
    r = compare({"value": 0.5, "unit": "1"}, {"value": 0.5, "unit": "dimensionless"})
    assert verify(r.receipt).ok


def test_0_1_0_rules_still_refuse_unit_one():
    from consilience.units import rules_of
    with rules_of("0.1.0"):
        with pytest.raises(UnitError) as e:
            parse_unit("1")
    assert e.value.reason == "unit_contains_number"
    assert parse_unit("1") == parse_unit("dimensionless")   # back to current rules
