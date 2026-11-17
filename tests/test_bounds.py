"""Gap 3 (WP5 feedback on 0.1.0): inequality values such as "<1e-6" or "≤ 0.30 V" were
unparseable. One-sided bounds (<, <=, ≤, >, >=, ≥) are now read in a measurement's value.

Value against bound: `agree` if the value satisfies the bound within the tolerance plus
the implied precision; `within_floor` if it does so only within the floor (which
includes the value's uncertainty) plus the implied precision; otherwise `disagree`.
Bound against bound: `undecidable_bounds` (exit 2) when both can hold, since there is no
single value to compare; `disagree` when they cannot both hold. Malformed bounds are
`unparseable`."""

from __future__ import annotations

import pytest

from consilience import compare, verify
from consilience.cli import main
from consilience.compare import EXIT
from consilience.units import UnitError, parse_bound, rules_of


@pytest.mark.parametrize("text,op,num,unit", [
    ("<1e-6", "<", "1e-6", None), ("< 1e-6", "<", "1e-6", None),
    ("<=0.3 V", "<=", "0.3", "V"), ("≤ 0.30 V", "<=", "0.30", "V"),
    ("≤0.30V", "<=", "0.30", "V"), (">5", ">", "5", None), (">= 5 mV", ">=", "5", "mV"),
    ("≥ 2.5 cells", ">=", "2.5", "cells"), ("< -3 degC", "<", "-3", "degC"),
    ("  <  10 %  ", "<", "10", "%"),
])
def test_parse_bound(text, op, num, unit):
    b = parse_bound(text)
    assert (b.op, b.number_text, b.unit) == (op, num, unit)


@pytest.mark.parametrize("text,reason", [
    ("<<1", "malformed_bound"), ("<", "malformed_bound"), ("< ", "malformed_bound"),
    ("<>1", "malformed_bound"), ("=<1", "malformed_bound"), ("=>1", "malformed_bound"),
    ("< =1", "malformed_bound"), ("≤≤ 0.3", "malformed_bound"), ("<= <1", "malformed_bound"),
    ("< nan", "non_finite"), ("<inf V", "non_finite"), ("< 1,5", "ambiguous_separator"),
    ("< 1 200", "space_separated_digits"), ("< 5M", "ambiguous_scale_suffix"),
    ("< 0.3 V < 0.4 V", "compound_quantity"), ("<1-2", "malformed_number"),
])
def test_malformed_bounds_are_refused(text, reason):
    with pytest.raises(UnitError) as e:
        parse_bound(text)
    assert e.value.reason == reason


def m(value, unit=None, **kw):
    d = {"value": value}
    if unit is not None:
        d["unit"] = unit
    d.update(kw)
    return d


def test_value_inside_an_upper_bound_agrees():
    r = compare(m("<1e-6", "dimensionless"), m(2e-7, "dimensionless"))
    assert r.verdict == "agree" and r.exit_code == 0
    res = r.receipt["result"]
    assert res["comparison"] == "value_vs_bound"
    assert res["a"]["bound"] == "<" and "bound" not in res["b"]
    assert res["difference"] == 0.0


def test_value_outside_an_upper_bound_disagrees():
    r = compare(m(2e-6, "dimensionless"), m("<1e-6", "dimensionless"))
    assert r.verdict == "disagree" and r.exit_code == 1
    assert r.difference == pytest.approx(1e-6)


def test_bounds_on_either_side_and_units_converted():
    assert compare(m("0.25 V"), m("< 300 mV")).verdict == "agree"
    assert compare(m("< 300 mV"), m("0.35 V")).verdict == "disagree"
    assert compare(m(">= 5 mV"), m("0.004 V"), precision="exact").verdict == "disagree"
    assert compare(m(">= 5 mV"), m("0.006 V")).verdict == "agree"


def test_strict_and_non_strict_at_the_threshold():
    assert compare(m("≤ 0.30 V"), m("0.30 V"), precision="exact").verdict == "agree"
    assert compare(m("< 0.30 V"), m("0.30 V"), precision="exact").verdict == "disagree"
    d = "dimensionless"
    assert compare(m("> 2", d), m(2.0, d), precision="exact").verdict == "disagree"
    assert compare(m(">= 2", d), m(2, d), precision="exact").verdict == "agree"


def test_stated_precision_and_tolerance_count():
    # 0.30 and 0.31 are both written to 2 places: +-0.005 each
    assert compare(m("≤ 0.30 V"), m("0.31 V")).verdict == "agree"
    assert compare(m("≤ 0.30 V"), m("0.31 V"), precision="exact").verdict == "disagree"
    assert compare(m("≤ 0.30 V"), m("0.32 V")).verdict == "disagree"
    assert compare(m("< 0.3 V"), m(0.32, "V"), abs_tol="25 mV",
                   precision="exact").verdict == "agree"
    assert compare(m("< 0.3 V"), m(0.32, "V"), abs_tol="15 mV",
                   precision="exact").verdict == "disagree"
    assert compare(m("< 100 mV"), m(102, "mV"), rel_tol=0.05).verdict == "agree"


def test_uncertainty_of_the_value_gives_within_floor():
    r = compare(m("< 0.30 V"), m(0.305, "V", uncertainty="10 mV"), precision="exact")
    assert r.verdict == "within_floor" and r.exit_code == 0
    r = compare(m("< 0.30 V"), m(0.32, "V", uncertainty="10 mV"), precision="exact")
    assert r.verdict == "disagree"
    assert compare(m("< 0.30 V"), m(0.305, "V"), floor="10 mV",
                   precision="exact").verdict == "within_floor"


def test_uncertainty_on_a_bound_is_refused():
    r = compare(m("< 0.30 V", uncertainty="1 mV"), m("0.2 V"))
    assert r.label == "unparseable(a.uncertainty: uncertainty_on_bound)"
    assert r.exit_code == 3


def test_bound_vs_bound():
    r = compare(m("<1e-6", "dimensionless"), m("<1e-5", "dimensionless"))
    assert r.verdict == "undecidable_bounds" and r.label == "undecidable_bounds"
    assert r.exit_code == EXIT["undecidable_bounds"] == 2
    assert r.receipt["result"]["comparison"] == "bounds"
    assert compare(m("> 1 V"), m("> 2 V")).verdict == "undecidable_bounds"
    assert compare(m("< 2 V"), m("> 1 V")).verdict == "undecidable_bounds"
    assert compare(m("<= 1 V"), m(">= 1 V"), precision="exact").verdict == \
        "undecidable_bounds"
    r = compare(m("< 1 V"), m("> 2 V"))
    assert r.verdict == "disagree" and r.difference == pytest.approx(1.0)
    assert compare(m("< 1 V"), m("> 1 V"), precision="exact").verdict == "disagree"
    assert compare(m("< 1 V"), m("> 1.5 V"), abs_tol="0.6 V").verdict == \
        "undecidable_bounds"
    assert compare(m("< 1 V"), m("> 1.5 V"), floor="0.6 V").verdict == \
        "undecidable_bounds"


def test_bounds_of_different_kinds_are_not_comparable():
    assert compare(m("< 1 V"), m("0.5 A")).label == "not_comparable(unit)"
    assert compare(m("< 3 fold"), m("2 cells")).label == "not_comparable(unit)"


def test_malformed_bound_in_compare():
    r = compare(m("<<1", "dimensionless"), m(0.5, "dimensionless"))
    assert r.label == "unparseable(a.value: malformed_bound)"
    assert compare(m("< nan"), m("1")).label == "unparseable(a.value: non_finite)"
    assert compare(m("<1 V", "V"), m("1 V")).label == "unparseable(a.value: unit_given_twice)"


def test_bound_receipts_verify():
    for a, b in ((m("<1e-6", "dimensionless"), m(2e-7, "dimensionless")),
                 (m("< 1 V"), m("> 2 V")), (m("< 1 V"), m("< 2 V"))):
        assert verify(compare(a, b).receipt).ok


def test_0_1_0_rules_do_not_read_bounds():
    with rules_of("0.1.0"):
        r = compare(m("<1e-6", "dimensionless"), m(2e-7, "dimensionless"))
    assert r.label == "unparseable(a.value: not_a_number)"


def test_cli_bound(tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text('{"value": "<1e-6", "unit": "1"}', encoding="utf-8")
    b.write_text('{"value": 2.3e-7, "unit": "1"}', encoding="utf-8")
    assert main(["compare", str(a), str(b)]) == 0
    out = capsys.readouterr().out
    assert "a:          < 1e-06 dimensionless" in out and "beyond:" in out
    b.write_text('{"value": "<1e-5", "unit": "1"}', encoding="utf-8")
    assert main(["compare", str(a), str(b)]) == 2
    out = capsys.readouterr().out
    assert out.startswith("verdict:    undecidable_bounds") and "can both hold" in out
