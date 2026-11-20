"""Build step 2: the harness runner, all five kinds (spec v1.0 §6.1)."""
import json
import textwrap

import numpy as np
import pytest

from consilience.stress.contract import load_contract
from consilience.stress.harness import Harness, extract


def _contract(tmp_path, harness, files: dict, returns=None, fields=None, glue=None):
    for name, text in files.items():
        (tmp_path / name).write_text(textwrap.dedent(text))
    np.savez(tmp_path / "ref.npz", x=np.array([0.25, 0.5]))
    d = {"kind": "evaluator-contract", "name": "t", "harness": harness,
         "fields": fields or [{"name": "x", "type": "real_array", "shape": [2], "role": "construction"}],
         "validity": [{"rule": "finite", "field": "x"}],
         "score": {"direction": "maximize"}, "reference": {"file": "ref.npz"}}
    if returns:
        d["returns"] = returns
    if glue:
        d["glue"] = glue
    return load_contract(d, base=tmp_path)


def test_extract_paths():
    out = {"scores": {"scores": [{"metric": "a", "score": 1.5}, {"metric": "b", "score": 2.0}]}, "x": {"y": 3}}
    assert extract(out, "scores.scores[metric=b].score") == 2.0
    assert extract(out, "x.y") == 3
    assert extract(out, "x.z") is None
    assert extract(out, "scores.scores[metric=c].score") is None


def test_function_kind_accept_and_reject_values(tmp_path):
    c = _contract(tmp_path, {"kind": "function", "evaluator": "ev.py", "entry": "score",
                             "reject": {"values": [-1e9]}},
                  {"ev.py": """
                   import numpy as np
                   def score(x):
                       print("noise on stdout must not break the protocol")
                       if not np.isfinite(x).all():
                           return -1e9
                       return float(x.sum())
                   """})
    with Harness(c) as h:
        o = h.score({"x": np.array([0.25, 0.5])})
        assert o.accepted and o.score == 0.75
        o = h.score({"x": np.array([np.nan, 0.5])})
        assert o.rejected and o.raw == -1e9
        assert h.calls == 2


def test_function_kind_exception_is_rejection(tmp_path):
    c = _contract(tmp_path, {"kind": "function", "evaluator": "ev.py", "entry": "score"},
                  {"ev.py": "def score(x):\n    raise ValueError('bad input')\n"})
    with Harness(c) as h:
        o = h.score({"x": np.array([1.0, 2.0])})
        assert o.rejected and o.raw["exception"] == "ValueError"


def test_nonfinite_output_is_rejection(tmp_path):
    c = _contract(tmp_path, {"kind": "function", "evaluator": "ev.py", "entry": "score"},
                  {"ev.py": "def score(x):\n    return float('nan')\n"})
    with Harness(c) as h:
        o = h.score({"x": np.array([1.0, 2.0])})
        assert o.rejected and not o.accepted


def test_py_path_kind_with_claimed_field(tmp_path):
    c = _contract(tmp_path, {"kind": "py_path", "evaluator": "ev.py", "entry": "evaluate",
                             "program_function": "run", "score_key": "combined_score",
                             "reject": {"keys_present": ["error"]}},
                  {"ev.py": """
                   import importlib.util, os
                   def evaluate(path):
                       spec = importlib.util.spec_from_file_location("p" + os.path.basename(path)[:-3], path)
                       m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
                       x, claim = m.run()
                       if abs(claim - float(x.sum())) > 1e-3:
                           return {"combined_score": 0.0, "error": "mismatch"}
                       return {"combined_score": claim}
                   """, "glue.py": "quantities = {'s': lambda c: float(c['x'].sum())}\n"},
                  returns=["x", "claim"],
                  fields=[{"name": "x", "type": "real_array", "shape": [2], "role": "construction"},
                          {"name": "claim", "type": "real", "role": "claimed", "quantity": "s"}],
                  glue="glue.py")
    with Harness(c) as h:
        assert h.score({"x": np.array([0.25, 0.5]), "claim": np.array(0.75)}).score == 0.75
        assert h.score({"x": np.array([0.25, 0.5]), "claim": np.array(0.7505)}).score == 0.7505   # slack accepted
        assert h.score({"x": np.array([0.25, 0.5]), "claim": np.array(0.8)}).rejected


def test_timeout_never_a_score_and_worker_restarts(tmp_path):
    c = _contract(tmp_path, {"kind": "function", "evaluator": "ev.py", "entry": "score", "timeout_s": 1},
                  {"ev.py": """
                   import time
                   def score(x):
                       if x[0] > 0.9:
                           time.sleep(30)
                       return float(x.sum())
                   """})
    with Harness(c) as h:
        o = h.score({"x": np.array([0.95, 0.0])})
        assert o.timeout and o.score is None
        assert h.score({"x": np.array([0.25, 0.5])}).score == 0.75      # restarted


def test_broken_scorer_is_harness_error_with_stderr(tmp_path):
    c = _contract(tmp_path, {"kind": "function", "evaluator": "ev.py", "entry": "score"},
                  {"ev.py": "import nonexistent_module_xyz\ndef score(x):\n    return 1.0\n"})
    with Harness(c) as h:
        o = h.score({"x": np.array([0.25, 0.5])})
        assert o.harness_error and "nonexistent_module_xyz" in o.harness_error


def test_cli_json_kind_with_reject_file(tmp_path):
    c = _contract(tmp_path, {"kind": "cli_json", "evaluator": "ev.py", "program_function": "run",
                             "argv": ["{python}", "{evaluator}", "--program_path", "{program}", "--results_dir", "{outdir}"],
                             "result_file": "{outdir}/metrics.json", "score_key": "combined_score",
                             "reject": {"file": {"path": "{outdir}/correct.json", "key": "correct", "equals": False}}},
                  {"ev.py": """
                   import argparse, json, importlib.util, os
                   ap = argparse.ArgumentParser(); ap.add_argument("--program_path"); ap.add_argument("--results_dir")
                   a = ap.parse_args()
                   spec = importlib.util.spec_from_file_location("p", a.program_path)
                   m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
                   x = m.run()
                   ok = bool((x >= 0).all())
                   json.dump({"combined_score": float(x.sum())}, open(os.path.join(a.results_dir, "metrics.json"), "w"))
                   json.dump({"correct": ok}, open(os.path.join(a.results_dir, "correct.json"), "w"))
                   """})
    with Harness(c) as h:
        assert h.score({"x": np.array([0.25, 0.5])}).score == 0.75
        assert h.score({"x": np.array([-0.25, 0.5])}).rejected


def test_sdk_dict_kind(tmp_path):
    c = _contract(tmp_path, {"kind": "sdk_dict", "evaluator": "ev.py", "entry": "evaluator",
                             "program_function": "run", "score_key": "scores.scores[metric=total].score"},
                  {"ev.py": """
                   def evaluator(program):
                       ns = {}
                       exec(program["content"]["files"][0]["content"], ns)
                       x = ns["run"]()
                       return {"scores": {"scores": [{"metric": "total", "score": float(x.sum())}]}}
                   """})
    with Harness(c) as h:
        assert h.score({"x": np.array([0.25, 0.5])}).score == 0.75


def test_template_kind_keeps_code_outside_the_block(tmp_path):
    c = _contract(tmp_path, {"kind": "template", "evaluator": "ev.py", "entry": "evaluate",
                             "program_function": "construct", "score_key": "score",
                             "program_template": "program.py", "block_start": "# EVOLVE-BLOCK-START",
                             "block_end": "# EVOLVE-BLOCK-END"},
                  {"ev.py": """
                   def evaluate(path):
                       ns = {}
                       exec(open(path).read(), ns)
                       return ns["evaluate"]()
                   """,
                   "program.py": """
                   # EVOLVE-BLOCK-START
                   def construct():
                       return None
                   # EVOLVE-BLOCK-END
                   def evaluate():
                       x = construct()
                       if (x < 0).any():
                           return {"score": float("-inf")}
                       return {"score": float(x.sum())}
                   """})
    with Harness(c) as h:
        assert h.score({"x": np.array([0.25, 0.5])}).score == 0.75
        assert h.score({"x": np.array([-0.25, 0.5])}).rejected        # validity inside the candidate file kept
