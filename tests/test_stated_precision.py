"""Gap 4 (WP5 feedback on 0.1.0): "0.777" against 0.776943 was `disagree` unless a
tolerance was given by hand. A value written with k decimal places now carries an
implied half-unit in its last place (0.777 means 0.7765 to 0.7775), unless it has a
stated uncertainty or --exact is given. Integers and mantissas without a decimal point
are exact. The precision used is shown in the output and recorded in the receipt."""

from __future__ import annotations

import json

import pytest

from consilience import compare, verify
from consilience.cli import main
from consilience.compare import InputError, read_json
from consilience.units import implied_half_unit


@pytest.mark.parametrize("text,half", [
    ("0.777", 0.0005), ("-0.777", 0.0005), ("+0.30", 0.005), ("1.50", 0.005),
    ("5.", 0.5), (".5", 0.05), ("1200.", 0.5), ("1200.0", 0.05),
    ("1.2e3", 50.0), ("1.23e-5", 5e-8), ("1.0E-6", 5e-8), ("6.02e+23", 5e20),
])
def test_implied_half_unit(text, half):
    assert implied_half_unit(text) == pytest.approx(half, rel=1e-12)


@pytest.mark.parametrize("text", ["1200", "17", "-3", "1e-6", "5E3", "0"])
def test_no_decimal_point_is_exact(text):
    assert implied_half_unit(text) == 0.0


def m(value, unit="dimensionless", **kw):
    return dict({"value": value, "unit": unit}, **kw)


def test_the_wp5_case_agrees_by_default():
    r = compare(m("0.777"), m(0.776943))
    assert r.verdict == "agree" and r.exit_code == 0
    p = r.receipt["result"]["precision"]
    assert p["mode"] == "stated"
    assert p["a"] == {"written": "0.777", "implied": 0.0005,
                      "rule": "3 decimal places"}
    assert p["b"]["implied"] == 0.0
    assert p["implied"] == pytest.approx(0.0005)
    assert r.receipt["options"]["precision"] == "stated"


def test_exact_turns_it_off():
    r = compare(m("0.777"), m(0.776943), precision="exact")
    assert r.verdict == "disagree"
    assert r.receipt["result"]["precision"] == {"mode": "exact", "implied": 0.0}
    assert r.receipt["options"]["precision"] == "exact"


def test_bad_precision_option():
    with pytest.raises(InputError):
        compare(m("1.0"), m("1.0"), precision="loose")


def test_both_sides_rounded():
    assert compare(m("0.78"), m("0.7849")).verdict == "agree"      # 0.005 + 0.00005
    assert compare(m("0.78"), m("0.7856")).verdict == "disagree"
    assert compare(m("1.2e-5"), m("1.24e-5")).verdict == "agree"    # sci notation
    assert compare(m("1.2e-5"), m("1.26e-5")).verdict == "disagree"


def test_integers_are_exact():
    assert compare(m("1200"), m("1201")).verdict == "disagree"
    assert compare(m("1200."), m("1200.4")).verdict == "agree"
    assert compare(m(1200), m(1201)).verdict == "disagree"
    assert compare(m("1e3"), m("1001")).verdict == "disagree"
    assert compare(m("1.0e3"), m("1040")).verdict == "agree"


def test_stated_uncertainty_replaces_implied_precision():
    r = compare(m("0.777", uncertainty="0.0001"), m(0.7765))
    assert r.receipt["result"]["precision"]["a"]["implied"] == 0.0
    assert r.receipt["result"]["precision"]["a"]["rule"] == "uncertainty stated"
    assert r.verdict == "disagree"


def test_implied_precision_is_converted_between_units():
    r = compare(m("0.32", "V"), m("324 mV", None))
    assert r.verdict == "agree"           # 0.32 V means 0.315 to 0.325 V
    assert r.receipt["result"]["precision"]["a"]["implied"] == pytest.approx(0.005)
    r = compare(m("324 mV", None), m("0.32", "V"))
    assert r.receipt["result"]["precision"]["b"]["implied"] == pytest.approx(5.0)
    assert r.verdict == "agree"


def test_implied_precision_also_widens_the_floor():
    r = compare(m("0.70"), m("0.7149"), floor="0.01")
    assert r.verdict == "within_floor"


def test_a_python_float_is_exact():
    r = compare(m(0.777), m(0.776943))
    assert r.verdict == "disagree"
    assert r.receipt["result"]["precision"]["a"]["rule"].startswith("a number with no")


def test_a_json_number_keeps_its_written_digits(tmp_path):
    (tmp_path / "a.json").write_text('{"value": 1.50, "unit": "V"}', encoding="utf-8")
    (tmp_path / "b.json").write_text('{"value": 1.504, "unit": "V"}', encoding="utf-8")
    (tmp_path / "c.json").write_text('{"value": 1.46, "unit": "V"}', encoding="utf-8")
    assert read_json(tmp_path / "a.json")["value"].text == "1.50"
    r = compare(tmp_path / "a.json", tmp_path / "b.json")
    assert r.verdict == "agree"
    assert r.receipt["result"]["precision"]["a"]["written"] == "1.50"
    assert compare(tmp_path / "a.json", tmp_path / "c.json").verdict == "disagree"
    # the receipt writes 1.5 (JSON drops the trailing zero) but records "1.50"
    path = tmp_path / "r.json"
    path.write_text(json.dumps(r.receipt), encoding="utf-8")
    assert '"value": 1.5,' in path.read_text()
    v = verify(path)
    assert v.ok, v.steps


def test_new_receipts_verify():
    for kw in ({}, {"precision": "exact"}):
        r = compare(m("0.777"), m(0.776943), **kw)
        assert verify(r.receipt).ok


def test_old_receipt_keeps_its_old_verdict():
    from conftest import ROOT
    p = ROOT / "tests" / "fixtures" / "receipts-0.1.0" / "compare-precision.json"
    rec = json.loads(p.read_text())
    assert rec["result"]["verdict"] == "disagree" and "precision" not in rec["options"]
    assert verify(p).ok
    # the same inputs under 0.1.1 rules agree
    assert compare(rec["inputs"]["a"], rec["inputs"]["b"]).verdict == "agree"


def test_cli_shows_and_records_precision(tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text('{"value": "0.777", "unit": "1"}', encoding="utf-8")
    b.write_text('{"value": 0.776943, "unit": "1"}', encoding="utf-8")
    assert main(["compare", str(a), str(b)]) == 0
    out = capsys.readouterr().out
    assert "precision:" in out and "±0.0005" in out and "stated precision" in out
    assert main(["compare", str(a), str(b), "--exact"]) == 1
    out = capsys.readouterr().out
    assert "precision:  exact (--exact)" in out
