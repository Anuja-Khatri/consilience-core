#!/usr/bin/env python3
"""After an agent writes or edits a scoring file: stress-test it, if it has a contract.

Runs as a hook (PostToolUse on Write/Edit). It reads the tool call from stdin, takes the edited
file's path, and looks in the same folder for a contract (`contract.yaml` or `*.contract.yaml`)
whose `harness.evaluator` IS that file, or whose `glue`/`harness.extra_files` include it. If
there is one, it runs `consilience stress <contract> --budget small` and tells the agent the
verdict and where the counterexamples are. With no contract it does nothing.

It never blocks the tool, never changes files other than its own receipt folder
(./consilience_receipts/stress/<time>/), never uses the network, and always exits 0: a problem
is reported as one line of context.

    --claude              Claude Code: context returned as hookSpecificOutput
    --antigravity-post    Antigravity PostToolUse: runs the check, leaves the summary pending
    --antigravity-inject  Antigravity PreInvocation: injects a pending summary once
    --contract PATH       run on a contract directly (used by /stress-check)
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

TIME_LIMIT = 280
PENDING = "consilience_receipts/stress/.pending_summary.txt"


def _contracts_for(edited: Path):
    """Contracts in the edited file's folder that use this file."""
    try:
        import yaml
    except ImportError:
        return []
    out = []
    folder = edited.parent
    for c in sorted(list(folder.glob("contract.yaml")) + list(folder.glob("*.contract.yaml"))):
        try:
            data = yaml.safe_load(c.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if data.get("kind") != "evaluator-contract":
            continue
        h = data.get("harness") or {}
        used = [h.get("evaluator"), data.get("glue")] + list(h.get("extra_files") or [])
        if any(u and (folder / u).resolve() == edited.resolve() for u in used):
            out.append(c)
    return out


def _run(contract: Path) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path.cwd() / "consilience_receipts" / "stress" / stamp
    cmd = [sys.executable, "-m", "consilience", "stress", str(contract), "--budget", "small", "--out", str(out)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIME_LIMIT)
    except subprocess.TimeoutExpired:
        return (f"Consilience stress check on {contract.name}: stopped after {TIME_LIMIT} s (small budget). "
                f"Run it yourself without a time limit: consilience stress {contract}")
    except OSError as exc:
        return f"Consilience stress check could not start: {exc}"
    if p.returncode == 64:
        return f"Consilience stress check on {contract.name}: the contract has a problem: {p.stderr.strip()[-600:]}"
    text = p.stdout.strip()
    lines = [l for l in text.splitlines() if not l.startswith(("wrote:", "receipt: sha256"))]
    return ("Consilience stress check (small budget) after this edit:\n" + "\n".join(lines[:40]) +
            f"\nReceipt and counterexamples: {out} (re-check with: consilience verify {out}/receipt.json)")


def main(argv) -> int:
    mode = argv[1] if len(argv) > 1 else "--claude"
    try:
        if mode == "--contract":
            print(_run(Path(argv[2])))
            return 0
        if mode == "--antigravity-inject":
            p = Path(PENDING)
            if p.is_file():
                text = p.read_text(encoding="utf-8")
                p.unlink()
                print(json.dumps({"injectSteps": [{"ephemeralMessage": text}]}))
            else:
                print("{}")
            return 0
        event = json.loads(sys.stdin.read() or "{}")
        ti = event.get("tool_input") or event.get("toolInput") or {}
        path = ti.get("file_path") or ti.get("path") or ti.get("TargetFile") or ti.get("target_file")
        if not path:
            print("{}")
            return 0
        edited = Path(path)
        contracts = _contracts_for(edited)
        if not contracts:
            print("{}")
            return 0
        text = "\n\n".join(_run(c) for c in contracts[:2])
        if mode == "--antigravity-post":
            Path(PENDING).parent.mkdir(parents=True, exist_ok=True)
            Path(PENDING).write_text(text, encoding="utf-8")
            print("{}")
            return 0
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}))
    except Exception as exc:  # never break the agent's turn
        msg = f"Consilience stress hook problem (ignored): {type(exc).__name__}: {exc}"
        if mode == "--claude":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
        else:
            print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
