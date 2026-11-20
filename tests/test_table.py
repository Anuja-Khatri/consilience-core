"""compare-table: every rule of the product spec (sections 4-7), one test or more each."""

from __future__ import annotations

import json
import random

import pytest

from consilience import compare, load_rules, verify
from consilience.cli import main
from consilience.compare import InputError
from consilience.rules import RuleFileError, rules_from_dict
from consilience.table import compare_table


def rec(mol="M1", value="41", rel="=", unit="nM", stype="IC50", atype="B", **kw):
    r = dict(mol=mol, tgt="T1", value=value, relation=rel, unit=unit,
             standard_type=stype, assay_type=atype)
    r.update(kw)
    return r


def by_row(res):
    return {r["row"]: r for r in res.records}


# ------------------------------------------------------------------ input rules
def test_csv_cells_are_text_and_keep_written_digits(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("mol,tgt,value,unit\nM1,T1,0.30,uM\nM1,T1,300,nM\n", encoding="utf-8")
    r = compare_table(p, key="mol,tgt", log_tol=0.0)
    # "0.30" carries an implied half-unit of 0.005 uM, so 300 nM agrees even at log_tol 0
    assert r.pairs[0]["verdict"] == "agree"


def test_empty_nan_and_blank_cells_are_not_stated():
    rows = [rec(value="5", assay_type=None), rec(value="6", assay_type="  "),
            rec(value="7", assay_type=float("nan"))]
    r = compare_table(rows, key="mol,tgt", pack="bioactivity")
    # all three have assay_type empty; BA2 has absent_on_both: equal -> one class
    assert {x["condition_class"] for x in r.records} == {"C1"}
    assert r.summary["record_status"] == {"usable": 3}


def test_nan_value_is_not_stated_not_unparseable():
    r = compare_table([rec(value=float("nan")), rec(value="5")], key="mol,tgt",
                      pack="bioactivity")
    assert by_row(r)[1]["record_status"] == "excluded(BR4: not stated)"
    assert r.exit_code == 0


def test_missing_column_means_rule_not_applied_and_said_so():
    r = compare_table([rec()], key="mol,tgt", pack="bioactivity")
    na = r.summary["not_checked_column_absent"]
    assert "BR2" in na["record_rules"] and "BA10" in na["conditions"]
    assert "Not checked (column absent from the table)" in r.text


def test_no_value_column_is_an_input_error():
    with pytest.raises(InputError, match="no value column"):
        compare_table([{"mol": "M1", "tgt": "T1", "x": "1"}], key="mol,tgt")


def test_key_required_and_key_column_must_exist():
    with pytest.raises(InputError, match="give --key"):
        compare_table([rec()])
    with pytest.raises(InputError, match="key column"):
        compare_table([rec()], key="mol,nope")


def test_key_not_stated_excludes_the_record():
    r = compare_table([rec(mol=None), rec()], key="mol,tgt")
    assert by_row(r)[1]["record_status"].startswith("excluded(key: mol not stated")


def test_chembl_api_json_shape_and_lookups(tmp_path):
    p = tmp_path / "act.json"
    p.write_text(json.dumps({"activities": [
        {"activity_id": 1, "parent_molecule_chembl_id": "CHEMBL1", "target_chembl_id": "CHEMBL203",
         "standard_value": "41.0", "standard_relation": "=", "standard_units": "nM",
         "standard_type": "IC50", "assay_variant_mutation": "UNDEFINED MUTATION"},
        {"activity_id": 2, "parent_molecule_chembl_id": "CHEMBL1", "target_chembl_id": "CHEMBL203",
         "standard_value": "40.0", "standard_relation": "=", "standard_units": "nM",
         "standard_type": "IC50", "assay_variant_mutation": "UNDEFINED MUTATION"},
    ], "page_meta": {"total_count": 2}}), encoding="utf-8")
    r = compare_table(p, map="chembl", pack="bioactivity")
    # an undefined mutation is unknown: never pooled, not even with another undefined one
    assert all(not x["pool_valid"] for x in r.records)
    assert by_row(r)[1]["pool_reason"] == "condition_not_stated(assay_variant_mutation)"
    assert r.pairs[0]["verdict"] == "not_stated"


def test_chembl_unit_notation_is_translated():
    rows = [{"parent_molecule_chembl_id": "M", "target_chembl_id": "T", "standard_value": "2",
             "standard_relation": "=", "standard_units": "ug.mL-1", "standard_type": "IC50"},
            {"parent_molecule_chembl_id": "M", "target_chembl_id": "T", "standard_value": "5",
             "standard_relation": "=", "standard_units": "nM", "standard_type": "IC50"}]
    r = compare_table(rows, map="chembl", pack="bioactivity")
    # mass concentration and molar concentration: different classes, named reason
    assert r.pairs[0]["label"] == "not_comparable(unit)"
    assert r.summary["record_status"] == {"usable": 2}


def test_jsonl_and_parquet_inputs(tmp_path):
    rows = [rec(value="41"), rec(value="50")]
    jl = tmp_path / "t.jsonl"
    jl.write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
    assert compare_table(jl, key="mol,tgt").pairs[0]["verdict"] in ("agree", "disagree")
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq
    pq.write_table(pa.Table.from_pylist(rows), tmp_path / "t.parquet")
    r = compare_table(tmp_path / "t.parquet", key="mol,tgt", log_tol=0.3)
    assert r.pairs[0]["verdict"] == "agree"


def test_csv_with_wrong_cell_count_is_refused(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("mol,tgt,value,unit\nM1,T1,1\n", encoding="utf-8")
    with pytest.raises(InputError, match="cells for"):
        compare_table(p, key="mol,tgt")


# --------------------------------------------------------------- pack options
def test_absent_on_both_in_compare_itself():
    pack = load_rules("bioactivity")
    a = {"value": "41", "unit": "nM", "conditions": {"standard_type": "IC50"}}
    b = {"value": "45", "unit": "nM", "conditions": {"standard_type": "IC50"}}
    assert compare(a, b, pack=pack).verdict == "agree"
    b2 = dict(b, conditions={"standard_type": "IC50", "assay_type": "B"})
    assert compare(a, b2, pack=pack).label == "not_stated(assay_type)"
    a3 = dict(a, conditions={"standard_type": "IC50", "assay_type": "unstated"})
    b3 = dict(b, conditions={"standard_type": "IC50", "assay_type": "unstated"})
    assert compare(a3, b3, pack=pack).label == "not_stated(assay_type)"


def test_old_packs_hash_unchanged():
    # the electrochemistry pack must hash as it did in 0.1.0/0.1.1 receipts
    assert load_rules("electrochemistry").sha256 == \
        "cbf7aea81b7f7eb070538e6049b2b2bd4ebcb00ae409c9ecfde9737d3ef1f97c"


@pytest.mark.parametrize("bad, msg", [
    ({"absent_on_both": "yes"}, "absent_on_both"),
])
def test_pack_option_validation(bad, msg):
    pack = {"kind": "compare-pack", "name": "x", "version": "x1", "plain_english": "x",
            "conditions": [dict({"id": "C1", "field": "f", "predicate": "equal",
                                 "plain_english": "x"}, **bad)]}
    with pytest.raises(RuleFileError, match=msg):
        rules_from_dict(pack)


def _pack(**extra):
    p = {"kind": "compare-pack", "name": "t", "version": "t1", "plain_english": "t",
         "conditions": [{"id": "C1", "field": "standard_type", "predicate": "equal",
                         "plain_english": "t"}]}
    p.update(extra)
    return rules_from_dict(p)


def test_record_rule_kinds_with_empty_cells():
    rr = [{"id": "E", "field": "warn", "kind": "empty", "plain_english": "x"},
          {"id": "P", "field": "value", "kind": "present", "plain_english": "x"},
          {"id": "I", "field": "flag", "kind": "in", "values": ["ok"], "plain_english": "x"},
          {"id": "IA", "field": "flag2", "kind": "in", "values": ["ok"], "allow_empty": True,
           "plain_english": "x"},
          {"id": "L", "field": "score", "kind": "at_least", "threshold": 9,
           "plain_english": "x"}]
    pk = _pack(record_rules=rr)
    base = dict(rec(), warn="", flag="ok", flag2="", score="9")
    rows = [base,
            dict(base, warn="bad"),               # E fails
            dict(base, flag=""),                  # I: empty -> not stated
            dict(base, flag2="other"),            # IA fails
            dict(base, score="8"),                # L fails
            dict(base, score=""),                 # L: not stated
            dict(base, score="high")]             # L: not a number
    r = compare_table(rows, key="mol,tgt", pack=pk)
    st = {x["row"]: x["record_status"] for x in r.records}
    assert st[1] == "usable"
    assert st[2] == "excluded(E: warn is bad)"
    assert st[3] == "excluded(I: not stated)"
    assert st[4] == "excluded(IA: flag2 is other)"
    assert st[5] == "excluded(L: score is 8)"
    assert st[6] == "excluded(L: not stated)"
    assert st[7] == "excluded(L: score is not a number: high)"


def test_bioactivity_br1_keeps_manually_validated():
    rows = [rec(data_validity_comment="Manually validated"),
            rec(data_validity_comment="Outside typical range"), rec(data_validity_comment="")]
    r = compare_table(rows, key="mol,tgt", pack="bioactivity")
    assert [x["record_status"].split("(")[0] for x in r.records] == ["usable", "excluded",
                                                                     "usable"]


def test_bioactivity_br3_relations():
    rows = [rec(rel="~"), rec(rel=None), rec(rel=">="), rec(rel=">>")]
    r = compare_table(rows, key="mol,tgt", pack="bioactivity")
    st = [x["record_status"] for x in r.records]
    assert st[0] == "excluded(BR3: relation is ~)"
    assert st[1] == "excluded(BR3: not stated)"
    assert st[2] == "bound"
    assert st[3] == "excluded(BR3: relation is >>)"


def test_assumption_requires_known_id_and_valid_definition():
    with pytest.raises(InputError, match="no such assumption"):
        compare_table([rec()], key="mol,tgt", pack="bioactivity", assume=["nope"])
    with pytest.raises(RuleFileError, match="not a condition"):
        _pack(assumptions=[{"id": "a", "condition": "zzz", "from": "Ki", "to": "IC50",
                            "factor": 2, "plain_english": "x"}])
    with pytest.raises(RuleFileError, match="positive"):
        _pack(assumptions=[{"id": "a", "condition": "standard_type", "from": "Ki",
                            "to": "IC50", "factor": 0, "plain_english": "x"}])


def test_defaults_validation():
    with pytest.raises(RuleFileError, match="cannot be mixed"):
        _pack(defaults={"log_tol": 0.3, "abs_tol": "1 nM", "plain_english": "x",
                        "source": "x"})


def test_tolerance_condition_refused_by_compare_table():
    pk = rules_from_dict({"kind": "compare-pack", "name": "t", "version": "t1",
                          "plain_english": "t",
                          "conditions": [{"id": "C1", "field": "temperature",
                                          "predicate": "quantity_equal",
                                          "tolerance": "1 K", "plain_english": "t"}]})
    with pytest.raises(InputError, match="exact-match"):
        compare_table([rec(temperature="25 degC")], key="mol,tgt", pack=pk)


# ----------------------------------------------------------- log-scale compare
def test_log_scale_compare_verdicts():
    a = {"value": "41", "unit": "nM"}
    assert compare(a, {"value": "80", "unit": "nM"}, log_tol=0.3, log_floor=1).verdict == "agree"
    assert compare(a, {"value": "300", "unit": "nM"}, log_tol=0.3,
                   log_floor=1).verdict == "within_floor"
    assert compare(a, {"value": "1", "unit": "uM"}, log_tol=0.3,
                   log_floor=1).verdict == "disagree"
    assert compare(a, {"value": "0", "unit": "nM"}, log_tol=0.3).label == \
        "unparseable(b.value: not_positive)"


def test_log_scale_bounds():
    a = {"value": "41", "unit": "nM"}
    assert compare(a, {"value": "< 1", "unit": "uM"}, log_tol=0.3).verdict == "agree"
    assert compare(a, {"value": "> 10", "unit": "uM"}, log_tol=0.3,
                   log_floor=1).verdict == "disagree"
    assert compare({"value": "> 1", "unit": "uM"}, {"value": "> 10", "unit": "uM"},
                   log_tol=0.3).verdict == "undecidable_bounds"
    assert compare({"value": "> 10", "unit": "uM"}, {"value": "< 1", "unit": "uM"},
                   log_tol=0.3, log_floor=0.5).verdict == "disagree"


def test_log_and_linear_options_cannot_mix():
    with pytest.raises(InputError, match="cannot be combined"):
        compare({"value": "1", "unit": "nM"}, {"value": "1", "unit": "nM"}, log_tol=0.3,
                abs_tol="1 nM")


def test_stated_precision_on_the_log_scale():
    # 0.3 uM written with one decimal: +-0.05 uM -> log10(1 + 0.05/0.3) = 0.067
    r = compare({"value": "300", "unit": "nM"}, {"value": "0.3", "unit": "uM"}, log_tol=0)
    assert r.verdict == "agree"
    r = compare({"value": "300", "unit": "nM"}, {"value": "0.36", "unit": "uM"}, log_tol=0.07)
    assert r.receipt["result"]["precision"]["scale"] == "log10"


def test_pack_defaults_are_used_and_recorded_and_verify(tmp_path):
    a = {"value": "41", "unit": "nM", "conditions": {"standard_type": "IC50"}}
    b = {"value": "300", "unit": "nM", "conditions": {"standard_type": "IC50"}}
    r = compare(a, b, pack="bioactivity")
    assert r.verdict == "within_floor"
    assert r.receipt["options"]["defaults_from_pack"] is True
    assert r.receipt["options"]["log_tol"] == 0.3
    p = tmp_path / "r.json"
    p.write_text(json.dumps(r.receipt), encoding="utf-8")
    assert verify(p).ok


def test_compare_receipt_shape_unchanged_without_new_options():
    r = compare({"value": "1.0", "unit": "V"}, {"value": "1.0", "unit": "V"})
    assert set(r.receipt["options"]) == {"abs_tol", "rel_tol", "floor", "precision"}
    assert "scale" not in r.receipt["result"]


# ------------------------------------------------------ classes and pool_valid
def test_singletons_are_pool_valid():
    r = compare_table([rec(mol="A"), rec(mol="B")], key="mol,tgt", pack="bioactivity")
    assert all(x["pool_valid"] and x["class_consensus"] == "single" for x in r.records)
    assert r.classes[0]["pooled_value"] == 41.0


def test_bounds_only_class_and_bound_records():
    r = compare_table([rec(value="1000", rel=">"), rec(value="5000", rel=">")],
                      key="mol,tgt", pack="bioactivity")
    assert r.classes[0]["consensus"] == "bounds_only"
    assert r.classes[0]["pooled_value"] is None
    assert all(x["pool_reason"] == "bound" for x in r.records)
    assert r.summary["pairs_within_classes"]["undecidable_bounds"] == 1


def test_disagreeing_class_is_not_pool_valid_and_exit_1():
    r = compare_table([rec(value="1"), rec(value="1000")], key="mol,tgt", pack="bioactivity")
    assert r.classes[0]["consensus"] == "disagree"
    assert all(x["pool_reason"] == "class_disagrees" for x in r.records)
    assert r.exit_code == 1


def test_within_floor_class_pools_with_geometric_median():
    r = compare_table([rec(value="40"), rec(value="160")], key="mol,tgt", pack="bioactivity")
    c = r.classes[0]
    assert c["consensus"] == "within_floor"
    assert c["pooled_value"] == pytest.approx(80.0)
    assert all(x["pool_valid"] for x in r.records)


def test_bound_inconsistent_with_pooled_value_makes_class_disagree():
    r = compare_table([rec(value="40"), rec(value="50"), rec(value="10000", rel=">")],
                      key="mol,tgt", pack="bioactivity")
    assert r.classes[0]["consensus"] == "disagree"


def test_bounds_consistent_flag():
    r = compare_table([rec(value="40"), rec(value="50"), rec(value="1000", rel="<")],
                      key="mol,tgt", pack="bioactivity")
    c = r.classes[0]
    assert c["consensus"] == "agree" and c["bounds_consistent"] == "true"


def test_condition_classes_split_and_name_the_reason():
    r = compare_table([rec(atype="B"), rec(atype="F"), rec(stype="Ki")], key="mol,tgt",
                      pack="bioactivity")
    labels = sorted(p["label"] for p in r.pairs)
    assert labels == ["not_comparable(assay_type)", "not_comparable(standard_type)",
                      "not_comparable(standard_type)"]
    assert r.summary["groups_with_more_than_one_class"] == 1
    assert all(x["pool_valid"] for x in r.records)   # each its own single class


def test_assumption_merges_ki_and_ic50_and_scales_ki():
    rows = [rec(value="100", stype="IC50"), rec(value="50", stype="Ki")]
    off = compare_table(rows, key="mol,tgt", pack="bioactivity")
    assert off.pairs[0]["label"] == "not_comparable(standard_type)"
    on = compare_table(rows, key="mol,tgt", pack="bioactivity", assume=["ki_ic50_x2"])
    assert len(on.classes) == 1
    assert on.pairs[0]["verdict"] == "agree"            # 50 x 2 = 100
    assert on.classes[0]["pooled_value"] == pytest.approx(100.0)
    assert on.records[1]["assumption"] == "ki_ic50_x2"
    assert on.receipt["options"]["assume"] == ["ki_ic50_x2"]


def test_exit_code_precedence_unparseable_over_disagree():
    r = compare_table([rec(value="1"), rec(value="1000"), rec(value="abc")], key="mol,tgt",
                      pack="bioactivity")
    assert r.exit_code == 3


def test_excluded_and_cross_class_do_not_set_exit_code():
    r = compare_table([rec(atype="B"), rec(atype="F", data_validity_comment="bad")],
                      key="mol,tgt", pack="bioactivity")
    assert r.exit_code == 0


def test_no_pack_means_no_conditions_checked():
    r = compare_table([rec(atype="B"), rec(atype="F", value="45")], key="mol,tgt",
                      log_tol=0.3)
    assert r.pairs[0]["verdict"] == "agree"
    assert "no pack" in r.text


def test_offset_units_and_rel_tol_refused():
    with pytest.raises(InputError, match="rel-tol"):
        compare_table([rec(value="20", unit="degC"), rec(value="21", unit="degC")],
                      key="mol,tgt", rel_tol=0.1)


# --------------------------------------------------------------- receipts/verify
def test_receipt_verifies_and_detects_tampering(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("mol,tgt,value,unit,standard_type\nM1,T1,41,nM,IC50\nM1,T1,300,nM,IC50\n",
                 encoding="utf-8")
    out = tmp_path / "out"
    compare_table(p, key="mol,tgt", pack="bioactivity", out=out)
    rp = out / "receipt.json"
    assert verify(rp).ok
    assert main(["verify", str(rp)]) == 0
    rec_ = json.loads(rp.read_text(encoding="utf-8"))
    rec_["summary"]["pairs"] = 99
    rp.write_text(json.dumps(rec_), encoding="utf-8")
    assert not verify(rp).ok


def test_verify_detects_changed_input_and_missing_input(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("mol,tgt,value,unit\nM1,T1,41,nM\n", encoding="utf-8")
    out = tmp_path / "out"
    compare_table(p, key="mol,tgt", out=out)
    p.write_text("mol,tgt,value,unit\nM1,T1,42,nM\n", encoding="utf-8")
    v = verify(out / "receipt.json")
    assert not v.ok and any(s[0] == "input hash" and not s[1] for s in v.steps)
    p.unlink()
    with pytest.raises(InputError, match="not found"):
        verify(out / "receipt.json")


def test_verify_with_input_override(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("mol,tgt,value,unit\nM1,T1,41,nM\n", encoding="utf-8")
    out = tmp_path / "out"
    compare_table(p, key="mol,tgt", out=out)
    moved = tmp_path / "moved.csv"
    p.rename(moved)
    assert verify(out / "receipt.json", input=moved).ok
    assert main(["verify", str(out / "receipt.json"), "--input", str(moved)]) == 0


def test_dataframe_input_saved_and_verifiable(tmp_path):
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame([rec(value=41.0), rec(value=50), rec(value=float("nan"))])
    out = tmp_path / "out"
    r = compare_table(df, key=["mol", "tgt"], pack="bioactivity", out=out)
    assert r.receipt["input"]["format"] == "records-json"
    assert verify(out / "receipt.json").ok


def test_outputs_are_deterministic(tmp_path):
    rows = [rec(value=str(v), atype=a) for v, a in [(41, "B"), (50, "B"), (300, "F"), (5, "B")]]
    a = compare_table(rows, key="mol,tgt", pack="bioactivity", out=tmp_path / "a")
    b = compare_table(rows, key="mol,tgt", pack="bioactivity", out=tmp_path / "b")
    assert a.files == b.files
    for n in ("records.csv", "classes.csv", "pairs.csv", "summary.json"):
        assert (tmp_path / "a" / n).read_bytes() == (tmp_path / "b" / n).read_bytes()


def test_cli_compare_table(tmp_path, capsys):
    p = tmp_path / "t.csv"
    p.write_text("mol,tgt,value,unit,standard_type\nM1,T1,1,nM,IC50\nM1,T1,1000,nM,IC50\n",
                 encoding="utf-8")
    code = main(["compare-table", str(p), "--key", "mol,tgt", "--pack", "bioactivity",
                 "--out", str(tmp_path / "o")])
    assert code == 1
    assert "Consilience pooling check" in capsys.readouterr().out
    assert main(["compare-table", str(p)]) == 64


# ------------------------------------------------------------ second domain: pKa
def test_pka_map_and_pack():
    rows = [
        {"unique_ID": "a", "InChI": "X", "pka_type": "pKa1", "pka_value": "4.75", "T": "25",
         "method": "E3bg", "assessment": "Reliable", "cosolvent": "", "pressure": ""},
        {"unique_ID": "b", "InChI": "X", "pka_type": "pKa1", "pka_value": "4.76", "T": "25",
         "method": "O5", "assessment": "Approximate", "cosolvent": "", "pressure": ""},
        {"unique_ID": "c", "InChI": "X", "pka_type": "pKa1", "pka_value": "4.60", "T": "40",
         "method": "E3bg", "assessment": "Reliable", "cosolvent": "", "pressure": ""},
        {"unique_ID": "d", "InChI": "X", "pka_type": "pKa1", "pka_value": "4.7", "T": "not_stated",
         "method": "E3bg", "assessment": "Uncertain", "cosolvent": "", "pressure": ""},
        {"unique_ID": "e", "InChI": "X", "pka_type": "pKa1", "pka_value": "4.9", "T": "25",
         "method": "E3bg", "assessment": "Very uncertain", "cosolvent": "", "pressure": ""},
    ]
    r = compare_table(rows, map="iupac_pka", pack="pka", abs_tol="0.02", floor="0.2")
    st = {x["id"]: x for x in r.records}
    assert st["a"]["pool_valid"] and st["b"]["pool_valid"]
    assert st["c"]["pool_valid"]                    # its own class (40 degC)
    assert st["d"]["pool_reason"] == "condition_not_stated(temperature)"
    assert st["e"]["record_status"].startswith("excluded(PKR1")
    c1 = [c for c in r.classes if c["class"] == st["a"]["condition_class"]][0]
    assert c1["methods"] == ["E3bg", "O5"]
    assert any(p["label"] == "not_comparable(temperature)" for p in r.pairs)


# -------------------------------------- same verdicts as compare() (randomised)
def _measure(row, fields):
    v = row["value"] if row["relation"] in ("=", None) else f"{row['relation']} {row['value']}"
    return {"value": v, "unit": row["unit"],
            "conditions": {f: row.get(f) for f in fields if f in row}}


@pytest.mark.parametrize("mode", ["log", "linear"])
def test_table_verdicts_equal_compare_verdicts(mode):
    rng = random.Random(7 if mode == "log" else 8)
    pack = load_rules("bioactivity")
    fields = [c["field"] for c in pack.rules]
    rows = []
    for g in range(60):
        for _ in range(rng.randint(1, 6)):
            unit = rng.choice(["nM", "uM", "nM"])
            val = rng.choice([f"{rng.uniform(1, 500):.1f}", str(rng.randint(1, 500)),
                              f"{rng.uniform(0.001, 0.5):.3f}"])
            rows.append(dict(mol=f"M{g}", tgt="T", value=val,
                             relation=rng.choice(["=", "=", "=", "<", ">"]), unit=unit,
                             standard_type=rng.choice(["IC50", "IC50", "Ki"]),
                             assay_type=rng.choice(["B", "B", "F", None]),
                             bao_format=rng.choice(["BAO_0000357", None]),
                             assay_variant_mutation=rng.choice([None, None, "L858R",
                                                                "unstated"])))
    opts = (dict(log_tol=0.3, log_floor=1.0) if mode == "log" else
            dict(abs_tol="20 nM", floor="100 nM"))
    r = compare_table(rows, key="mol,tgt", pack=pack, **opts)
    checked = 0
    for p in r.pairs:
        a, b = rows[p["a"] - 1], rows[p["b"] - 1]
        c = compare(_measure(a, fields), _measure(b, fields), pack=pack, **opts)
        assert (p["verdict"], p["label"]) == (c.verdict, c.label), (a, b, p)
        checked += 1
    assert checked > 100


def test_electrochemistry_quantity_and_record_conditions_match_compare():
    pack = load_rules("electrochemistry")
    conds = [
        {"electrolyte": {"identity": "H2SO4", "concentration": "0.5 mol/L"},
         "current_density": {"value": 10, "unit": "mA/cm^2", "normalization": "geometric"},
         "temperature": "25 degC", "ir_correction": True},
        {"electrolyte": {"identity": "sulfuric acid", "concentration": "500 mmol/L"},
         "current_density": {"value": 0.01, "unit": "A/cm^2", "normalization": "geometric"},
         "temperature": "298.15 K", "ir_correction": True},
        {"electrolyte": {"identity": "KOH", "concentration": "1 mol/L"},
         "current_density": {"value": 10, "unit": "mA/cm^2", "normalization": "ECSA"},
         "temperature": "room_temperature", "ir_correction": False},
    ]
    rows = [dict(cat="X", value=v, unit="mV", **c) for v, c in zip(["320", "331", "400"], conds, strict=True)]
    r = compare_table(rows, key="cat", pack=pack, abs_tol="15 mV")
    for p in r.pairs:
        a, b = rows[p["a"] - 1], rows[p["b"] - 1]
        ma = {"value": a["value"], "unit": "mV", "conditions": conds[p["a"] - 1]}
        mb = {"value": b["value"], "unit": "mV", "conditions": conds[p["b"] - 1]}
        c = compare(ma, mb, pack=pack, abs_tol="15 mV")
        assert (p["verdict"], p["label"]) == (c.verdict, c.label)
    assert r.pairs[0]["verdict"] == "agree"   # same conditions, other spellings and units


# ---------------------------------------------------------------------- speed
def test_speed_egfr_scale():
    import time
    rng = random.Random(1)
    rows = []
    for g in range(9000):
        n = 1 if rng.random() < 0.6 else rng.randint(2, 6)
        if g < 15:
            n = rng.randint(300, 600)
        for _ in range(n):
            rows.append(dict(parent_molecule_chembl_id=f"M{g}", target_chembl_id="CHEMBL203",
                             standard_value=f"{rng.uniform(0.1, 20000):.1f}",
                             standard_relation=rng.choice(["="] * 8 + [">", "<"]),
                             standard_units="nM",
                             standard_type=rng.choice(["IC50", "IC50", "Ki", "Kd", "EC50"]),
                             assay_type=rng.choice(["B", "F"]),
                             assay_variant_mutation=rng.choice(["", "", "L858R",
                                                                "UNDEFINED MUTATION"])))
    assert len(rows) > 25000
    t = time.time()
    compare_table(rows, map="chembl", pack="bioactivity")
    assert time.time() - t < 300   # spec E6: under 5 minutes (one core here)


# ------------------------------------------------- every bioactivity rule (step 2)
BA_FIELDS = ["standard_type", "assay_type", "assay_organism", "assay_category",
             "assay_tax_id", "assay_strain", "assay_tissue", "assay_cell_type",
             "assay_subcellular_fraction", "bao_format", "assay_variant_mutation"]


def test_bioactivity_pack_lists_exactly_these_conditions():
    assert [c["field"] for c in load_rules("bioactivity").rules] == BA_FIELDS


@pytest.mark.parametrize("field", BA_FIELDS)
def test_each_bioactivity_condition_splits_classes(field):
    base = {f: "X" for f in BA_FIELDS}
    base.update(standard_type="IC50")
    a = dict(rec(), **base)
    b = dict(rec(value="45"), **base)
    b[field] = "Ki" if field == "standard_type" else "Y"
    r = compare_table([a, b], key="mol,tgt", pack="bioactivity")
    assert r.pairs[0]["label"] == f"not_comparable({field})"
    same = compare_table([a, dict(b, **{field: a[field]})], key="mol,tgt", pack="bioactivity")
    assert same.pairs[0]["verdict"] == "agree"


@pytest.mark.parametrize("field", BA_FIELDS[1:])
def test_absent_on_one_side_is_not_stated(field):
    a = dict(rec(atype=None), **{field: "X"})
    b = rec(value="45", atype=None)
    r = compare_table([a, b], key="mol,tgt", pack="bioactivity")
    assert r.pairs[0]["label"] == f"not_stated({field})"


def test_br2_confidence_score():
    r = compare_table([rec(confidence_score="9"), rec(confidence_score="8"),
                       rec(confidence_score="")], key="mol,tgt", pack="bioactivity")
    assert [x["record_status"] for x in r.records] == [
        "usable", "excluded(BR2: confidence_score is 8)", "excluded(BR2: not stated)"]


def test_bioactivity_defaults_are_the_cited_thresholds():
    d = load_rules("bioactivity").content["defaults"]
    assert (d["log_tol"], d["log_floor"]) == (0.3, 1.0)
    assert "Landrum" in d["source"] and "Kramer" in d["source"]


def test_map_nested_paths_and_fixed_unit():
    from consilience.maps import map_from_dict
    m = map_from_dict({"kind": "column-map", "name": "n", "version": "n1",
                       "plain_english": "nested", "value": "result.value",
                       "fixed_unit": "nM", "fields": {"assay_type": "assay.type"}})
    rows = [{"mol": "M", "tgt": "T", "result": {"value": "41"}, "assay": {"type": "B"},
             "standard_type": "IC50"},
            {"mol": "M", "tgt": "T", "result": {"value": "45"}, "assay": {"type": "F"},
             "standard_type": "IC50"}]
    r = compare_table(rows, key="mol,tgt", map=m, pack="bioactivity")
    assert r.pairs[0]["label"] == "not_comparable(assay_type)"
    with pytest.raises(RuleFileError, match="not both"):
        map_from_dict({"kind": "column-map", "name": "n", "version": "n1",
                       "plain_english": "x", "value": "v", "unit": "u", "fixed_unit": "nM"})
