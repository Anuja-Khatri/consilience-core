"""Build step 1: contract loading and the validity engine (spec v1.0 §6)."""
import math
import textwrap
from pathlib import Path

import numpy as np
import pytest

from consilience.stress.contract import (ContractError, eval_dim_expr, load_contract, parse_derived,
                                         record_resolution)
from consilience.stress.validity import (check_rules, convex_polygon_ordered, convex_position, project_type,
                                         violations)


def _base(tmp_path: Path, **over):
    (tmp_path / "ev.py").write_text("def score(x):\n    return float(sum(x))\n")
    np.savez(tmp_path / "ref.npz", x=np.array([0.5, 0.5]))
    d = {
        "kind": "evaluator-contract", "name": "toy",
        "harness": {"kind": "function", "evaluator": "ev.py", "entry": "score"},
        "fields": [{"name": "x", "type": "real_array", "shape": [2], "role": "construction"}],
        "validity": [{"rule": "finite", "field": "x"}, {"rule": "range", "field": "x", "min": "0", "max": "1"}],
        "score": {"direction": "maximize", "record": {"value": "1.0", "source": "toy"}},
        "reference": {"file": "ref.npz"},
    }
    d.update(over)
    return d


def test_loads_and_hash_is_order_independent(tmp_path):
    c1 = load_contract(_base(tmp_path), base=tmp_path)
    d = _base(tmp_path)
    d2 = dict(reversed(list(d.items())))
    c2 = load_contract(d2, base=tmp_path)
    assert c1.hash == c2.hash
    assert c1.construction == ["x"]
    assert "ev.py" in c1.file_hashes and "ref.npz" in c1.file_hashes


@pytest.mark.parametrize("mutate, msg", [
    (lambda d: d.update(bogus=1), "unknown key"),
    (lambda d: d["validity"].append({"rule": "wobbly", "field": "x"}), "rule must be one of"),
    (lambda d: d.update(invariances=[{"transform": "twirl", "field": "x"}]), "transform must be one of"),
    (lambda d: d["validity"].append({"rule": "sum", "field": "x", "equals": "1"}), "a 'tolerance' must be stated"),
    (lambda d: d["score"]["record"].update(value=1.0), "must be written as a string"),
    (lambda d: d["score"].update(direction="up"), "direction must be"),
    (lambda d: d["validity"].append({"rule": "range", "field": "nope", "min": "0"}), "unknown field"),
    (lambda d: d.pop("reference"), "'reference' is required"),
    (lambda d: d["harness"].update(kind="py_path"), "program_function"),
    (lambda d: d["validity"].append({"rule": "predicate", "call": "f"}), "no 'glue' file"),
    (lambda d: d["score"]["record"].update(kind="best_known", margin="0"), "only to kind: threshold"),
])
def test_named_errors(tmp_path, mutate, msg):
    d = _base(tmp_path)
    mutate(d)
    with pytest.raises(ContractError, match=msg):
        load_contract(d, base=tmp_path)


def test_duplicate_yaml_key(tmp_path):
    _base(tmp_path)
    (tmp_path / "c.yaml").write_text("kind: evaluator-contract\nname: a\nname: b\n")
    with pytest.raises(ContractError, match="duplicate key"):
        load_contract(tmp_path / "c.yaml")


def test_glue_must_not_import_scorer(tmp_path):
    d = _base(tmp_path, glue="glue.py")
    d["validity"].append({"rule": "predicate", "call": "ok", "name": "ok"})
    (tmp_path / "glue.py").write_text("import ev\npredicates = {'ok': lambda c: (True, 0.0)}\n")
    with pytest.raises(ContractError, match="imports the scorer"):
        load_contract(d, base=tmp_path)
    (tmp_path / "glue.py").write_text("predicates = {'ok': lambda c: (True, 0.0)}\n")
    c = load_contract(d, base=tmp_path)
    assert c.glue_hash and c.glue is not None


def test_glue_function_must_exist(tmp_path):
    d = _base(tmp_path, glue="glue.py")
    d["validity"].append({"rule": "predicate", "call": "missing"})
    (tmp_path / "glue.py").write_text("predicates = {}\n")
    with pytest.raises(ContractError, match="no callable"):
        load_contract(d, base=tmp_path)


def test_dim_expressions():
    dims = {"n": 4, "m": 3, "rank": 2}
    assert eval_dim_expr("n*m", dims, "w") == 12
    assert eval_dim_expr("(n+1)*rank", dims, "w") == 10
    assert eval_dim_expr(7, dims, "w") == 7
    with pytest.raises(ContractError):
        eval_dim_expr("n-1", dims, "w")
    with pytest.raises(ContractError):
        eval_dim_expr("k", dims, "w")


def test_derived_expressions():
    assert parse_derived("len(f)", "w") == ("len", "f")
    assert parse_derived("P.shape[1]", "w") == ("shape", "P", 1)
    with pytest.raises(ContractError):
        parse_derived("f.sum()", "w")


def test_record_resolution():
    assert record_resolution("1.4557") == pytest.approx(5e-5)
    assert record_resolution("0") == 0.0
    assert record_resolution("-0.49012") == pytest.approx(5e-6)


# ------------------------------------------------------------------ validity, one test per rule

def R(rule, **kw):
    d = {"rule": rule, "field": "x", "tolerance": kw.pop("tolerance", "0")}
    d.update(kw)
    return d


def V(rules, x, **extra):
    cand = {"x": np.asarray(x)}
    cand.update({k: np.asarray(v) for k, v in extra.items()})
    return check_rules(rules, cand)


def test_finite():
    assert V([R("finite")], [1.0, 2.0]) == []
    v = V([R("finite")], [1.0, np.nan])
    assert v[0].cls == "gross" and math.isinf(v[0].magnitude)
    assert V([R("finite")], [1.0, np.inf])[0].rule == "finite"


def test_range_exact_boundary_and_small_vs_large():
    assert V([R("range", min="0", max="1")], [0.0, 1.0]) == []
    v = V([R("range", min="0")], [-1e-12, 0.5])
    assert v[0].cls == "small"
    v = V([R("range", min="0")], [-0.1, 0.5])
    assert v[0].cls == "large" and v[0].magnitude == pytest.approx(0.1)
    # exact: 0.1 as a float is slightly above 1/10
    assert V([R("range", max="0.1")], [0.1]) != []
    assert V([R("range", max="0.1", tolerance="1e-12")], [0.1]) == []
    # NaN is the finite rule's business, not range's
    assert V([R("range", min="0")], [np.nan]) == []


def test_shape_and_count():
    assert V([R("shape", shape=[2])], [1.0, 2.0]) == []
    assert V([R("shape", shape=[3])], [1.0, 2.0])[0].cls == "gross"
    assert V([R("count", equals=2)], [1.0, 2.0]) == []
    assert V([R("count", min=3)], [1.0, 2.0])[0].cls == "gross"


def test_integral_distinct_alphabet_are_type_class():
    assert V([R("integral")], [1.0, 2.0]) == []
    assert V([R("integral")], [1.0, 2.5])[0].cls == "type"
    assert V([R("distinct")], [1, 2, 3]) == []
    assert V([R("distinct")], [1, 2, 1])[0].cls == "type"
    assert V([R("alphabet", values=["-1", "1"])], [1, -1, 1]) == []
    assert V([R("alphabet", values=["-1", "1"])], [1, 0.5])[0].cls == "type"


def test_sum_and_norm_need_tolerance_semantics():
    assert V([R("sum", equals="1", tolerance="1e-12")], [0.25, 0.75]) == []
    assert V([R("sum", equals="1", tolerance="1e-12")], [0.25, 0.7])[0].rule == "sum"
    pts = np.array([[1.0, 0.0], [0.6, 0.8]])
    assert V([R("norm", equals="1", tolerance="1e-12", axis=1)], pts) == []
    assert V([R("norm", equals="1", tolerance="1e-12", axis=1)], pts * 1.001)[0].magnitude == pytest.approx(1e-3, rel=1e-3)


def test_in_disk_in_box_separation():
    assert V([R("in_disk", radius="1", center=["0", "0"])], np.array([0.5 + 0.5j])) == []
    assert V([R("in_disk", radius="1", center=["0", "0"])], np.array([1 + 1j]))[0].rule == "in_disk"
    c = np.array([[0.25, 0.25], [0.75, 0.75]])
    r = np.array([0.25, 0.25])
    assert check_rules([R("in_box", box=[["0", "1"], ["0", "1"]], margin_from="r")], {"x": c, "r": r}) == []
    assert check_rules([R("in_box", box=[["0", "1"], ["0", "1"]], margin_from="r")], {"x": c, "r": r * 1.1}) != []
    assert check_rules([R("pairwise_separation", radii_from="r")], {"x": c, "r": r}) == []
    v = check_rules([R("pairwise_separation", radii_from="r")], {"x": c, "r": np.array([0.4, 0.4])})
    assert v and v[0].magnitude == pytest.approx(0.8 - math.sqrt(0.5))


def test_convexity_ordered_and_unordered():
    sq = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    assert convex_position(sq) and convex_polygon_ordered(sq)
    shuffled = sq[[0, 2, 1, 3]]
    assert convex_position(shuffled) and not convex_polygon_ordered(shuffled)   # a 'bow tie'
    with_inner = np.vstack([sq, [[0.5, 0.5]]])
    assert not convex_position(with_inner)
    with_edge_point = np.vstack([sq[:2], [[2.0, 0.0]], sq[2:]])
    assert not convex_position(np.array([[0, 0], [1, 0], [2, 0], [1, 1]], float))
    star = np.array([[np.cos(t), np.sin(t)] for t in np.linspace(0, 4 * np.pi, 6)[:-1]])  # pentagram order
    assert convex_position(star) and not convex_polygon_ordered(star)
    assert V([R("convex_polygon_ordered")], shuffled)[0].cls == "large"


def test_collinear_coplanar_graph():
    assert V([R("no_k_collinear", k=3)], np.array([[0, 0], [1, 1], [2, 0]], float)) == []
    assert V([R("no_k_collinear", k=3)], np.array([[0, 0], [1, 1], [2, 2]], float)) != []
    cube = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1]], float)
    assert V([R("no_k_coplanar", k=4)], cube) == []
    assert V([R("no_k_coplanar", k=4)], np.vstack([cube, [[1, 1, 0]]])) != []
    assert V([R("graph_simple")], np.array([[0, 1], [1, 2]])) == []
    assert V([R("graph_simple")], np.array([[0, 1], [1, 0]])) != []
    assert V([R("graph_simple")], np.array([[0, 0]])) != []


def test_predicate_and_projection(tmp_path):
    d = _base(tmp_path, glue="glue.py")
    d["fields"] = [{"name": "x", "type": "int_set", "role": "construction"}]
    d["validity"] = [{"rule": "finite", "field": "x"}, {"rule": "integral", "field": "x"},
                     {"rule": "distinct", "field": "x"},
                     {"rule": "predicate", "call": "has_zero", "name": "has_zero"}]
    (tmp_path / "glue.py").write_text("predicates = {'has_zero': lambda c: (0 in list(c['x']), float('inf'))}\n")
    np.savez(tmp_path / "ref.npz", x=np.array([0, 1, 3]))
    c = load_contract(d, base=tmp_path)
    assert violations(c, {"x": np.array([0, 1, 3])}) == []
    v = violations(c, {"x": np.array([1, 3])})
    assert [x.rule for x in v] == ["has_zero"] and v[0].cls == "large"
    p = project_type(c, {"x": np.array([0.0, 1.4, 1.0, 3.0])})
    assert list(p["x"]) == [0.0, 1.0, 3.0]


def test_extra_files_are_hashed(tmp_path):
    d = _base(tmp_path)
    (tmp_path / "helper.py").write_text("X = 1\n")
    d["harness"]["extra_files"] = ["helper.py"]
    c = load_contract(d, base=tmp_path)
    assert "helper.py" in c.file_hashes
    d["harness"]["extra_files"] = ["missing.py"]
    with pytest.raises(ContractError, match="file not found"):
        load_contract(d, base=tmp_path)


def test_nonfinite_reject_value_is_named_error(tmp_path):
    d = _base(tmp_path)
    d["harness"]["reject"] = {"values": [float("-inf")]}
    with pytest.raises(ContractError, match="must be finite"):
        load_contract(d, base=tmp_path)


def test_validity_survives_huge_values_and_mismatched_counts():
    big = 1e300
    v = check_rules([R("in_disk", radius="1", center=["0", "0"])], {"x": np.array([big + big * 1j])})
    assert v and math.isinf(v[0].magnitude)
    v = check_rules([R("norm", equals="1", tolerance="1e-12", axis=1)], {"x": np.array([[big, big]])})
    assert v
    c = np.array([[0.25, 0.25], [0.75, 0.75], [0.5, 0.5]])
    r = np.array([0.1, 0.1])                              # one radius short
    assert check_rules([R("pairwise_separation", radii_from="r")], {"x": c, "r": r})
    assert check_rules([R("in_box", box=[["0", "1"], ["0", "1"]], margin_from="r")], {"x": c, "r": r})
    v = check_rules([R("pairwise_separation", radii_from="r")], {"x": c * big, "r": np.array([big, big, big])})
    assert v is not None


@pytest.mark.parametrize("rule", [
    R("in_box", box=[["0", "1"], ["0", "1"]], margin_from="r"), R("pairwise_separation", radii_from="r"),
    R("range", min="0"), R("distinct"), R("integral"), R("alphabet", values=["1"]), R("convex_position"),
    R("convex_polygon_ordered"), R("no_k_collinear", k=3), R("no_k_coplanar", k=4),
    R("norm", equals="1", tolerance="1e-12", axis=1), R("sum", equals="1", tolerance="1e-12"),
])
def test_every_rule_survives_empty_input(rule):
    check_rules([rule], {"x": np.zeros((0, 2)), "r": np.zeros(0)})
    check_rules([rule], {"x": np.zeros((0, 3)), "r": np.zeros(0)})
