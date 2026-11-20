"""The agent plugin's hook (integrations/agent-plugin/consilience-pooling), run as an agent
platform runs it: a subprocess fed a PostToolUse event on stdin. Exit code always 0."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1] / "integrations" / "agent-plugin" / \
    "consilience-pooling"
HOOK = PLUGIN / "hooks" / "after_fetch.py"


def acts(n_pairs=3, total=None):
    rows = []
    for i in range(n_pairs):
        rows.append({"activity_id": 10 + i, "parent_molecule_chembl_id": "CHEMBL1",
                     "target_chembl_id": "CHEMBL203", "standard_type": "IC50",
                     "standard_relation": "=", "standard_value": str(40 + i),
                     "standard_units": "nM", "assay_type": "B" if i else "F",
                     "bao_format": "BAO_0000357", "data_validity_comment": None,
                     "assay_variant_mutation": None})
    rows.append(dict(rows[0], activity_id=99, standard_relation=">", standard_value="10000"))
    d = {"activities": rows}
    if total is not None:
        d["page_meta"] = {"total_count": total, "limit": len(rows), "offset": 0}
    return d


def run(event, mode="--claude", cwd=None):
    t = time.time()
    p = subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps(event),
                       capture_output=True, text=True, cwd=cwd, timeout=60)
    return p, time.time() - t


def test_manifest_and_hook_files_are_valid_json():
    m = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert m["name"] == "consilience-pooling"
    h = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert "PostToolUse" in h["hooks"]
    ag = json.loads((PLUGIN / "hooks.json").read_text(encoding="utf-8"))
    assert set(ag["consilience-pooling"]) == {"PostToolUse", "PreInvocation"}
    for f in ("skills/check-pooling/SKILL.md", "commands/check-pooling.md", "README.md"):
        assert (PLUGIN / f).is_file()


def test_deepmind_skill_status_json_naming_output_file(tmp_path):
    out = tmp_path / "egfr.json"
    out.write_text(json.dumps(acts(total=26600)), encoding="utf-8")
    # exactly what chembl_api.py's _write_json prints after writing the file
    stdout = json.dumps({"status": "success", "output_file": str(out),
                         "size_bytes": out.stat().st_size,
                         "license_notice": "Data from the ChEMBL Database."}, indent=2)
    ev = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": str(tmp_path),
          "tool_input": {"command": f"uv run scripts/chembl_api.py activity --filter "
                                    f"target_chembl_id=CHEMBL203 standard_type=IC50 --limit 5 "
                                    f"--output {out}"},
          "tool_response": {"stdout": stdout, "stderr": "", "interrupted": False,
                            "isImage": False}}
    p, _ = run(ev, cwd=tmp_path)
    assert p.returncode == 0
    ctx = json.loads(p.stdout)["hookSpecificOutput"]
    assert ctx["hookEventName"] == "PostToolUse"
    text = ctx["additionalContext"]
    assert "Consilience pooling check" in text
    assert "of the 26600 matching records" in text          # partial fetch said
    assert "not_comparable(assay_type)" in text
    assert "Not checked here: assay organism" in text
    receipts = list((tmp_path / "consilience_receipts").glob("*/receipt.json"))
    assert len(receipts) == 1
    from consilience import verify
    assert verify(receipts[0]).ok


def test_inline_activity_json(tmp_path):
    ev = {"tool_name": "mcp__chembl__get_activities", "cwd": str(tmp_path),
          "tool_response": [{"type": "text", "text": json.dumps(acts())}]}
    p, _ = run(ev, cwd=tmp_path)
    assert p.returncode == 0
    assert "pool_valid" in json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]


def test_output_path_found_from_the_command(tmp_path):
    out = tmp_path / "a.json"
    out.write_text(json.dumps(acts()), encoding="utf-8")
    ev = {"tool_name": "Bash", "cwd": str(tmp_path),
          "tool_input": {"command": f"python fetch.py --output {out}"},
          "tool_response": {"stdout": "done\n", "stderr": ""}}
    p, _ = run(ev, cwd=tmp_path)
    assert p.returncode == 0 and "Consilience pooling check" in p.stdout


@pytest.mark.parametrize("resp", [
    {"stdout": "total 0\n-rw-r--r-- a.txt\n", "stderr": ""},
    {"stdout": json.dumps({"molecules": [{"molecule_chembl_id": "CHEMBL25"}]}), "stderr": ""},
    {"stdout": "", "stderr": "error"},
])
def test_non_matching_output_is_silent_and_fast(tmp_path, resp):
    ev = {"tool_name": "Bash", "cwd": str(tmp_path), "tool_input": {"command": "ls"},
          "tool_response": resp}
    p, secs = run(ev, cwd=tmp_path)
    assert p.returncode == 0 and p.stdout == ""
    assert secs < 3   # interpreter start included; the hook itself returns at once


def test_malformed_input_is_one_line_and_exit_0(tmp_path):
    p = subprocess.run([sys.executable, str(HOOK), "--claude"], input="{not json",
                       capture_output=True, text=True, cwd=tmp_path, timeout=60)
    assert p.returncode == 0
    msg = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
    assert msg.startswith("consilience pooling check could not run")


def test_antigravity_post_then_inject(tmp_path):
    out = tmp_path / "act.json"
    out.write_text(json.dumps(acts()), encoding="utf-8")
    post = {"toolCall": {"name": "run_command",
                         "args": {"CommandLine": "python chembl_api.py activity --output act.json",
                                  "Cwd": str(tmp_path)}},
            "workspacePaths": [str(tmp_path)]}
    p, _ = run(post, mode="--antigravity-post", cwd=tmp_path)
    assert p.returncode == 0 and json.loads(p.stdout) == {}
    inj, _ = run({"workspacePaths": [str(tmp_path)]}, mode="--antigravity-inject",
                 cwd=tmp_path)
    steps = json.loads(inj.stdout)["injectSteps"]
    assert "Consilience pooling check" in steps[0]["ephemeralMessage"]
    again, _ = run({"workspacePaths": [str(tmp_path)]}, mode="--antigravity-inject",
                   cwd=tmp_path)
    assert json.loads(again.stdout) == {}          # shown once only


def test_file_mode_for_the_command(tmp_path):
    out = tmp_path / "act.json"
    out.write_text(json.dumps(acts()), encoding="utf-8")
    p = subprocess.run([sys.executable, str(HOOK), "--file", str(out)], capture_output=True,
                       text=True, cwd=tmp_path, timeout=60)
    assert p.returncode == 0 and "Consilience pooling check" in p.stdout
