"""consilience: compare two measurements with units and conditions, and check a table
against written limits. Every result carries a receipt that ``verify`` can re-run.

    from consilience import compare, check, verify, load_rules

The nanopublication exporter (``consilience.export``) is a separate, optional part:
``pip install "consilience[nanopub]"``.
"""

__version__ = "0.2.0.dev0"

from .api import (  # noqa: E402
    BUNDLED_PACKS,
    CheckResult,
    CompareResult,
    InputError,
    RuleFileError,
    RuleSet,
    UnitError,
    VerifyResult,
    check,
    compare,
    load_rules,
    verify,
)

__all__ = ["__version__", "compare", "check", "verify", "load_rules", "CompareResult",
           "CheckResult", "VerifyResult", "RuleSet", "InputError", "RuleFileError",
           "UnitError", "BUNDLED_PACKS"]
