"""Build step 3: each check catches its planted gap; each fixed twin PASSes (spec v1.0 §7, §8, §12)."""
import json
import textwrap
from pathlib import Path

import numpy as np
import pytest

from consilience.cli import main as cli_main
from consilience.stress import stress
from consilience.verify import verify


def make(tmp_path: Path, ev: str, contract: dict, ref: dict, glue: str = None, extra_npz: dict = None, name="c"):
    d = tmp_path / name
    d.mkdir(exist_ok=True)
    (d / "ev.py").write_text(textwrap.dedent(ev))
    np.savez(d / "ref.npz", **{k: np.asarray(v) for k, v in ref.items()})
    for fn, arrs in (extra_npz or {}).items():
        np.savez(d / fn, **{k: np.asarray(v) for k, v in arrs.items()})
    if glue:
        (d / "glue.py").write_text(textwrap.dedent(glue))
        contract.setdefault("glue", "glue.py")
    contract.setdefault("kind", "evaluator-contract")
    contract.setdefault("name", name)
    contract.setdefault("reference", {"file": "ref.npz"})
    import yaml
    (d / "contract.yaml").write_text(yaml.safe_dump(contract, sort_keys=False))
    return d / "contract.yaml"


def kinds(run, block=True):
    fs = run.result.findings if block else run.result.reported
    return sorted({(f.check, f.kind) for f in fs if f.block == block})


VEC = {"name": "x", "type": "real_array", "shape": [4], "role": "construction"}
FN = lambda entry="score", **kw: {"kind": "function", "evaluator": "ev.py", "entry": entry, **kw}


# ---------------------------------------------------------------- C1 gross / sentinel
def test_c1_nan_accepted_and_fixed_twin(tmp_path):
    base = dict(harness=FN(), fields=[VEC],
                validity=[{"rule": "finite", "field": "x"}, {"rule": "range", "field": "x", "min": "0", "max": "1"}],
                score={"direction": "maximize", "record": {"value": "4.0", "source": "toy"}})
    leaky = make(tmp_path, """
        import numpy as np
        def score(x):
            if np.any(x < 0) or np.any(x > 1):      # NaN slips through both comparisons
                raise ValueError("out of range")
            return float(np.nansum(x)) + 0.5 * float(np.isnan(x).sum())
        """, dict(base), {"x": [0.5, 0.5, 0.5, 0.5]}, name="leaky")
    r = stress(leaky, budget="small")
    assert r.verdict == "BLOCK" and ("C1", "accepts_gross_invalid") in kinds(r)
    fixed = make(tmp_path, """
        import numpy as np
        def score(x):
            if not np.isfinite(x).all() or np.any(x < 0) or np.any(x > 1):
                raise ValueError("invalid")
            return float(x.sum())
        """, dict(base), {"x": [0.5, 0.5, 0.5, 0.5]}, name="fixed")
    assert stress(fixed, budget="small").verdict == "PASS"


def test_c1_sentinel_is_best(tmp_path):
    base = dict(harness=FN(reject={"values": [1e9, -1e9]}), fields=[{"name": "x", "type": "real_array", "role": "construction"}],
                validity=[{"rule": "finite", "field": "x"}, {"rule": "count", "field": "x", "equals": 4},
                          {"rule": "range", "field": "x", "min": "0", "max": "1"}],
                score={"direction": "maximize"})
    leaky = make(tmp_path, """
        import numpy as np
        def score(x):
            if len(x) != 4:
                return 1e9                      # 'high error' - but the score is maximised
            if not np.isfinite(x).all() or (x < 0).any() or (x > 1).any():
                return -1e9
            return float(x.sum())
        """, dict(base), {"x": [0.5] * 4}, name="leaky")
    r = stress(leaky, budget="small")
    assert ("C1", "sentinel_is_best") in kinds(r)
    fixed = make(tmp_path, """
        import numpy as np
        def score(x):
            if len(x) != 4 or not np.isfinite(x).all() or (x < 0).any() or (x > 1).any():
                return -1e9
            return float(x.sum())
        """, dict(base), {"x": [0.5] * 4}, name="fixed")
    assert stress(fixed, budget="small").verdict == "PASS"


# ---------------------------------------------------------------- C2
def test_c2_self_report_and_fixed(tmp_path):
    fields = [VEC, {"name": "c", "type": "real", "role": "claimed", "quantity": "total"}]
    glue = "quantities = {'total': lambda c: float(c['x'].sum())}\n"
    base = dict(harness=FN(), fields=fields, returns=["x", "c"],
                validity=[{"rule": "finite", "field": "x"}, {"rule": "range", "field": "x", "min": "0", "max": "1"}],
                score={"direction": "maximize", "record": {"value": "4.000", "source": "toy"}})
    leaky = make(tmp_path, """
        import numpy as np
        def score(x, c):
            if not np.isfinite(x).all() or (x < 0).any() or (x > 1).any():
                raise ValueError
            if abs(c - x.sum()) > 1e-2:
                raise ValueError("mismatch")
            return float(c)                     # scores the self-report
        """, dict(base), {"x": [0.5] * 4}, glue=glue, name="leaky")
    r = stress(leaky, budget="small")
    k = kinds(r)
    assert ("C2", "trusts_self_report") in k
    f = next(f for f in r.result.findings if f.kind == "trusts_self_report")
    assert f.data["slack_claim_units"] == pytest.approx(1e-2, rel=1e-3)
    fixed = make(tmp_path, """
        import numpy as np
        def score(x, c):
            if not np.isfinite(x).all() or (x < 0).any() or (x > 1).any():
                raise ValueError
            if abs(c - x.sum()) > 1e-2:
                raise ValueError("mismatch")
            return float(x.sum())               # scores the recomputed value
        """, dict(base), {"x": [0.5] * 4}, glue=glue, name="fixed")
    assert stress(fixed, budget="small").verdict == "PASS"


# ---------------------------------------------------------------- C4 integer invariance
def test_c4_integer_invariance_and_fixed(tmp_path):
    base = dict(harness=FN(), fields=[{"name": "B", "type": "int_set", "role": "construction"}],
                validity=[{"rule": "finite", "field": "B"}, {"rule": "integral", "field": "B"},
                          {"rule": "distinct", "field": "B"}],
                invariances=[{"transform": "translate", "field": "B"}, {"transform": "permute", "field": "B"}],
                score={"direction": "maximize"})
    leaky = make(tmp_path, """
        def score(B):
            B = sorted(set(int(b) for b in B))
            if 0 not in B:
                B.append(0)                     # appended after sorting: order now matters below
            diffs = {abs(B[i + 1] - B[i]) for i in range(len(B) - 1)}
            return float(len(diffs))
        """, dict(base), {"B": [0, 1, 3, 7]}, name="leaky")
    r = stress(leaky, budget="small")
    assert ("C4", "invariance_broken_integer") in kinds(r)
    fixed = make(tmp_path, """
        def score(B):
            B = sorted(set(int(b) for b in B))
            return float(len({b - a for a in B for b in B if b > a}))
        """, dict(base), {"B": [0, 1, 3, 7]}, name="fixed")
    assert stress(fixed, budget="small").verdict == "PASS"


# ---------------------------------------------------------------- C4 threshold flips
def test_c4_threshold_flip_and_fixed(tmp_path):
    base = dict(harness=FN(), fields=[VEC],
                validity=[{"rule": "finite", "field": "x"}],
                invariances=[{"transform": "permute", "field": "x"}],
                score={"direction": "maximize", "record": {"value": "0", "kind": "threshold", "success": ">",
                                                           "source": "toy: positive = counterexample"}})
    ref = {"x": [1e16, 3.0, -1e16, -3.0]}       # true sum 0; a naive float sum gives -1, 0 or +1 by order
    leaky = make(tmp_path, """
        def score(x):
            s = 0.0
            for v in x:            # naive float sum: depends on the order
                s += float(v)
            return s
        """, dict(base), ref, name="leaky")
    r = stress(leaky, budget="small")
    assert ("C4", "decision_flips_under_invariance") in kinds(r)
    fixed = make(tmp_path, """
        import math
        def score(x):
            return math.fsum(float(v) for v in x)
        """, dict(base), ref, name="fixed")
    assert ("C4", "decision_flips_under_invariance") not in kinds(stress(fixed, budget="small"))


# ---------------------------------------------------------------- C3 / escalation exploit
def test_c3_exploitable_invalid_and_fixed(tmp_path):
    # maximise sum(x) subject to ||x||_2 <= 1 ; the leaky scorer forgets the constraint
    glue = """
        import numpy as np
        from fractions import Fraction
        def in_ball(c):
            x = c['x']
            sq = sum(Fraction(float(v)) ** 2 for v in x)
            return (sq <= 1, float(max(0.0, float(sq) - 1.0)))
        predicates = {'in_ball': in_ball}
        """
    base = dict(harness=FN(), fields=[VEC],
                validity=[{"rule": "finite", "field": "x"}, {"rule": "predicate", "call": "in_ball", "name": "in_ball"}],
                score={"direction": "maximize", "record": {"value": "2.000", "source": "toy: 4/sqrt(4)"}})
    leaky = make(tmp_path, """
        def score(x):
            return float(sum(x))
        """, dict(base), {"x": [0.25, 0.25, 0.25, 0.25]}, glue=glue, name="leaky")
    r = stress(leaky, budget="small")
    k = kinds(r)
    assert any(kind == "exploitable_invalid" for _, kind in k), k
    fixed = make(tmp_path, """
        import numpy as np
        def score(x):
            if float(np.dot(x, x)) > 1.0:
                raise ValueError("outside the ball")
            return float(sum(x))
        """, dict(base), {"x": [0.25, 0.25, 0.25, 0.25]}, glue=glue, name="fixed")
    rf = stress(fixed, budget="small")
    assert not any(kind == "exploitable_invalid" for _, kind in kinds(rf)), kinds(rf)


# ---------------------------------------------------------------- no false alarms
def test_rounding_scorer_is_not_blocked(tmp_path):
    base = dict(harness=FN(), fields=[{"name": "z", "type": "int_array", "shape": [3], "role": "construction"}],
                validity=[{"rule": "finite", "field": "z"}, {"rule": "integral", "field": "z"},
                          {"rule": "range", "field": "z", "min": "0", "max": "10"}],
                score={"direction": "maximize"})
    p = make(tmp_path, """
        import numpy as np
        def score(z):
            z = np.around(np.asarray(z, float))          # rounds fractional input itself
            if not np.isfinite(z).all() or (z < 0).any() or (z > 10).any():
                raise ValueError
            return float(z.sum())
        """, base, {"z": np.array([1, 2, 3])})
    r = stress(p, budget="small")
    assert ("C1", "exploitable_type_violation") not in kinds(r)
    assert any(f.kind == "type_violation_harmless" for f in r.result.reported)


def test_equality_without_projection_is_unpaired_not_block(tmp_path):
    glue = """
        from fractions import Fraction
        def unit_sum(c):
            d = abs(sum(Fraction(float(v)) for v in c['x']) - 1)
            return (d <= Fraction(1, 10**12), float(d))
        predicates = {'unit_sum': unit_sum}
        """
    base = dict(harness=FN(), fields=[VEC],
                validity=[{"rule": "finite", "field": "x"}, {"rule": "range", "field": "x", "min": "0"},
                          {"rule": "predicate", "call": "unit_sum", "name": "unit_sum", "equality": True,
                           "tolerance": "1e-12"}],
                score={"direction": "maximize", "record": {"value": "0.5000", "source": "toy"}})
    p = make(tmp_path, """
        import numpy as np
        def score(x):
            if not np.isfinite(x).all() or (x < 0).any() or abs(x.sum() - 1) > 1e-3:
                raise ValueError
            return float(np.max(x) * 0.25 + 0.2)
        """, base, {"x": [0.25] * 4}, glue=glue)
    r = stress(p, budget="small")
    # search-based findings (C3, escalation) have no valid twin here, so they never BLOCK on a paired gain;
    # C1's single-rule scale attack is like-for-like (same shape, only the scale) and may BLOCK: the 1e-3 slack
    # on the equality really buys score.
    assert not any(f.block and f.check in ("C3", "C1-escalation") and not f.data.get("beats_record")
                   for f in r.result.findings)
    assert all(f.check == "C1" for f in r.result.findings if f.kind == "exploitable_invalid")


# ---------------------------------------------------------------- ABSTAIN reasons
def test_abstain_reasons(tmp_path):
    base = dict(harness=FN(), fields=[VEC],
                validity=[{"rule": "finite", "field": "x"}, {"rule": "range", "field": "x", "min": "0", "max": "1"}],
                score={"direction": "maximize"})
    p = make(tmp_path, "def score(x):\n    return 1.0\n", dict(base), {"x": [2.0, 0, 0, 0]}, name="badref")
    r = stress(p, budget="small")
    assert r.verdict == "ABSTAIN" and r.result.abstain_reasons[0]["reason"] == "reference_invalid" and r.exit_code == 2
    p = make(tmp_path, "def score(x):\n    raise ValueError('no')\n", dict(base), {"x": [0.5] * 4}, name="rej")
    assert stress(p, budget="small").result.abstain_reasons[0]["reason"] == "reference_rejected"
    nb = dict(base, validity=[{"rule": "finite", "field": "x"}],
              fields=[VEC, {"name": "y", "type": "real_array", "shape": [1], "role": "construction"}])
    p = make(tmp_path, "def score(x, y):\n    return 1.0\n", nb, {"x": [0.5] * 4, "y": [0.0]}, name="norules")
    assert stress(p, budget="small").result.abstain_reasons[0]["reason"] == "no_validity_rules"


# ---------------------------------------------------------------- receipt, determinism, verify, CLI
def _leaky_selfreport(tmp_path):
    fields = [VEC, {"name": "c", "type": "real", "role": "claimed", "quantity": "total"}]
    return make(tmp_path, """
        import numpy as np
        def score(x, c):
            if not np.isfinite(x).all() or (x < 0).any() or (x > 1).any() or abs(c - x.sum()) > 1e-2:
                raise ValueError
            return float(c)
        """, dict(harness=FN(), fields=fields, returns=["x", "c"],
                  validity=[{"rule": "finite", "field": "x"}, {"rule": "range", "field": "x", "min": "0", "max": "1"}],
                  invariances=[{"transform": "permute", "field": "x"}],
                  score={"direction": "maximize", "record": {"value": "4.000", "source": "toy"}}),
        {"x": [0.5] * 4}, glue="quantities = {'total': lambda c: float(c['x'].sum())}\n", name="sr")


def test_receipt_is_deterministic_and_verifies(tmp_path):
    p = _leaky_selfreport(tmp_path)
    a = stress(p, budget="small", seed=3, out=tmp_path / "o1")
    b = stress(p, budget="small", seed=3, out=tmp_path / "o2")
    strip = lambda r: {k: v for k, v in r.items() if k not in ("created", "environment")}
    assert json.dumps(strip(a.receipt), sort_keys=True) == json.dumps(strip(b.receipt), sort_keys=True)
    files1 = sorted(q.relative_to(tmp_path / "o1") for q in (tmp_path / "o1").rglob("*.json") if q.name != "receipt.json")
    for q in files1:
        assert (tmp_path / "o1" / q).read_bytes() == (tmp_path / "o2" / q).read_bytes()
    v = verify(tmp_path / "o1" / "receipt.json")
    assert v.ok, v.steps
    assert any("trusts_self_report" in s[0] for s in v.steps)


def test_verify_detects_edited_candidate(tmp_path):
    p = _leaky_selfreport(tmp_path)
    stress(p, budget="small", out=tmp_path / "o")
    cand = next((tmp_path / "o" / "candidates").glob("*.json"))
    d = json.loads(cand.read_text())
    d["c"]["values"][0] = 3.999
    cand.write_text(json.dumps(d))
    assert not verify(tmp_path / "o" / "receipt.json").ok


def test_cli_exit_codes(tmp_path, capsys):
    p = _leaky_selfreport(tmp_path)
    assert cli_main(["stress", str(p), "--budget", "small", "--out", str(tmp_path / "o")]) == 1
    out = capsys.readouterr().out
    assert "BLOCK" in out and "trusts_self_report" in out
    assert cli_main(["verify", str(tmp_path / "o" / "receipt.json")]) == 0
    assert cli_main(["stress", str(tmp_path / "missing.yaml")]) == 64
    assert cli_main(["stress", str(p), "--only", "C9"]) == 64


def test_scalar_and_2d_fields_do_not_crash(tmp_path):
    # a scalar construction field and an (n, 2) field with a distinct rule (regression for two step-5 crashes)
    base = dict(harness=FN(), fields=[{"name": "s", "type": "real", "role": "construction"},
                                      {"name": "P", "type": "real_array", "role": "construction"}],
                validity=[{"rule": "finite", "field": "s"}, {"rule": "range", "field": "s", "min": "0", "max": "1"},
                          {"rule": "finite", "field": "P"}, {"rule": "distinct", "field": "P"},
                          {"rule": "count", "field": "P", "equals": 3}],
                score={"direction": "maximize"})
    p = make(tmp_path, """
        import numpy as np
        def score(s, P):
            P = np.asarray(P, float)
            if P.shape != (3, 2) or not np.isfinite(P).all() or not np.isfinite(s) or not 0 <= s <= 1:
                raise ValueError
            return float(s + np.min([np.linalg.norm(P[i] - P[j]) for i in range(3) for j in range(i)]))
        """, base, {"s": 0.5, "P": [[0, 0], [1, 0], [0, 1]]})
    r = stress(p, budget="small")
    assert r.verdict in ("PASS", "BLOCK")
