import json
import os
import subprocess
import urllib.request
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORDS = sorted((ROOT / "pilot" / "records").glob("*.json"))
LEDGER_RAW = "https://raw.githubusercontent.com/Anuja-Khatri/consilience-ledger"


@lru_cache(maxsize=None)
def ledger_file(commit: str, path: str) -> str | None:
    """A file of the public consilience-ledger at a pinned commit.

    Read from a local clone if CONSILIENCE_LEDGER_DIR points at one, otherwise from
    raw.githubusercontent.com. Returns None if neither is reachable.
    """
    local = os.environ.get("CONSILIENCE_LEDGER_DIR")
    if local:
        try:
            return subprocess.run(["git", "-C", local, "show", f"{commit}:{path}"],
                                  check=True, capture_output=True, text=True).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    if os.environ.get("CONSILIENCE_OFFLINE"):
        return None
    try:
        with urllib.request.urlopen(f"{LEDGER_RAW}/{commit}/{path}", timeout=60) as r:
            return r.read().decode("utf-8")
    except OSError:
        return None


@pytest.fixture
def ledger():
    def get(commit, path):
        text = ledger_file(commit, path)
        if text is None:
            pytest.skip("public ledger not reachable (set CONSILIENCE_LEDGER_DIR or go online)")
        return text
    return get


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))
