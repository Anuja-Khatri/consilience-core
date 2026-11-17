"""Re-run a result from its receipt and confirm the hash.

A receipt (``consilience compare ... --receipt FILE`` or ``consilience check ...
--receipt FILE``) holds the inputs (for ``check``: the data file's path and SHA-256),
the options, the full rule file it used, the consilience version and the result, plus
``sha256`` over all of that. ``verify``:

1. recomputes the receipt's own hash (has the file been edited?);
2. for ``check``: finds the data file and confirms its SHA-256 (has the data changed?);
3. confirms the embedded rule file still hashes to the recorded rule hash;
4. re-runs the comparison or check with this installed consilience and confirms that a
   fresh receipt, stamped with the recorded version, has the same hash. The re-run uses
   the rules of the version that wrote the receipt: a 0.1.0 receipt is re-run by the
   0.1.0 rules (see ``consilience.units.rules_of``), so a later change of rule never
   makes an old receipt fail.

It also accepts a nanopublication record envelope (``schema: consilience-record/v0``),
for which it checks the record against its content hash (see ``consilience.receipts``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from . import __version__
from .compare import PINT_VERSION, RECEIPT_SCHEMA, InputError, compare, read_json
from .hashing import sha256_bytes, sha256_json
from .rules import RuleFileError, rules_from_dict
from .units import rules_of


@dataclass
class VerifyResult:
    ok: bool
    command: str
    recorded_sha256: Optional[str]
    recomputed_sha256: Optional[str]
    steps: list = field(default_factory=list)   # (step, ok, detail)
    note: str = ""

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 1


def _restamp(fresh: dict, recorded: dict) -> str:
    """Hash of a fresh receipt stamped with the recorded versions, so that the hash
    compares inputs, rules and result only."""
    r = {k: v for k, v in fresh.items() if k != "sha256"}
    for key in ("consilience_version", "pint_version"):
        if key in recorded:
            r[key] = recorded[key]
    return sha256_json(r)


def _resolve(stored: str, override, receipt_path: Optional[Path]) -> Path:
    if override is not None:
        p = Path(override)
        if not p.is_file():
            raise InputError(f"data file not found: {override}")
        return p
    cands = [Path(stored)]
    if receipt_path is not None and not Path(stored).is_absolute():
        cands.append(receipt_path.parent / stored)
    for c in cands:
        if c.is_file():
            return c
    raise InputError(f"the data file named in the receipt ({stored}) was not found; pass "
                     "its location with --data")


def verify(receipt: Union[str, Path, dict], *, data=None) -> VerifyResult:
    """Re-run the result recorded in ``receipt`` (a path or a dict) and confirm its hash.

    ``data`` overrides where to find the data file of a ``check`` receipt. Raises
    ``InputError`` if the receipt or its inputs cannot be used.
    """
    rpath = None
    if isinstance(receipt, (str, Path)):
        rpath = Path(receipt)
        rec = read_json(rpath)
    else:
        rec = receipt
    if not isinstance(rec, dict):
        raise InputError("a receipt must be a JSON object")

    from .receipts import SCHEMA as ENVELOPE_SCHEMA
    if rec.get("schema") == ENVELOPE_SCHEMA:
        return _verify_envelope(rpath, rec)

    if rec.get("receipt") != RECEIPT_SCHEMA:
        raise InputError(f"not a consilience receipt (expected \"receipt\": "
                         f"\"{RECEIPT_SCHEMA}\")")
    command = rec.get("command")
    if command not in ("compare", "check"):
        raise InputError(f"unknown receipt command {command!r}")
    recorded = rec.get("sha256")
    version = rec.get("consilience_version")
    steps = []

    body = {k: v for k, v in rec.items() if k != "sha256"}
    try:
        integrity = sha256_json(body)
    except ValueError as exc:
        raise InputError(f"the receipt cannot be hashed: {exc}") from None
    steps.append(("receipt hash", integrity == recorded,
                  "matches its contents" if integrity == recorded else
                  f"recorded {recorded}, contents hash to {integrity}: the receipt was edited"))

    with rules_of(version):
        return _rerun(rec, rpath, data, command, recorded, version, integrity, steps)


def _rerun(rec, rpath, data, command, recorded, version, integrity, steps) -> VerifyResult:
    """Steps 2-4, run under the rules of the version that wrote the receipt."""
    key = "pack" if command == "compare" else "rules"
    ruleset = None
    if rec.get(key) is not None:
        try:
            ruleset = rules_from_dict(rec[key]["content"], origin=f"receipt {key}")
            rok = ruleset.sha256 == rec[key].get("sha256")
            steps.append(("rule hash", rok, f"{ruleset.name} ({ruleset.version}) "
                          + ("matches" if rok else f"hashes to {ruleset.sha256}, recorded "
                             f"{rec[key].get('sha256')}")))
        except (RuleFileError, KeyError, TypeError) as exc:
            steps.append(("rule hash", False, f"embedded rules unusable: {exc}"))
            ruleset = None
    elif command == "check":
        raise InputError("a check receipt must contain its rules")

    fresh = None
    if command == "compare":
        try:
            inp, opt = rec["inputs"], rec["options"]
            if rec.get("pack") is not None and ruleset is None:
                raise InputError("the embedded pack is unusable")
            prec = rec["result"].get("precision") or {}
            written = {k: prec[k].get("written") for k in ("a", "b")
                       if isinstance(prec.get(k), dict)}
            fresh = compare(inp["a"], inp["b"], pack=ruleset, abs_tol=opt.get("abs_tol"),
                            rel_tol=opt.get("rel_tol"), floor=opt.get("floor"),
                            precision=opt.get("precision", "exact"),
                            _written=written).receipt
        except (KeyError, TypeError) as exc:
            raise InputError(f"the receipt is missing a field: {exc}") from None
    else:
        from .check import check
        stored = rec["inputs"]["data"]
        p = _resolve(stored["path"], data, rpath)
        got = sha256_bytes(p.read_bytes())
        dok = got == stored["sha256"]
        steps.append(("data hash", dok, f"{p} " + ("matches" if dok else
                                                    f"hashes to {got}, recorded "
                                                    f"{stored['sha256']}: the data changed")))
        if dok and ruleset is not None:
            fresh = check(p, ruleset).receipt
            fresh["inputs"]["data"]["path"] = stored["path"]   # where it was, as recorded

    recomputed = None
    if fresh is not None:
        recomputed = _restamp(fresh, rec)
        # the fresh receipt must match both the recorded hash and the receipt as written
        same = recomputed == recorded == integrity
        steps.append(("re-run", same, "same result" if same else
                      "the re-run gives a different result from the receipt"))
    else:
        steps.append(("re-run", False, "not re-run (see above)"))
    notes = []
    if version != __version__:
        notes.append(f"receipt made with consilience {version}; re-run with {__version__}")
    if rec.get("pint_version") != PINT_VERSION:
        notes.append(f"receipt made with pint {rec.get('pint_version')}; re-run with "
                     f"{PINT_VERSION} (a different pint can change the last digits of a "
                     "converted number)")
    note = "; ".join(notes)
    return VerifyResult(ok=all(s[1] for s in steps), command=command,
                        recorded_sha256=recorded, recomputed_sha256=recomputed, steps=steps,
                        note=note)


def _verify_envelope(rpath, rec) -> VerifyResult:
    from .receipts import ReceiptError, load_envelope, verify as verify_envelope
    if rpath is None:
        raise InputError("pass a record envelope as a file path")
    try:
        env = load_envelope(rpath)
        h = verify_envelope(env)
        return VerifyResult(ok=True, command="record-envelope", recorded_sha256=h,
                            recomputed_sha256=h,
                            steps=[("content hash", True,
                                    f"{env.receipt['hash_method']}; receipt {env.receipt_url}")])
    except ReceiptError as exc:
        return VerifyResult(ok=False, command="record-envelope",
                            recorded_sha256=rec.get("receipt", {}).get("content_hash")
                            if isinstance(rec.get("receipt"), dict) else None,
                            recomputed_sha256=None, steps=[("content hash", False, str(exc))])


__all__ = ["VerifyResult", "verify"]
