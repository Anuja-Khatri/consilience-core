"""Build examples/stress_demo.ipynb (run once; the executed notebook is committed).

    python examples/make_stress_notebook.py
    jupyter nbconvert --to notebook --execute --inplace examples/stress_demo.ipynb
"""

from pathlib import Path

import nbformat as nbf

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells = [
    md("""# `consilience stress`: checking scoring code before a search runs

An optimiser such as AlphaEvolve, OpenEvolve or ShinkaEvolve will exploit any loophole in its
scoring function. `consilience stress` takes the scorer plus a short contract (what a valid answer is,
which transformations must not change the score, the published record) and looks for a
counterexample *before* the search runs. Every result has a receipt that `verify` re-checks.

This notebook runs real cases from `benchmarks/evaluator-stress/`, all on published code at
pinned commits (`SOURCES.yaml`):

1. a publicly reported bug, before and after its fix (non-finite input);
2. a scorer that trusts a number the candidate reports about itself;
3. a claimed record that is within the scorer's own rounding (check C5);
4. re-checking two stored findings on DeepMind's problem notebooks without re-running the search.

What it is not: a proof (PASS means no counterexample within the budget), a security sandbox, or a
discovery engine for deep loopholes. See `docs/stress.md` and `benchmarks/evaluator-stress/results/RESULTS.md`."""),
    code("""import json, tempfile, time
from pathlib import Path
from consilience import __version__, verify
from consilience.stress import stress

ROOT = Path.cwd().parent if Path.cwd().name == "examples" else Path.cwd()
B = ROOT / "benchmarks" / "evaluator-stress"
OUT = Path(tempfile.mkdtemp(prefix="stress_demo_"))
print("consilience", __version__)

def run(rel, budget="standard"):
    t = time.time()
    r = stress(B / rel / "contract.yaml", budget=budget, out=OUT / rel.replace("/", "_"))
    print(r.text)
    print(f"[{time.time() - t:.0f} s, exit code {r.exit_code}]")
    return r"""),
    md("""## 1. A reported bug, before and after its fix

OpenEvolve issue #548: the circle-packing-in-a-rectangle evaluator accepted NaN radii. The contract
says radii are finite and non-negative; check C1 feeds invalid inputs and asks whether the scorer
accepts them and whether an optimiser could profit."""),
    code("""pre = run("contracts/LABELS/oe548_cpr_pre")"""),
    code("""post = run("contracts/LABELS/oe548_cpr_post")"""),
    md("""## 2. A scorer that trusts a self-reported value

OpenEvolve issue #562 (Erdős minimum overlap): the program returns its own claimed bound, and the
pre-fix evaluator scores that claim instead of recomputing it. Check C2 perturbs only the reported
value and watches the score move."""),
    code("""erdos = run("contracts/LABELS/oe562_erdos_pre")"""),
    md("""## 3. A claimed record within rounding (C5)

From the pre-lock pilot: a float "counterexample" to a matrix AM-GM inequality scores +1.9e-6 under
the published `get_score`, but is negative at 60 digits. As a claim it does not clear the scorer's
own invariance noise, so C5 rates it `claim_within_rounding`. (The tool did not find this candidate
by search; it was supplied as the claim.)"""),
    code("""amgm = run("pilot/dm_amgm")"""),
    md("""## 4. Re-checking stored findings without re-running the search

`verify` recomputes each BLOCK's deciding inequality from the receipt, the stored candidate and the
hashed scorer. These two concern DeepMind's AlphaEvolve problem notebooks (commit 8f44745):

- `flat_polynomials` C⁻: the coefficients are not checked to be ±1, and scaling them improves the score;
- `equidistant_points_in_convex_polygons` at the `large` budget: a wrong vertex count returns +1e9, and
  non-convex point sets score better than AlphaEvolve's construction."""),
    code("""for rel in ["results/receipts/DM/flat_polynomials_c_minus/receipt.json",
            "results/extra/receipts/DM/equidistant_points_in_convex_polygons_large/receipt.json"]:
    v = verify(B / rel)
    print(rel, "->", "OK" if v.ok else "FAILED")
    for name, ok, note in v.steps:
        print(f"   {'ok ' if ok else 'BAD'} {name}: {note}")"""),
    md("""## 5. Summary of this notebook's runs"""),
    code("""for name, r in [("oe548 pre", pre), ("oe548 post", post), ("oe562 pre", erdos), ("AM-GM claim", amgm)]:
    print(f"{name:12s} {r.verdict}")
print("receipts written under", OUT)"""),
]

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
Path(__file__).with_name("stress_demo.ipynb").write_text(nbf.writes(nb), encoding="utf-8")
print("wrote stress_demo.ipynb")
