"""Acceptance test A1 (spec v1.0 §12): the pre-lock pilot's cases give the same verdicts and finding
kinds through the shipped command. Slow (several minutes); runs when CONSILIENCE_SLOW=1.

One recorded difference (build plan §5, proposed change 1): the equidistant C3 finding was found by the
prototype at the standard budget in 1 of 6 seeds (seed 0 was lucky). At the standard budget the engine
finds the C1 sentinel only; the C3 exploit is checked here at the large budget, where it was found in
3 of 3 seeds.
"""
import os
from pathlib import Path

import pytest

from consilience.stress import stress

PILOT = Path(__file__).resolve().parent.parent / "benchmarks" / "evaluator-stress" / "pilot"
slow = pytest.mark.skipif(os.environ.get("CONSILIENCE_SLOW") != "1", reason="slow acceptance test; set CONSILIENCE_SLOW=1")

EXPECTED = {
    "dm_amgm": ("PASS", set(), "claim_within_rounding"),
    "dm_equidistant": ("BLOCK", {("C1", "sentinel_is_best")}, None),
    "dm_diffbases": ("BLOCK", {("C4", "invariance_broken_integer")}, None),
    "oe_c3_post": ("BLOCK", {("C2", "trusts_self_report")}, None),
    "oe_c1_pre": ("BLOCK", {("C1", "accepts_gross_invalid")}, None),
    "oe_c1_post": ("PASS", set(), None),
    "oe_erdos_pre": ("BLOCK", {("C2", "trusts_self_report")}, None),
    "oe_erdos_post": ("PASS", set(), None),
    "oe_cpr_pre": ("BLOCK", {("C1", "accepts_gross_invalid")}, None),
    "oe_cpr_post": ("PASS", set(), None),
}


@slow
@pytest.mark.parametrize("case", sorted(EXPECTED))
def test_a1_standard_budget(case, tmp_path):
    verdict, blocks, c5 = EXPECTED[case]
    r = stress(PILOT / case / "contract.yaml", budget="standard", seed=0, out=tmp_path / "o")
    got = {(f.check, f.kind) for f in r.result.findings if f.block}
    assert r.verdict == verdict, (r.verdict, got)
    assert got == blocks
    if c5:
        assert r.result.c5["verdict"] == c5
    from consilience.verify import verify
    assert verify(tmp_path / "o" / "receipt.json").ok


@slow
def test_a1_equidistant_c5_shipped_best():
    r = stress(PILOT / "dm_equidistant" / "contract_c5.yaml", budget="small", seed=0, only=["C5"])
    assert r.result.c5["verdict"] == "within_resolution"


@slow
def test_a1_equidistant_c3_large_budget():
    r = stress(PILOT / "dm_equidistant" / "contract.yaml", budget="large", seed=0, only=["C3"])
    kinds = {(f.check, f.kind) for f in r.result.findings if f.block}
    assert ("C3", "exploitable_invalid") in kinds
