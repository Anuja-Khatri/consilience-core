"""The Python API. It mirrors the command line:

    from consilience import compare, check, verify, load_rules

    r = compare("measurement_a.json", "measurement_b.json", pack="electrochemistry")
    r.verdict, r.label, r.exit_code, r.receipt          # receipt: a dict with "sha256"

    c = check("readings.csv", "readings_rules.yaml")
    c.summary, c.violations, c.unparseable, c.to_html()

    v = verify(r.receipt)                               # or a receipt file path
    v.ok, v.steps

    rules = load_rules("electrochemistry")              # or a path to a YAML file
    rules.name, rules.version, rules.sha256

Errors in the inputs themselves raise ``InputError`` (a missing file, an unknown field,
an unusable option) or ``RuleFileError`` (an unusable rule file). Everything that can
be read but not compared is a verdict, not an exception.
"""

from __future__ import annotations

from .check import CheckResult, check
from .compare import CompareResult, InputError, compare
from .rules import BUNDLED_PACKS, RuleFileError, RuleSet, load_rules
from .units import UnitError
from .verify import VerifyResult, verify

__all__ = ["compare", "check", "verify", "load_rules", "CompareResult", "CheckResult",
           "VerifyResult", "RuleSet", "InputError", "RuleFileError", "UnitError",
           "BUNDLED_PACKS"]
