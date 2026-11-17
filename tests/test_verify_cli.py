"""`verify` re-runs receipts; the command line keeps its documented exit codes; the core
package works without the optional nanopub dependencies. Example data is made up."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from consilience import check, compare, verify
from consilience.cli import EXAMPLE_FILES, main
from consilience.compare import InputError
from conftest import ROOT

PILOT_RECORDS = sorted((ROOT / "pilot" / "records").glob("*.json"))


@pytest.fixture
def ex(tmp_path, monkeypatch):
    assert main(["examples", str(tmp_path)]) == 0
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ------------------------------------------------------------------ verify
def test_compare_receipt_round_trip(ex):
    r = compare("measurement_a.json", "measurement_b.json", pack="electrochemistry",
                floor="13 mV")
    v = verify(r.receipt)
    assert v.ok and v.recomputed_sha256 == r.receipt["sha256"]


def test_edited_receipt_fails(ex):
    rec = compare("measurement_a.json", "measurement_b.json", pack="electrochemistry").receipt
    rec["result"]["verdict"] = "agree"
    v = verify(rec)
    assert not v.ok and v.exit_code == 1
    assert [s[0] for s in v.steps if not s[1]] == ["receipt hash", "re-run"]


def test_edited_input_with_rehashed_receipt_fails_on_rerun(ex):
    from consilience.hashing import sha256_json
    rec = compare("measurement_a.json", "measurement_b.json").receipt
    rec["inputs"]["b"]["value"] = 320
    rec["sha256"] = sha256_json({k: v for k, v in rec.items() if k != "sha256"})
    v = verify(rec)
    assert not v.ok and [s[0] for s in v.steps if not s[1]] == ["re-run"]


def test_edited_pack_fails(ex):
    from consilience.hashing import sha256_json
    rec = compare("measurement_a.json", "measurement_b.json", pack="electrochemistry").receipt
    rec["pack"]["content"]["conditions"] = rec["pack"]["content"]["conditions"][:1]
    rec["sha256"] = sha256_json({k: v for k, v in rec.items() if k != "sha256"})
    assert not verify(rec).ok


def test_check_receipt_round_trip_and_changed_data(ex):
    c = check("readings.csv", "readings_rules.yaml")
    Path("check.json").write_text(json.dumps(c.receipt))
    assert verify("check.json").ok
    data = Path("readings.csv")
    data.write_text(data.read_text().replace("S-004,2.71", "S-004,2.41"))
    v = verify("check.json")
    assert not v.ok and [s[0] for s in v.steps if not s[1]] == ["data hash", "re-run"]


def test_check_receipt_finds_data_next_to_the_receipt_or_by_flag(ex, tmp_path, monkeypatch):
    c = check("readings.csv", "readings_rules.yaml")
    (ex / "r.json").write_text(json.dumps(c.receipt))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert verify(ex / "r.json").ok            # found beside the receipt
    moved = elsewhere / "moved.csv"
    shutil.move(str(ex / "readings.csv"), moved)
    with pytest.raises(InputError, match="--data"):
        verify(ex / "r.json")
    assert verify(ex / "r.json", data=moved).ok


def test_not_a_receipt_is_an_input_error(ex):
    with pytest.raises(InputError):
        verify("measurement_a.json")
    assert main(["verify", "measurement_a.json"]) == 64


@pytest.mark.parametrize("record", PILOT_RECORDS[:3], ids=lambda p: p.name)
def test_nanopub_record_envelopes_still_verify(record):
    v = verify(record)
    assert v.ok and v.command == "record-envelope"
    assert main(["verify", str(record)]) == 0


# ------------------------------------------------------------------ CLI exit codes
@pytest.mark.parametrize("args,code", [
    (["compare", "measurement_a.json", "measurement_b.json", "--pack", "electrochemistry"], 1),
    (["compare", "measurement_a.json", "measurement_b.json", "--pack", "electrochemistry",
      "--floor", "13 mV"], 0),
    (["compare", "measurement_a.json", "measurement_b.json", "--pack", "electrochemistry",
      "--abs-tol", "15 mV"], 0),
    (["compare", "measurement_a.json", "measurement_c.json", "--pack", "electrochemistry"], 2),
    (["compare", "measurement_a.json", "measurement_d.json", "--pack", "electrochemistry"], 2),
    (["compare", "measurement_a.json", "measurement_e.json", "--pack", "electrochemistry"], 3),
    (["compare", "measurement_a.json", "measurement_b.json"], 2),
    (["compare", "measurement_a.json", "electrochemistry.yaml"], 64),
    (["compare", "measurement_a.json", "missing.json"], 64),
    (["compare", "measurement_a.json", "measurement_b.json", "--pack", "nope"], 64),
    (["compare", "measurement_a.json", "measurement_b.json", "--abs-tol", "1,5 mV"], 64),
    (["check", "readings.csv", "--rules", "readings_rules.yaml"], 3),
    (["check", "readings.csv", "--rules", "electrochemistry.yaml"], 64),
    (["check", "missing.csv", "--rules", "readings_rules.yaml"], 64),
    (["compare", "measurement_a.json", "measurement_b.json", "--pack",
      "./electrochemistry.yaml"], 1),
    ([], 64),
])
def test_cli_exit_codes(ex, args, code, capsys):
    assert main(args) == code


def test_cli_usage_errors_exit_64(ex):
    for argv in (["check", "readings.csv"], ["compare", "only_one.json"], ["frobnicate"]):
        r = subprocess.run([sys.executable, "-m", "consilience", *argv], cwd=ex,
                           capture_output=True, text=True)
        assert r.returncode == 64, (argv, r.stderr)


def test_cli_json_html_and_receipt(ex, capsys):
    assert main(["check", "readings.csv", "--rules", "readings_rules.yaml", "--json",
                 "--html", "report.html", "--receipt", "r.json"]) == 3
    out = json.loads(capsys.readouterr().out)
    assert out["result"]["summary"]["violations"] == 5
    assert out["result"]["summary"]["unparseable_cells"] == 2
    assert json.loads(Path("r.json").read_text())["sha256"] == out["sha256"]
    assert "S-004" in Path("report.html").read_text()
    assert main(["verify", "r.json"]) == 0


def test_examples_refuse_to_overwrite(ex):
    assert main(["examples", str(ex)]) == 64
    assert main(["examples", str(ex), "--force"]) == 0
    for name in EXAMPLE_FILES:
        text = (ex / name).read_text()
        assert "MADE-UP" in text or "MADE UP" in text, name


def test_core_needs_no_nanopub_dependencies(ex):
    code = ("import sys, consilience\n"
            "r = consilience.compare('measurement_a.json', 'measurement_b.json', "
            "pack='electrochemistry')\n"
            "c = consilience.check('readings.csv', 'readings_rules.yaml')\n"
            "from consilience import cli\n"
            "heavy = [m for m in ('rdflib', 'nanopub', 'Crypto', 'requests') "
            "if m in sys.modules]\n"
            "assert not heavy, heavy\n"
            "print(r.verdict, c.exit_code)\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=ex, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["disagree", "3"]
