"""Canonical JSON and SHA-256, used for every receipt and rule-file hash."""

from __future__ import annotations

import hashlib
import json


def canonical_json(obj) -> str:
    """Deterministic JSON: sorted keys, no spaces, UTF-8, NaN and infinity refused."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def sha256_json(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
