"""Calling the scorer (spec v1.0 §6.1, S2).

`Harness(contract).score(candidate)` returns an `Outcome`:
  - `score`: the extracted number, when the scorer accepted the candidate;
  - `rejected` with `raw`: the scorer said no (an error key, a reject value, a reject file,
    a raised exception, or a non-numeric/non-finite output);
  - `timeout`: no answer within the time limit (never stored as a score);
  - `harness_error`: the harness itself could not run the scorer.

In-process kinds use one persistent worker subprocess (the scorer is imported once); `cli_json`
runs the scorer's command per call. Not a security sandbox.
"""

from __future__ import annotations

import json
import math
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np


@dataclass
class Outcome:
    score: Optional[float] = None
    rejected: bool = False
    raw: Any = None                 # what the scorer returned (or the reject value / exception text)
    timeout: bool = False
    harness_error: Optional[str] = None
    seconds: float = 0.0

    @property
    def accepted(self) -> bool:
        return self.score is not None

    def as_dict(self) -> dict:
        return {"score": self.score, "rejected": self.rejected, "raw": _tag(self.raw), "timeout": self.timeout,
                "harness_error": self.harness_error}


def _tag(o):
    if isinstance(o, float) and not math.isfinite(o):
        return {"$float": "nan" if math.isnan(o) else ("inf" if o > 0 else "-inf")}
    if isinstance(o, dict):
        return {k: _tag(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_tag(v) for v in o]
    return o


def _untag(o):
    if isinstance(o, dict):
        if set(o) == {"$float"}:
            return {"nan": math.nan, "inf": math.inf, "-inf": -math.inf}[o["$float"]]
        return {k: _untag(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_untag(v) for v in o]
    return o


_SEL = re.compile(r"^([^\[\]]+)\[([^=\]]+)=([^\]]+)\]$")


def extract(out, key: Optional[str]):
    """Follow a key path: `a.b`, and list selectors `scores[metric=sum_of_radii]`. None if absent."""
    if key is None:
        return out
    cur = out
    for part in key.split("."):
        m = _SEL.match(part)
        if m:
            name, k, v = m.groups()
            lst = cur.get(name) if isinstance(cur, dict) else None
            if not isinstance(lst, list):
                return None
            cur = next((it for it in lst if isinstance(it, dict) and str(it.get(k)) == v), None)
        else:
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def _as_number(v) -> Optional[float]:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


class HarnessError(RuntimeError):
    pass


class Harness:
    def __init__(self, contract, workdir: Optional[str] = None):
        self.c = contract
        h = contract.data["harness"]
        self.h = h
        self.kind = h["kind"]
        self.timeout = h["timeout_s"]
        self._own_dir = workdir is None
        self.dir = Path(workdir or tempfile.mkdtemp(prefix="consilience_stress_"))
        self.dir.mkdir(parents=True, exist_ok=True)
        self.proc = None
        self.calls = 0
        self.seconds = 0.0
        self.stderr_path = self.dir / "scorer_stderr.log"
        fields = contract.fields
        self.returns = [(n, fields[n]["type"]) for n in contract.data["returns"]]

    # ---------------------------------------------------------------- worker management
    def _cfg(self) -> dict:
        cfg = {"kind": self.kind, "evaluator": str(self.c.path(self.h["evaluator"])), "entry": self.h.get("entry"),
               "program_function": self.h.get("program_function"), "returns": self.returns,
               "call_args": self.h.get("call_args", {}),
               "glue": str(self.c.path(self.c.data["glue"])) if self.c.data.get("glue") else None}
        if self.kind == "template":
            cfg.update(program_template=str(self.c.path(self.h["program_template"])),
                       block_start=self.h["block_start"], block_end=self.h["block_end"])
        return cfg

    def _start(self):
        if self.proc is not None:
            return
        err = open(self.stderr_path, "ab")
        self.proc = subprocess.Popen([sys.executable, "-m", "consilience.stress._worker", json.dumps(self._cfg())],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err,
                                     text=True, bufsize=1)
        line = self._readline(max(60.0, self.timeout))
        if line is None:
            self._kill()
            raise HarnessError("the scorer did not finish importing within the time limit")
        msg = json.loads(line)
        if not msg.get("ready"):
            self._kill()
            raise HarnessError("the scorer could not be imported:\n" + msg.get("error", ""))

    def _readline(self, timeout: float) -> Optional[str]:
        r, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not r:
            return None
        line = self.proc.stdout.readline()
        return line or None

    def _kill(self):
        if self.proc is not None:
            try:
                self.proc.kill()
                self.proc.wait(timeout=5)
            except Exception:
                pass
            self.proc = None

    def close(self):
        if self.proc is not None:
            try:
                self.proc.stdin.write(json.dumps({"op": "quit"}) + "\n")
                self.proc.stdin.flush()
                self.proc.wait(timeout=5)
            except Exception:
                self._kill()
            self.proc = None
        if self._own_dir:
            shutil.rmtree(self.dir, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---------------------------------------------------------------- scoring
    def _write_npz(self, cand: dict) -> str:
        p = self.dir / f"c_{uuid.uuid4().hex[:12]}.npz"
        np.savez(p, **{k: np.asarray(v) for k, v in cand.items()})
        return str(p)

    def _judge(self, out, t0) -> Outcome:
        """Turn the scorer's raw output into an Outcome using the contract's reject rules."""
        rej = self.h["reject"]
        dt = time.time() - t0
        if isinstance(out, dict) and any(k in out for k in rej["keys_present"]):
            return Outcome(rejected=True, raw=out, seconds=dt)
        v = _as_number(extract(out, self.h.get("score_key")) if isinstance(out, dict) else out)
        if v is None:
            return Outcome(rejected=True, raw=out, seconds=dt)
        if not math.isfinite(v):
            return Outcome(rejected=True, raw=v, seconds=dt)
        if v in rej["values"]:
            return Outcome(rejected=True, raw=v, seconds=dt)
        return Outcome(score=v, raw=v, seconds=dt)

    def score(self, cand: dict) -> Outcome:
        self.calls += 1
        t0 = time.time()
        try:
            if self.kind == "cli_json":
                o = self._score_cli(cand, t0)
            else:
                o = self._score_worker(cand, t0)
        except HarnessError as exc:
            o = Outcome(harness_error=str(exc), seconds=time.time() - t0)
        self.seconds += o.seconds
        return o

    def _score_worker(self, cand: dict, t0: float) -> Outcome:
        self._start()
        npz = self._write_npz(cand)
        try:
            self.proc.stdin.write(json.dumps({"npz": npz, "dir": str(self.dir)}) + "\n")
            self.proc.stdin.flush()
        except BrokenPipeError:
            self._kill()
            raise HarnessError("the scorer process died")
        line = self._readline(self.timeout)
        try:
            os.remove(npz)
        except OSError:
            pass
        if line is None:
            self._kill()                      # a hung scorer is killed and restarted on the next call
            return Outcome(timeout=True, seconds=time.time() - t0)
        msg = json.loads(line)
        if not msg.get("ok"):
            return Outcome(rejected=True, raw={"exception": msg.get("exc"), "message": msg.get("msg")},
                           seconds=time.time() - t0)
        return self._judge(_untag(msg["out"]), t0)

    def _score_cli(self, cand: dict, t0: float) -> Outcome:
        npz = self._write_npz(cand)
        outdir = self.dir / f"out_{uuid.uuid4().hex[:10]}"
        outdir.mkdir()
        from ._worker import _program_text
        cfg = self._cfg()
        prog = self.dir / f"cand_{uuid.uuid4().hex[:12]}.py"
        prog.write_text(_program_text(cfg, npz), encoding="utf-8")
        ev = str(self.c.path(self.h["evaluator"]))
        argv = [a.replace("{evaluator}", ev).replace("{program}", str(prog)).replace("{outdir}", str(outdir))
                .replace("{python}", sys.executable) for a in self.h["argv"]]
        try:
            with open(self.stderr_path, "ab") as err:
                subprocess.run(argv, cwd=str(Path(ev).parent), stdout=err, stderr=err, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return Outcome(timeout=True, seconds=time.time() - t0)
        except OSError as exc:
            raise HarnessError(f"could not run {argv[0]!r}: {exc}")
        finally:
            for p in (npz, prog):
                try:
                    os.remove(p)
                except OSError:
                    pass
        rf = self.h["reject"].get("file")
        if rf:
            rp = Path(rf["path"].replace("{outdir}", str(outdir)))
            if rp.is_file():
                try:
                    rd = json.loads(rp.read_text(encoding="utf-8"))
                    if extract(rd, rf["key"]) == rf["equals"]:
                        shutil.rmtree(outdir, ignore_errors=True)
                        return Outcome(rejected=True, raw=rd, seconds=time.time() - t0)
                except (ValueError, OSError):
                    pass
        res = Path(self.h["result_file"].replace("{outdir}", str(outdir)))
        try:
            out = json.loads(res.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            shutil.rmtree(outdir, ignore_errors=True)
            return Outcome(rejected=True, raw={"error": "no readable result file"}, seconds=time.time() - t0)
        shutil.rmtree(outdir, ignore_errors=True)
        return self._judge(out, t0)

    def stderr_tail(self, n: int = 2000) -> str:
        try:
            return self.stderr_path.read_text(encoding="utf-8", errors="replace")[-n:]
        except OSError:
            return ""

    @property
    def mean_call_seconds(self) -> float:
        return self.seconds / self.calls if self.calls else 0.0
