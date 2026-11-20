"""Run the preregistered benchmark (build step 5). Do not run before PREREGISTRATION.md is committed.

    python benchmarks/evaluator-stress/run_benchmark.py [--budget standard] [--seed 0] [--jobs 3] [--only SET/slug ...]

Runs `consilience stress` on every contract under contracts/ (one process per contract), writes each receipt
to results/receipts/<SET>/<slug>/, and collects results/results.json and results/per_evaluator.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACTS = HERE / "contracts"
RESULTS = HERE / "results"


def discover(only=None):
    out = []
    for p in sorted(CONTRACTS.glob("*/*/contract.yaml")):
        key = f"{p.parent.parent.name}/{p.parent.name}"
        if only and key not in only:
            continue
        out.append((key, p))
    return out


def run_one(key, path, budget, seed, timeout):
    out = RESULTS / "receipts" / key
    if out.exists():
        import shutil
        shutil.rmtree(out)
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-m", "consilience", "stress", str(path), "--budget", budget,
                            "--seed", str(seed), "--out", str(out)], capture_output=True, text=True, timeout=timeout)
        code, text = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        code, text = -1, f"benchmark wall-clock limit of {timeout}s reached"
    dt = time.time() - t0
    rec = None
    rp = out / "receipt.json"
    if rp.is_file():
        rec = json.loads(rp.read_text(encoding="utf-8"))
    return {"key": key, "exit": code, "seconds": round(dt, 1), "text": text[-4000:], "receipt": rec}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", default="standard")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=5400, help="wall-clock limit per contract (s)")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    items = discover(set(a.only) if a.only else None)
    RESULTS.mkdir(exist_ok=True)
    print(f"{len(items)} contracts; budget {a.budget}; seed {a.seed}; jobs {a.jobs}", flush=True)
    rows = []
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futs = [ex.submit(run_one, k, p, a.budget, a.seed, a.timeout) for k, p in items]
        for f in futs:
            r = f.result()
            rec = r["receipt"] or {}
            blocks = sorted({(x["check"], x["kind"]) for x in rec.get("findings", []) if x.get("block")})
            reported = sorted({(x["check"], x["kind"]) for x in rec.get("reported", [])})
            row = {"key": r["key"], "verdict": rec.get("verdict", "NO_RECEIPT"), "exit": r["exit"], "seconds": r["seconds"],
                   "blocks": ";".join(f"{c}:{k}" for c, k in blocks),
                   "reported": ";".join(f"{c}:{k}" for c, k in reported),
                   "abstain": ";".join(x["reason"] for x in rec.get("abstain_reasons", [])),
                   "c5": (rec.get("C5") or {}).get("verdict", ""),
                   "m": (rec.get("info") or {}).get("m", ""), "margin_source": (rec.get("info") or {}).get("margin_source", ""),
                   "calls": (rec.get("info") or {}).get("calls", ""),
                   "scaled_budget": json.dumps((rec.get("info") or {}).get("scaled_budget", "")),
                   "receipt_sha256": rec.get("sha256", "")}
            rows.append(row)
            print(f"{row['key']:55s} {row['verdict']:8s} {row['seconds']:7.1f}s {row['blocks']}", flush=True)
            if row["verdict"] == "NO_RECEIPT":
                print("   " + r["text"][-600:].replace("\n", "\n   "), flush=True)
    with (RESULTS / "per_evaluator.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (RESULTS / "results.json").write_text(json.dumps({"budget": a.budget, "seed": a.seed, "rows": rows}, indent=1) + "\n",
                                          encoding="utf-8")
    print(f"wrote {RESULTS / 'per_evaluator.csv'}")


if __name__ == "__main__":
    main()
