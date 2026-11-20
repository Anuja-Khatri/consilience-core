"""The consilience-stress agent plugin: recorded hook inputs (spec v1.0 §9)."""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import yaml

HOOK = Path(__file__).resolve().parent.parent / "integrations" / "agent-plugin" / "consilience-stress" / "hooks" / "after_edit.py"


def _setup(tmp_path: Path, leaky: bool):
    guard = "(x < 0).any() or (x > 1).any()" if leaky else "not np.isfinite(x).all() or (x < 0).any() or (x > 1).any()"
    bonus = "0.5 * float(np.isnan(x).sum())" if leaky else "0.0"
    (tmp_path / "scorer.py").write_text(textwrap.dedent(f"""
        import numpy as np
        def score(x):
            if {guard}:
                raise ValueError
            return float(np.nansum(x)) + {bonus}
        """))
    np.savez(tmp_path / "ref.npz", x=np.array([0.5, 0.5, 0.5, 0.5]))
    (tmp_path / "contract.yaml").write_text(yaml.safe_dump({
        "kind": "evaluator-contract", "name": "toy", "contract_author": "model",
        "harness": {"kind": "function", "evaluator": "scorer.py", "entry": "score"},
        "fields": [{"name": "x", "type": "real_array", "shape": [4], "role": "construction"}],
        "validity": [{"rule": "finite", "field": "x"}, {"rule": "range", "field": "x", "min": "0", "max": "1"}],
        "score": {"direction": "maximize"}, "reference": {"file": "ref.npz"}}, sort_keys=False))


def _hook(tmp_path, event, mode="--claude"):
    p = subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps(event) if not isinstance(event, str) else event,
                       capture_output=True, text=True, cwd=tmp_path, timeout=300)
    assert p.returncode == 0
    return p.stdout.strip()


def test_edit_of_contracted_scorer_reports_block(tmp_path):
    _setup(tmp_path, leaky=True)
    out = _hook(tmp_path, {"tool_name": "Edit", "tool_input": {"file_path": str(tmp_path / "scorer.py")}})
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "BLOCK" in ctx and "accepts_gross_invalid" in ctx
    assert "consilience verify" in ctx
    assert list((tmp_path / "consilience_receipts" / "stress").glob("*/receipt.json"))


def test_fixed_scorer_passes(tmp_path):
    _setup(tmp_path, leaky=False)
    out = _hook(tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "scorer.py")}})
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "PASS" in ctx and "Not a proof" in ctx


def test_unrelated_file_and_bad_input_do_nothing(tmp_path):
    _setup(tmp_path, leaky=True)
    (tmp_path / "notes.md").write_text("x")
    assert _hook(tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "notes.md")}}) == "{}"
    assert _hook(tmp_path, "not json at all").startswith("{")
    assert _hook(tmp_path, {"tool_name": "Bash", "tool_input": {"command": "ls"}}) == "{}"


def test_antigravity_post_then_inject(tmp_path):
    _setup(tmp_path, leaky=True)
    assert _hook(tmp_path, {"toolInput": {"TargetFile": str(tmp_path / "scorer.py")}}, "--antigravity-post") == "{}"
    out = json.loads(_hook(tmp_path, {}, "--antigravity-inject"))
    assert "BLOCK" in out["injectSteps"][0]["ephemeralMessage"]
    assert _hook(tmp_path, {}, "--antigravity-inject") == "{}"          # injected once


def test_verify_reports_unrunnable_scorer_cleanly(tmp_path):
    """A receipt whose scorer cannot be imported fails verify with a message, not a traceback."""
    from consilience import verify
    from consilience.stress import stress
    _setup(tmp_path, leaky=True)
    src = (tmp_path / "scorer.py").read_text()
    (tmp_path / "scorer.py").write_text("import os\nif os.path.exists(os.path.join(os.path.dirname(__file__), 'FLAG')):\n"
                                        "    import consilience_no_such_module_xyz\n" + src)
    r = stress(tmp_path / "contract.yaml", out=tmp_path / "out")
    assert r.verdict == "BLOCK"
    (tmp_path / "FLAG").write_text("")
    v = verify(tmp_path / "out" / "receipt.json")
    assert not v.ok
    msg = " ".join(d for _, _, d in v.steps)
    assert "could not run the scorer" in msg and "consilience_no_such_module_xyz" in msg
