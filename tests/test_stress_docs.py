"""docs/stress.md must cover every contract key, rule, transform, harness kind and finding kind the code accepts."""
import re
from pathlib import Path

from consilience.stress import contract as C

ROOT = Path(__file__).resolve().parent.parent
DOC = (ROOT / "docs" / "stress.md").read_text(encoding="utf-8")


def _in_doc(word):
    return f"`{word}`" in DOC or re.search(rf"\b{re.escape(word)}\b", DOC) is not None


def test_rules_transforms_kinds_types_documented():
    missing = [w for w in (*C.RULES, *C.TRANSFORMS, *C.HARNESS_KINDS, *C.FIELD_TYPES, *C.ROLES, *C.RECORD_KINDS,
                           *C.TOP) if not _in_doc(w)]
    assert not missing, missing


def test_finding_kinds_documented():
    src = (ROOT / "src" / "consilience" / "stress" / "checks.py").read_text(encoding="utf-8")
    kinds = set(re.findall(r'Finding\(\s*(?:where|"[A-Z0-9-]+"|"harness"),\s*"([a-z_]+)"', src))
    kinds |= set(re.findall(r'"kind":\s*"([a-z_]+)"', src))
    assert kinds, "no finding kinds found"
    missing = [k for k in sorted(kinds) if not _in_doc(k)]
    assert not missing, missing
