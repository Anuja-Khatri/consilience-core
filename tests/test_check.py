"""`check`: a table against a rule file. Every violating row is reported with the rule,
the value, the limit and a row receipt; every cell that cannot be read is reported and
counted, never skipped. All data here is made up."""

from __future__ import annotations

import json
import textwrap

import pytest

from consilience.check import InputError, check
from consilience.hashing import sha256_json
from consilience.rules import RuleFileError, load_rules

RULES = textwrap.dedent("""\
    kind: check-rules
    name: test-rules
    version: test-rules-v1
    plain_english: Made-up rules for tests.
    id_column: id
    columns:
      reading: {unit_column: reading_unit}
      limit_v: {unit: V}
      temp_c: {unit: degC}
      share_pct: {unit: percent}
    rules:
      - id: R1
        kind: limit
        column: reading
        limit_column: limit_v
        must_be: at_most
        margin: 0.02 V
        plain_english: A reading must not exceed its own recorded limit by more than 0.02 V.
      - id: R2
        kind: bound
        column: temp_c
        min: 0 K
        plain_english: No temperature below absolute zero.
      - id: R3
        kind: bound
        column: share_pct
        min: 0
        max: 100
        plain_english: A percentage share lies between 0 and 100.
    """)


def write(tmp_path, rows, rules=RULES, header="id,reading,reading_unit,limit_v,temp_c,share_pct"):
    d = tmp_path / "data.csv"
    d.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    r = tmp_path / "rules.yaml"
    r.write_text(rules, encoding="utf-8")
    return d, r


OK = "x,1.0,V,2.0,20,50"


def test_clean_table_exits_zero(tmp_path):
    d, r = write(tmp_path, [OK, "y,500,mV,0.6,21.5,0"])
    res = check(d, r)
    assert res.exit_code == 0
    assert res.summary["violations"] == 0 and res.summary["unparseable_cells"] == 0
    assert res.summary["rows"] == 2


def test_violations_are_reported_with_rule_value_limit_and_receipt(tmp_path):
    d, r = write(tmp_path, [OK, "hot,2.71,V,2.50,20,50", "mv,850,mV,0.80,20,50",
                            "cold,1.0,V,2.0,-280,50", "pct,1.0,V,2.0,20,104"])
    res = check(d, r)
    assert res.exit_code == 1
    by = {(v["id"], v["rule"]) for v in res.violations}
    assert by == {("hot", "R1"), ("mv", "R1"), ("cold", "R2"), ("pct", "R3")}
    v = next(v for v in res.violations if v["id"] == "mv")
    assert v["value"] == "850" and v["unit"] == "mV"
    assert v["limit"] == pytest.approx(800.0) and v["limit_unit"] == "mV"
    assert v["line"] == 4 and len(v["row_sha256"]) == 64
    cold = next(v for v in res.violations if v["id"] == "cold")
    assert cold["limit"] == pytest.approx(-273.15) and cold["bound"] == "min"


def test_within_margin_and_at_the_bound_pass(tmp_path):
    d, r = write(tmp_path, ["a,0.82,V,0.80,20,100", "b,820,mV,0.80,-273.15,0"])
    assert check(d, r).exit_code == 0


def test_row_receipt_is_the_documented_hash(tmp_path):
    d, r = write(tmp_path, ["hot,2.71,V,2.50,20,50"])
    res = check(d, r)
    v = res.violations[0]
    rules = load_rules(r)
    cells = {"id": "hot", "reading": "2.71", "reading_unit": "V", "limit_v": "2.50",
             "temp_c": "20", "share_pct": "50"}
    assert v["row_sha256"] == sha256_json({"rules_sha256": rules.sha256, "rule": "R1",
                                           "line": 2, "cells": cells})


# ---------------------------------------------------------------- refusals
@pytest.mark.parametrize("cell,reason", [
    ("1 200", "space_separated_digits"),
    ("3,14", "ambiguous_separator"),
    ("1.2.3", "second_decimal_point"),
    ("nan", "non_finite"),
    ("NaN", "non_finite"),
    ("inf", "non_finite"),
    ("-Infinity", "non_finite"),
    ("1e400", "non_finite"),
    ("n/a", "not_a_number"),
    ("(5)", "parenthesised_number"),
    ("5-10", "malformed_number"),
    ("12 degC", "unit_in_number"),
    ("", "empty"),
    ("   ", "empty"),
])
def test_unreadable_cells_are_reported_and_counted(tmp_path, cell, reason):
    d, r = write(tmp_path, [OK, f'bad,1.0,V,2.0,"{cell}",50'])
    res = check(d, r)
    assert res.exit_code == 3
    assert res.summary["unparseable_cells"] == 1
    u = res.unparseable[0]
    assert (u["id"], u["column"], u["reason"], u["rules"]) == ("bad", "temp_c", reason, ["R2"])
    assert u["text"] == cell


@pytest.mark.parametrize("unit,reason", [
    ("C", "ambiguous_unit"), ("banana", "unknown_unit"), ("", "missing_unit"),
    ("mA", "dimension_mismatch"),
])
def test_bad_row_units_are_refused(tmp_path, unit, reason):
    d, r = write(tmp_path, [f"u,1.0,{unit},2.0,20,50"])
    res = check(d, r)
    assert res.exit_code == 3
    u = res.unparseable[0]
    assert u["column"] == "reading_unit" and u["reason"] == reason


def test_unparseable_takes_precedence_over_violations_in_the_exit_code(tmp_path):
    d, r = write(tmp_path, ["hot,2.71,V,2.50,20,50", "bad,1.0,V,n/a,20,50"])
    res = check(d, r)
    assert res.summary["violations"] == 1 and res.summary["unparseable_cells"] == 1
    assert res.exit_code == 3


def test_a_cell_needed_by_two_rules_is_counted_once(tmp_path):
    rules = RULES + (
        "  - id: R4\n"
        "    kind: bound\n"
        "    column: temp_c\n"
        "    max: 100 degC\n"
        "    plain_english: Below boiling.\n")
    d, r = write(tmp_path, ["bad,1.0,V,2.0,n/a,50"], rules=rules)
    res = check(d, r)
    assert res.summary["unparseable_cells"] == 1
    assert res.unparseable[0]["rules"] == ["R2", "R4"]


def test_rows_of_the_wrong_length_are_refused_whole(tmp_path):
    d, r = write(tmp_path, [OK, "short,1.0,V", "long,1.0,V,2.0,20,50,99"])
    res = check(d, r)
    assert res.summary["unparseable_cells"] == 2
    assert {u["reason"] for u in res.unparseable} == {"row_length"}
    assert res.exit_code == 3


def test_blank_lines_are_counted_not_hidden(tmp_path):
    d, r = write(tmp_path, [OK, "", OK])
    res = check(d, r)
    assert res.summary["rows"] == 2 and res.summary["blank_lines"] == 1


def test_skip_empty_is_explicit_and_counted(tmp_path):
    rules = RULES.replace("    min: 0 K\n", "    min: 0 K\n    if_empty: skip\n")
    d, r = write(tmp_path, ["e,1.0,V,2.0,,50"], rules=rules)
    res = check(d, r)
    assert res.exit_code == 0
    assert res.summary["skipped_empty"] == 1 and res.summary["by_rule"]["R2"]["skipped"] == 1


def test_missing_limit_can_fall_back_to_a_stated_limit(tmp_path):
    rules = RULES.replace("    must_be: at_most\n",
                          "    must_be: at_most\n    if_limit_empty: 1.5 V\n")
    d, r = write(tmp_path, ["f,1.6,V,,20,50", "g,1.4,V,,20,50"], rules=rules)
    res = check(d, r)
    assert [v["id"] for v in res.violations] == ["f"]
    assert res.violations[0]["route"] == "fallback_limit"


def test_at_least_and_exclusive_bounds(tmp_path):
    rules = textwrap.dedent("""\
        kind: check-rules
        name: t
        version: t-v1
        plain_english: Made-up.
        columns:
          flow: {unit: mL/min}
          floor: {unit: L/min}
          ph: {unit: dimensionless}
        rules:
          - id: L1
            kind: limit
            column: flow
            limit_column: floor
            must_be: at_least
            plain_english: Flow at least the recorded floor.
          - id: B1
            kind: bound
            column: ph
            min: 0
            max: 14
            max_inclusive: false
            plain_english: pH below 14.
        """)
    d, r = write(tmp_path, ["900,1.0,7", "1000,1.0,14"], rules=rules, header="flow,floor,ph")
    res = check(d, r)
    assert [(v["line"], v["rule"]) for v in res.violations] == [(2, "L1"), (3, "B1")]


def test_missing_column_is_an_input_error(tmp_path):
    d, r = write(tmp_path, ["x,1.0,V,2.0,20"], header="id,reading,reading_unit,limit_v,temp_c")
    with pytest.raises(InputError, match="share_pct"):
        check(d, r)


def test_duplicate_header_is_an_input_error(tmp_path):
    d, r = write(tmp_path, ["x,1,V,2,20,50,1"],
                 header="id,reading,reading_unit,limit_v,temp_c,share_pct,temp_c")
    with pytest.raises(InputError, match="duplicate"):
        check(d, r)


def test_comment_lines_before_the_header_are_allowed(tmp_path):
    d = tmp_path / "data.csv"
    d.write_text("# made-up data\n# second note\nid,reading,reading_unit,limit_v,temp_c,"
                 "share_pct\nhot,2.71,V,2.50,20,50\n", encoding="utf-8")
    r = tmp_path / "rules.yaml"
    r.write_text(RULES, encoding="utf-8")
    res = check(d, r)
    assert res.violations[0]["line"] == 4


@pytest.mark.parametrize("mutation,match", [
    (("min: 0 K", "min: 0 banana"), "banana"),
    (("must_be: at_most", "must_be: below"), "must_be"),
    (("column: temp_c", "column: nope"), "nope"),
    (("    min: 0 K\n", "    min: 0 K\n    maximum: 3\n"), "maximum"),
    (("margin: 0.02 V", "margin: 1,5 V"), "ambiguous_separator"),
    (("margin: 0.02 V", "margin: 0.02"), "needs a unit"),
    (("kind: check-rules", "kind: checks"), "kind"),
])
def test_bad_rule_files_are_refused(tmp_path, mutation, match):
    d, r = write(tmp_path, [OK], rules=RULES.replace(*mutation))
    with pytest.raises(RuleFileError, match=match):
        check(d, r)


def test_receipt_and_html(tmp_path):
    d, r = write(tmp_path, ["<b>,2.71,V,2.50,20,50"])
    res = check(d, r)
    rec = res.receipt
    assert rec["command"] == "check" and len(rec["sha256"]) == 64
    assert rec["inputs"]["data"]["sha256"] and rec["rules"]["sha256"] == load_rules(r).sha256
    json.dumps(rec, allow_nan=False)
    html = res.to_html()
    assert "<b>" not in html and "&lt;b&gt;" in html
    assert "R1" in html and rec["sha256"] in html


def test_value_offset_is_added_before_comparing(tmp_path):
    rules = RULES.replace("    margin: 0.02 V\n", "    margin: 0.02 V\n    value_offset: 1.0 V\n")
    d, r = write(tmp_path, ["a,1.5,V,2.50,20,50", "b,1.6,V,2.50,20,50"], rules=rules)
    res = check(d, r)
    assert [v["id"] for v in res.violations] == ["b"]
    assert res.violations[0]["value_offset"] == pytest.approx(1.0)
    assert "margin 0.02 V, value offset 1 V" in res.to_html()
