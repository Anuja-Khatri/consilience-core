"""Receipts written by consilience 0.1.0 must keep verifying under later versions.

The files in tests/fixtures/receipts-0.1.0/ were written by the released 0.1.0 (from tag
v0.1.0) and are never regenerated. Several cover inputs whose verdict changed in 0.1.1
(stated precision, the unit "1", count units, inequality values), so `verify` must
re-run each receipt by the rules of the version that wrote it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from consilience import verify
from consilience.cli import main

OLD = Path(__file__).resolve().parent / "fixtures" / "receipts-0.1.0"
RECEIPTS = sorted(OLD.glob("*.json"))


def test_fixture_receipts_are_from_0_1_0():
    assert len(RECEIPTS) == 10
    for p in RECEIPTS:
        rec = json.loads(p.read_text(encoding="utf-8"))
        assert rec["consilience_version"] == "0.1.0", p.name


@pytest.mark.parametrize("path", RECEIPTS, ids=lambda p: p.name)
def test_0_1_0_receipt_verifies(path):
    v = verify(path)
    assert v.ok, (path.name, v.steps)
    assert v.recomputed_sha256 == v.recorded_sha256


@pytest.mark.parametrize("path", RECEIPTS, ids=lambda p: p.name)
def test_0_1_0_receipt_verifies_from_the_command_line(path, capsys):
    assert main(["verify", str(path)]) == 0
    assert capsys.readouterr().out.startswith(f"ok: {path}")


def test_a_new_receipt_relabelled_as_0_1_0_fails():
    from consilience import compare
    from consilience.hashing import sha256_json
    rec = compare({"value": "0.777", "unit": "1"}, {"value": 0.776943, "unit": "1"}).receipt
    rec["consilience_version"] = "0.1.0"
    rec["sha256"] = sha256_json({k: v for k, v in rec.items() if k != "sha256"})
    v = verify(rec)
    assert not v.ok and [s[0] for s in v.steps if not s[1]] == ["re-run"]


def test_0_1_0_note_names_the_rules():
    v = verify(OLD / "compare-precision.json")
    assert "by the 0.1.0 rules" in v.note
