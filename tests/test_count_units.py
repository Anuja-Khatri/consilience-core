"""Gap 2 (WP5 feedback on 0.1.0): count and ratio words such as "fold" and "cells" were
unknown units. A small, fixed set is now read; each is a dimensionless kind of its own,
so "3 fold" and "3 cells" are not comparable. Anything else still fails closed."""

from __future__ import annotations

import pytest

from consilience import check, compare, verify
from consilience.units import COUNT_UNITS, UnitError, as_quantity, convert, parse_unit, \
    rules_of


def test_the_set_is_small_and_explicit():
    assert COUNT_UNITS == ("fold", "cell", "event", "sample")


@pytest.mark.parametrize("word,base", [("fold", "fold"), ("folds", "fold"),
                                       ("cell", "cell"), ("cells", "cell"),
                                       ("event", "event"), ("events", "event"),
                                       ("sample", "sample"), ("samples", "sample")])
def test_words_and_plurals_are_read(word, base):
    assert parse_unit(word) == parse_unit(base)


def test_each_word_is_its_own_kind():
    kinds = [as_quantity(f"3 {w}").dimensionality for w in COUNT_UNITS]
    assert len(set(map(str, kinds))) == len(COUNT_UNITS)
    for w in COUNT_UNITS:
        with pytest.raises(UnitError) as e:
            convert(as_quantity(f"3 {w}"), "dimensionless")
        assert e.value.reason == "dimension_mismatch"


def test_compound_units_work():
    assert convert(as_quantity("2e6 cells/mL"), "cells/L") == pytest.approx(2e9)
    assert convert(as_quantity("120 events/min"), "events/s") == pytest.approx(2.0)


@pytest.mark.parametrize("unit", ["kcells", "kilocell", "millifold", "mfold", "Mcells",
                                  "Cells", "FOLD", "banana", "reads", "copies", "x"])
def test_prefixes_and_other_words_fail_closed(unit):
    with pytest.raises(UnitError) as e:
        parse_unit(unit)
    assert e.value.reason == "unknown_unit"


def test_count_stays_pint_dimensionless_as_in_0_1_0():
    # pint's own "count" was already accepted by 0.1.0 as a pure number; unchanged.
    assert convert(as_quantity("3 count"), "dimensionless") == 3


def test_compare_fold_and_cells():
    r = compare({"value": "3 fold"}, {"value": 3, "unit": "fold"})
    assert r.verdict == "agree"
    r = compare({"value": "3 fold"}, {"value": "3 cells"})
    assert r.label == "not_comparable(unit)" and r.exit_code == 2
    r = compare({"value": "12 cells"}, {"value": 12, "unit": "dimensionless"})
    assert r.label == "not_comparable(unit)"
    r = compare({"value": "12 cells"}, {"value": "13 cells"})
    assert r.verdict == "disagree"
    r = compare({"value": "3 kfold"}, {"value": "3 fold"})
    assert r.label == "unparseable(a.value: unknown_unit)"
    assert verify(compare({"value": "3 fold"}, {"value": "3 fold"}).receipt).ok


def test_0_1_0_rules_refuse_count_words():
    with rules_of("0.1.0"):
        for w in ("fold", "cells", "cells/mL"):
            with pytest.raises(UnitError) as e:
                parse_unit(w)
            assert e.value.reason == "unknown_unit"
            assert e.value.detail == "not a unit pint knows"


def test_count_units_in_a_check(tmp_path):
    (tmp_path / "d.csv").write_text("n,u\n4,cells\n9,cells\n2,fold\n", encoding="utf-8")
    (tmp_path / "r.yaml").write_text(
        "kind: check-rules\nname: t\nversion: t-v1\nplain_english: t\n"
        "columns:\n  n: {unit_column: u}\n"
        "rules:\n  - {id: B, kind: bound, column: n, max: 8 cells, plain_english: x}\n",
        encoding="utf-8")
    c = check(tmp_path / "d.csv", tmp_path / "r.yaml")
    assert c.summary["violations"] == 1
    assert [u["reason"] for u in c.unparseable] == ["dimension_mismatch"]
