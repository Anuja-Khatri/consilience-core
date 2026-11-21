#!/usr/bin/env python3
"""After an agent fetches ChEMBL activity records: which may be pooled, and why not.

Runs as a hook (PostToolUse). It reads the tool call from stdin, finds ChEMBL activity
records in the tool's output, or in the file the tool wrote (some ChEMBL skills
print {"output_file": ...}), and runs `consilience compare-table --map chembl --pack
bioactivity` on them. It writes the outputs and receipt under
./consilience_receipts/<time>/ and tells the agent the result in plain language.

It never blocks the tool, never changes its output, never uses the network, and stops
after 20 seconds. It always exits 0: a problem is reported as one line of context.

    --claude              Claude Code: context returned as hookSpecificOutput
    --antigravity-post    Antigravity PostToolUse (gets no tool output; reads the file
                          named by --output in the command; leaves the summary pending)
    --antigravity-inject  Antigravity PreInvocation: injects a pending summary once
    --file PATH           run on a file directly (used by /check-pooling)
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shlex
import signal
import sys
from pathlib import Path

TIME_LIMIT = 20
PENDING = "consilience_receipts/.pending_summary.txt"


class _Timeout(Exception):
    pass


def _alarm(signum, frame):  # noqa: ARG001
    raise _Timeout()


def _activities(obj):
    """(records, total_count) if obj looks like ChEMBL activity data, else (None, None)."""
    total = None
    if isinstance(obj, dict):
        total = (obj.get("page_meta") or {}).get("total_count")
        obj = obj.get("activities", obj.get("records"))
    if isinstance(obj, list) and obj and all(isinstance(r, dict) for r in obj):
        if any("standard_relation" in r and "standard_type" in r for r in obj):
            return obj, total
    return None, None


def _load(path: str):
    p = Path(path)
    if not p.is_file() or p.stat().st_size > 200_000_000:
        return None, None
    try:
        return _activities(json.loads(p.read_text(encoding="utf-8")))
    except (ValueError, UnicodeDecodeError):
        return None, None


def _output_path_from_command(cmd: str):
    try:
        parts = shlex.split(cmd)
    except ValueError:
        parts = cmd.split()
    for i, x in enumerate(parts):
        if x == "--output" and i + 1 < len(parts):
            return parts[i + 1]
        if x.startswith("--output="):
            return x.split("=", 1)[1]
    return None


def find_records(event: dict):
    """From a Claude Code PostToolUse event: the records and the page's total_count."""
    resp = event.get("tool_response")
    texts = []
    if isinstance(resp, dict):
        texts.append(resp.get("stdout") or "")
        recs, total = _activities(resp)
        if recs:
            return recs, total
    elif isinstance(resp, str):
        texts.append(resp)
    elif isinstance(resp, list):   # MCP tools: list of content blocks
        texts.extend(b.get("text", "") for b in resp if isinstance(b, dict))
    for t in texts:
        t = t.strip()
        if not t:
            continue
        try:
            obj = json.loads(t)
        except ValueError:
            m = re.search(r'"output_file"\s*:\s*"([^"]+)"', t)
            obj = {"output_file": m.group(1)} if m else None
        if obj is None:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("output_file"), str):
            recs, total = _load(obj["output_file"])
            if recs:
                return recs, total
        recs, total = _activities(obj)
        if recs:
            return recs, total
    cmd = (event.get("tool_input") or {}).get("command") or ""
    out = _output_path_from_command(cmd)
    if out:
        return _load(out)
    return None, None


def check(records, total, cwd: str) -> str:
    from consilience.table import compare_table
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(cwd) / "consilience_receipts" / stamp
    r = compare_table(records, map="chembl", pack="bioactivity", out=out)
    lines = [r.text]
    if isinstance(total, int) and total > len(records):
        lines.append(f"- This fetch holds {len(records)} of the {total} matching records in "
                     "ChEMBL. Pooling decisions need all records: fetch every page, then "
                     "run /check-pooling on the combined file.")
    na = r.summary["not_checked_column_absent"]
    assay_only = [x for x in ("BA3", "BA4", "BA5", "BA6", "BA7", "BA8", "BA9", "BR2")
                  if x in na["conditions"] + na["record_rules"]]
    if assay_only:
        lines.append("- Not checked here: assay organism, category, strain, tissue, cell "
                     "type, subcellular fraction and confidence score. They come from "
                     "ChEMBL's assay records (/assay), not from activity records.")
    lines.append(f"- Outputs and receipt: {out}/ (re-check with: consilience verify "
                 f"{out}/receipt.json)")
    return "\n".join(lines)


def main(argv) -> int:
    mode = argv[1] if len(argv) > 1 else "--claude"
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(TIME_LIMIT)
    try:
        if mode == "--antigravity-inject":
            ev = json.loads(sys.stdin.read() or "{}")
            base = (ev.get("workspacePaths") or [os.getcwd()])[0]
            p = Path(base) / PENDING
            if p.is_file():
                text = p.read_text(encoding="utf-8")
                p.unlink()
                print(json.dumps({"injectSteps": [{"ephemeralMessage": text}]}))
            else:
                print("{}")
            return 0
        if mode == "--file":
            recs, total = _load(argv[2])
            if not recs:
                print(f"consilience: no ChEMBL activity records found in {argv[2]}")
                return 0
            print(check(recs, total, os.getcwd()))
            return 0
        ev = json.loads(sys.stdin.read() or "{}")
        if mode == "--antigravity-post":
            args = (ev.get("toolCall") or {}).get("args") or {}
            cwd = args.get("Cwd") or (ev.get("workspacePaths") or [os.getcwd()])[0]
            out = _output_path_from_command(args.get("CommandLine") or "")
            recs, total = _load(os.path.join(cwd, out)) if out else (None, None)
            if recs:
                text = check(recs, total, cwd)
                p = Path(cwd) / PENDING
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
            print("{}")
            return 0
        recs, total = find_records(ev)
        if not recs:
            return 0                     # not ChEMBL activity data: say nothing
        text = check(recs, total, ev.get("cwd") or os.getcwd())
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": text}}))
    except _Timeout:
        _say(mode, "consilience pooling check: stopped after 20 s (large fetch); run "
                   "/check-pooling on the file instead.")
    except ImportError:
        _say(mode, "consilience pooling check: the consilience package is not installed "
                   "(pip install 'consilience>=0.2').")
    except Exception as exc:  # noqa: BLE001 (reported in one line, never raised)
        _say(mode, f"consilience pooling check could not run: {type(exc).__name__}: "
                   f"{str(exc)[:200]}")
    finally:
        signal.alarm(0)
    return 0


def _say(mode: str, text: str) -> None:
    if mode == "--claude":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": text}}))
    elif mode == "--file":
        print(text)
    else:
        print("{}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
