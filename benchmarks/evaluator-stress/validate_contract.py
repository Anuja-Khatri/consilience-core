"""Validate benchmark contracts WITHOUT running any stress check (step 4: no results before preregistration).

    python benchmarks/evaluator-stress/validate_contract.py <contract.yaml> [...]

For each contract: it loads (named errors), the reference (and initial / claimed_best, if given) passes the
contract's own validity rules, and the scorer accepts the reference (one call). It prints the reference
score. Nothing else is run.
"""
import sys
from pathlib import Path

import numpy as np

from consilience.stress.checks import Runner
from consilience.stress.contract import ContractError, load_contract
from consilience.stress.harness import Harness
from consilience.stress.validity import violations


def check(path: str) -> bool:
    try:
        c = load_contract(path)
    except ContractError as exc:
        print(f"FAIL {path}: contract: {exc}")
        return False
    ok = True
    with Harness(c) as h:
        R = Runner(c, h, seed=0, budget="small")
        for key in ("reference", "initial", "claimed_best"):
            if not c.data.get(key):
                continue
            cand = R.complete(dict(np.load(c.path(c.data[key]["file"]), allow_pickle=False)))
            v = violations(c, cand)
            if v and key != "claimed_best":
                print(f"FAIL {path}: {key} breaks the contract's own rules: {[x.rule for x in v]}")
                ok = False
                continue
            o = h.score(cand)
            if o.harness_error:
                print(f"FAIL {path}: harness: {o.harness_error[:500]}\n{h.stderr_tail(800)}")
                return False
            if key == "reference" and not o.accepted:
                print(f"FAIL {path}: the scorer rejects the reference: {str(o.raw)[:300]}")
                ok = False
            else:
                print(f"  {key}: score {o.score}" + (f" (invalid by contract: {[x.rule for x in v]})" if v else ""))
    if ok:
        print(f"OK   {path}")
    return ok


if __name__ == "__main__":
    results = [check(p) for p in sys.argv[1:]]
    sys.exit(0 if all(results) else 1)
