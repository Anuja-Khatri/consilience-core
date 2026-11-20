"""Compare a whole table of measurements: which records may be pooled, and do they agree.

``compare-table`` groups the records of a table by a key (for bioactivity: molecule and
target), and inside each group:

1. **Record status.** Each record is ``excluded(<rule>: <reason>)`` if one of the pack's
   record rules fails (or its key is not stated); ``unparseable(<what>: <why>)`` if its
   value, unit, uncertainty or a condition cannot be read; ``bound`` if its value is a
   one-sided bound (">10 uM"); otherwise ``usable``.
2. **Condition classes.** The records that are not excluded or unparseable are split by
   their condition values (the pack's conditions, after aliases, case rules and unit
   conversion; "not stated" kept as its own value). Records in different classes may not
   be pooled. With ``assume``, the two classes an assumption joins become one.
3. **Pairs.** Every pair inside a class is compared numerically, with exactly the rules
   of ``compare`` (tolerance, floor, stated precision, bounds); a class with a condition
   that is not stated gives ``not_stated`` pairs. Every pair across classes gets the
   refusal ``compare`` would give (``not_comparable(<condition>)`` or ``not_stated``).
4. **Class consensus**: ``single``, ``bounds_only``, ``disagree`` (any pair disagrees),
   ``within_floor`` (any pair only within the floor) or ``agree``. Pairs that are
   ``undecidable_bounds`` do not change it.
5. **Pooled value** (``single``/``agree``/``within_floor`` classes with a usable record):
   the median of the usable values (on the log scale in log mode: 10^median(log10 v)), in
   the first usable record's unit, assumption factors applied.
6. **pool_valid** is true when the record is ``usable``, its class has every condition
   stated, and the class consensus is ``single``, ``agree`` or ``within_floor``. It means
   the record may be pooled with the others **of its condition class**, never across
   classes. ``pool_reason`` names why when it is false.

Every cell is read as text (CSV, and strings in JSON), so the written digits that stated
precision depends on are kept. Numbers from Parquet or a DataFrame have no written form
and are exact. Empty or NaN cells are "not stated". A pack field whose column is absent
from the whole table is not checked; the summary and the receipt say so.

Exit codes: 64 unusable input; 3 a record could not be read; 1 a class disagrees inside;
0 otherwise. Records refused across classes or excluded by a rule are the expected
product of the check and do not set the exit code; they are counted in the summary.
"""

from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from . import __version__
from .compare import (PINT_VERSION, RANK, InputError, WrittenFloat, _absent, _bounded,
                      _check_conditions, _close, _defect, _label, _leaf, _log_options,
                      _options, _option_in, _raw, _read_uncertainty, _read_value,
                      _resolve_options, _side_precision, _written_text, read_json)
from .hashing import sha256_bytes, sha256_json
from .maps import ColumnMap, apply_map, load_map
from .rules import RuleSet, load_rules
from .units import (UREG, UnitError, convert, convert_difference, is_offset_unit,
                    parse_number, unit_text)

TABLE_RECEIPT_SCHEMA = "consilience-table-receipt/v1"
CONSENSUS_POOLABLE = ("single", "agree", "within_floor")
OUTPUT_FILES = ("records.csv", "classes.csv", "pairs.csv", "summary.json")


# ----------------------------------------------------------------------- reading
def _cell(v):
    """A table cell as the engine reads it: text stays text, JSON numbers keep their
    written digits, floats without a written form stay exact, NaN and blanks are None."""
    if v is None:
        return None
    if isinstance(v, float) and not isinstance(v, WrittenFloat) and math.isnan(v):
        return None
    if isinstance(v, str) and not v.strip():
        return None
    if isinstance(v, str) and v.strip().casefold() == "nan":
        return None
    return v


def _plain(v):
    """A value for writing into an output CSV or a receipt."""
    if isinstance(v, WrittenFloat):
        return v.text
    return v


def _read_csv(path: Path) -> tuple[list, list]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise InputError(f"{path}: not UTF-8 text") from None
    reader = csv.reader(io.StringIO(text, newline=""))
    rows = list(reader)
    if not rows:
        raise InputError(f"{path}: empty table")
    header = rows[0]
    if len(set(header)) != len(header):
        raise InputError(f"{path}: repeated column names in the header")
    out = []
    for i, r in enumerate(rows[1:], start=2):
        if not r or all(not c.strip() for c in r):
            continue
        if len(r) != len(header):
            raise InputError(f"{path}, line {i}: {len(r)} cells for {len(header)} columns")
        out.append(dict(zip(header, r)))
    return header, out


def _records_from_json(data, cmap: Optional[ColumnMap], origin: str) -> list:
    if isinstance(data, dict):
        key = cmap.content.get("records") if cmap is not None else None
        if key and key in data:
            data = data[key]
        elif "records" in data:
            data = data["records"]
        else:
            raise InputError(f"{origin}: a JSON table must be a list of records"
                             + (f" or have them under {key!r}" if key else ""))
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise InputError(f"{origin}: a JSON table must be a list of objects")
    return data


def read_table(table, cmap: Optional[ColumnMap] = None) -> tuple[list, dict]:
    """(rows, description) for a path (CSV, JSON, Parquet), a DataFrame or a list of
    dicts. The description goes into the receipt."""
    if isinstance(table, (str, Path)):
        p = Path(table)
        if not p.is_file():
            raise InputError(f"table not found: {table}")
        suffix = p.suffix.lower()
        desc = {"path": str(table), "sha256": sha256_bytes(p.read_bytes())}
        if suffix in (".csv", ".tsv", ".txt"):
            _, rows = _read_csv(p)
            desc["format"] = "csv"
        elif suffix == ".json":
            rows = _records_from_json(read_json(p), cmap, str(table))
            desc["format"] = "json"
        elif suffix == ".jsonl":
            rows = []
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
                if line.strip():
                    try:
                        rows.append(json.loads(line, parse_float=WrittenFloat))
                    except json.JSONDecodeError as exc:
                        raise InputError(f"{table}, line {i}: not valid JSON: {exc}") from None
            desc["format"] = "jsonl"
        elif suffix == ".parquet":
            try:
                import pyarrow.parquet as pq
            except ImportError:
                raise InputError("reading Parquet needs pyarrow (pip install pyarrow)") from None
            rows = pq.read_table(p).to_pylist()
            desc["format"] = "parquet"
        else:
            raise InputError(f"{table}: give a .csv, .json, .jsonl or .parquet file")
        return rows, desc
    if hasattr(table, "to_dict") and hasattr(table, "columns"):
        rows = [{str(k): _py(v) for k, v in r.items()} for r in table.to_dict(orient="records")]
        return rows, {"kind": "dataframe", "sha256": sha256_json(_canonical_rows(rows))}
    if isinstance(table, list) and all(isinstance(r, dict) for r in table):
        rows = [{str(k): _py(v) for k, v in r.items()} for r in table]
        return rows, {"kind": "records", "sha256": sha256_json(_canonical_rows(rows))}
    raise InputError("the table must be a file path, a pandas DataFrame or a list of dicts")


def _py(v):
    """numpy and pandas scalars as plain Python values; pandas' NA as None."""
    if type(v).__name__ in ("NAType", "NaTType"):
        return None
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        try:
            return v.item()
        except (ValueError, TypeError):
            return v
    return v


def _canonical_json_rows(rows) -> list:
    """Rows for input.json: plain JSON values (floats stay floats: exact on re-reading)."""
    def c(v):
        v = _cell(v)
        if isinstance(v, WrittenFloat):
            return v.text
        return v if isinstance(v, (str, int, float, bool)) or v is None else str(v)
    return [{str(k): c(v) for k, v in r.items()} for r in rows]


def _canonical_rows(rows) -> list:
    def c(v):
        v = _cell(v)
        if isinstance(v, float):
            return repr(v)
        if isinstance(v, (int, bool, str)) or v is None:
            return v
        return str(v)
    return [{str(k): c(v) for k, v in r.items()} for r in rows]


# ----------------------------------------------------------------------- records
@dataclass
class _Rec:
    row: int                 # 1-based position in the input
    rid: Any                 # the map's id column, if any
    key: tuple
    fields: dict             # the record under the engine's names
    status: str = "usable"
    reason: str = ""
    measurement: dict = field(default_factory=dict)
    q: Any = None            # pint quantity (own unit)
    unit_text: Optional[str] = None
    op: Optional[str] = None
    unc_own: float = 0.0
    written: Optional[str] = None
    assumption: str = ""
    factor: float = 1.0
    ckey: tuple = ()
    cls: str = ""
    # filled per class
    val: float = 0.0
    unc: float = 0.0
    implied: float = 0.0


def _relation_value(fields: dict, has_relation: bool):
    """The value as the comparison core reads it: "<op> number" for a bound."""
    v = _cell(fields.get("value"))
    if v is None:
        return None
    rel = _cell(fields.get("relation")) if has_relation else None
    rel = "=" if rel is None else " ".join(str(rel).split())
    text = v.text if isinstance(v, WrittenFloat) else v
    if rel == "=":
        return text if isinstance(text, (str, int, float)) else str(text)
    return f"{rel} {text}"


def _record_rule(rule: dict, fields: dict) -> Optional[str]:
    """None if the record passes; else the reason."""
    v = _cell(fields.get(rule["field"]))
    kind = rule["kind"]
    if kind == "empty":
        return None if v is None else f"{rule['field']} is {_plain(v)!s}"
    if kind == "present":
        return None if v is not None else "not stated"
    if kind == "in":
        if v is None:
            return None if rule.get("allow_empty") else "not stated"
        s = " ".join(str(_plain(v)).split())
        return None if s in rule["values"] else f"{rule['field']} is {s}"
    if kind == "at_least":
        if v is None:
            return "not stated"
        try:
            x = parse_number(_plain(v) if not isinstance(v, (int, float)) else v)
        except UnitError:
            return f"{rule['field']} is not a number: {_plain(v)!s}"
        return None if x >= rule["threshold"] else f"{rule['field']} is {_plain(v)!s}"
    raise AssertionError(kind)


# ------------------------------------------------------------- condition classes
def _canon(rule: dict, v):
    """The class-key part of one condition value under one pack rule. Mirrors
    ``compare``'s pack rules exactly: two records get the same canonical value if and
    only if ``compare`` finds no defect on this condition."""
    if rule.get("absent_on_both") == "equal" and _absent(v):
        return ("absent",)
    if v is None:
        return ("unstated",)
    leaf = _leaf(v)                        # may raise UnitError: record unparseable
    if leaf[0] == "unstated":
        return ("unstated",)
    pred = rule["predicate"]
    if pred == "equal":
        if leaf[0] == "text":
            s = leaf[1].casefold() if rule.get("ignore_case") else leaf[1]
            return ("text", rule.get("aliases", {}).get(s, s))
        if leaf[0] in ("number", "bool"):
            return (leaf[0], leaf[1])
        return ("different_kinds", _raw(v))   # never equal: compare refuses it
    if pred == "quantity_equal":
        words = set(rule.get("words", []))
        if leaf[0] == "text" and leaf[1] in words:
            return ("word", leaf[1])
        if leaf[0] != "quantity":
            raise UnitError("missing_unit" if leaf[0] == "number" else "not_a_quantity", v,
                            "expected a quantity with a unit")
        q = leaf[1]
        dims = str(q.dimensionality)
        mag = float(q.to_base_units().magnitude)   # an absolute value (degC -> kelvin)
        rest = tuple((k, _canon({"predicate": "equal"}, leaf[2].get(k)))
                     for k in rule.get("also_equal", []))
        return ("quantity", dims, float(f"{mag:.10g}"), rest)
    # record
    if not isinstance(v, dict):
        raise UnitError("expected_record", v, "expected an object with parts "
                        + ", ".join(rule["parts"]))
    return ("record",) + tuple((p, _canon(dict(pr, id=rule.get("id")), v.get(p)))
                               for p, pr in rule["parts"].items())


def _stated(c) -> bool:
    if not isinstance(c, tuple):
        return True
    if c and c[0] == "unstated":
        return False
    return all(_stated(x) for x in c if isinstance(x, tuple))


def _display(c):
    """Human-readable form of a canonical condition value, for classes.csv."""
    if c[0] == "absent":
        return ""
    if c[0] == "unstated":
        return "not stated"
    if c[0] in ("text", "word"):
        return c[1]
    if c[0] in ("number", "bool"):
        v = c[1]
        return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)
    if c[0] == "quantity":
        return f"{c[2]:g} ({c[1]})"
    if c[0] == "record":
        return {p: _display(x) for p, x in c[1:]}
    return str(c[1])


# ------------------------------------------------------------------- the result
@dataclass
class TableResult:
    summary: dict
    records: list
    classes: list
    pairs: list
    receipt: dict = field(repr=False)
    text: str = ""
    files: dict = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        return self.summary["exit_code"]


# ------------------------------------------------------------------------- main
def compare_table(table, *, key=None, pack: Union[str, Path, RuleSet, None] = None,
                  map: Union[str, Path, dict, ColumnMap, None] = None,  # noqa: A002
                  out: Union[str, Path, None] = None, abs_tol=None, rel_tol=None,
                  floor=None, log_tol=None, log_floor=None, assume=(),
                  precision: str = "stated") -> TableResult:
    """Compare every record of ``table`` with the others in its group.

    ``table``: a CSV, JSON, JSONL or Parquet path, a pandas DataFrame, or a list of dicts.
    ``key``: the column names that define a group (default: the map's ``key``).
    ``pack``: a bundled pack name or a path (conditions, record rules, assumptions,
    defaults). ``map``: a bundled column map (``chembl``, ``iupac_pka``), a path or None.
    ``out``: a directory for records.csv, classes.csv, pairs.csv, summary.json and
    receipt.json. Tolerances as for ``compare``; with none given, the pack's defaults.
    ``assume``: assumption ids from the pack to switch on. Raises ``InputError`` for
    unusable input.
    """
    if precision not in ("stated", "exact"):
        raise InputError(f"precision must be 'stated' or 'exact', not {precision!r}")
    cmap = load_map(map)
    ps = load_rules(pack) if pack is not None else None
    if ps is not None and ps.kind != "compare-pack":
        raise InputError(f"{ps.origin} is a {ps.kind} file, not a compare pack")
    if isinstance(key, str):
        key = [k.strip() for k in key.split(",") if k.strip()]
    if not key:
        key = list(cmap.content.get("key", [])) if cmap is not None else []
    if not key:
        raise InputError("give --key: the column(s) that identify the same quantity "
                         "(for example molecule and target)")
    assume = list(assume or [])
    pack_assumptions = {a["id"]: a for a in (ps.content.get("assumptions", []) if ps else [])}
    for a in assume:
        if a not in pack_assumptions:
            raise InputError(f"--assume {a!r}: the pack has no such assumption "
                             f"(it has: {sorted(pack_assumptions) or 'none'})")
    if ps is not None:
        for r in ps.rules:
            if r["predicate"] == "quantity_equal" and str(r.get("tolerance", 0)) not in (
                    "0", "0.0") and r.get("tolerance") not in (0, 0.0):
                raise InputError(f"pack rule {r['id']} has a tolerance; compare-table needs "
                                 "exact-match conditions so that classes are well defined")

    a_tol, r_tol, fl, l_tol, l_floor, from_pack = _resolve_options(
        ps, abs_tol, rel_tol, floor, log_tol, log_floor)
    given, opts = _options(a_tol, r_tol, fl)
    logopts = _log_options(l_tol, l_floor)
    log_mode = bool(logopts)

    rows, input_desc = read_table(table, cmap)
    if not rows:
        raise InputError("the table has no records")

    # ---- records under the engine's names, and which columns exist at all
    recs: list[_Rec] = []
    present_any: set = set()
    mapped = []
    for i, row in enumerate(rows, start=1):
        rec, present = apply_map(row, cmap)
        rec = {k: _cell(v) for k, v in rec.items()}   # empty, blank and NaN: not stated
        mapped.append(rec)
        present_any |= present
    if "value" not in present_any:
        raise InputError("no value column: name it 'value' or give a --map that says "
                         "which column holds the value")
    missing_key = [k for k in key if k not in present_any]
    if missing_key:
        raise InputError(f"key column(s) not in the table: {missing_key}")
    has_relation = "relation" in present_any
    has_unit = "unit" in present_any
    rules_all = ps.rules if ps is not None else []
    applied = [r for r in rules_all if r["field"] in present_any]
    not_applied = [r["id"] for r in rules_all if r["field"] not in present_any]
    rrules = ps.content.get("record_rules", []) if ps is not None else []
    rr_applied = [r for r in rrules if r["field"] in present_any]
    rr_not_applied = [r["id"] for r in rrules if r["field"] not in present_any]
    applied_pack = None
    if ps is not None:
        content = dict(ps.content, conditions=applied)
        applied_pack = RuleSet(kind=ps.kind, name=ps.name, version=ps.version,
                               content=content, sha256=ps.sha256, origin=ps.origin)

    for i, rec in enumerate(mapped, start=1):
        k = tuple(_plain(_cell(rec.get(c))) for c in key)
        r = _Rec(row=i, rid=_plain(_cell(rec.get("id"))), key=k, fields=rec)
        recs.append(r)
        if any(x is None for x in k):
            miss = [c for c, x in zip(key, k) if x is None]
            r.status, r.reason = "excluded", f"key: {', '.join(miss)} not stated"
            continue
        for rule in rr_applied:
            why = _record_rule(rule, rec)
            if why is not None:
                r.status, r.reason = "excluded", f"{rule['id']}: {why}"
                break
        if r.status == "excluded":
            continue
        # the measurement, read exactly as compare reads it
        value = _relation_value(rec, has_relation)
        unit = _cell(rec.get("unit")) if has_unit else None
        unc = _cell(rec.get("uncertainty"))
        m = {"value": value}
        if unit is not None:
            m["unit"] = _plain(unit) if not isinstance(unit, str) else unit
        if unc is not None:
            m["uncertainty"] = _plain(unc) if isinstance(unc, WrittenFloat) else unc
        defects: list = []
        got = _read_value(m, "record", defects)
        if got is not None:
            r.q, r.unit_text, r.op = got
            u = _read_uncertainty(m, "record", r.q, defects)
            r.unc_own = u or 0.0
            if r.op is not None and m.get("uncertainty") is not None:
                defects.append(_defect("unparseable", "record.uncertainty",
                                       "uncertainty_on_bound",
                                       "a bound has no uncertainty"))
            if log_mode and not float(r.q.magnitude) > 0:
                defects.append(_defect("unparseable", "record.value", "not_positive",
                                       "a log-scale comparison needs a value above zero"))
        if defects:
            d = sorted(defects, key=lambda x: RANK[x["verdict"]])[0]
            tgt = d["target"].replace("record.", "")
            r.status = "unparseable" if d["verdict"] == "unparseable" else "excluded"
            r.reason = (f"{tgt}: {d['reason']}" if d["verdict"] == "unparseable" else
                        f"{tgt}: not stated")
            continue
        if precision == "exact":
            r.written = None
        elif isinstance(value, str):
            r.written = _written_text(value, None)
        elif isinstance(value, int) and not isinstance(value, bool):
            r.written = str(value)
        else:
            r.written = None   # a number with no written form (Parquet, DataFrame): exact
        r.measurement = m
        # assumption: rewrite the condition and remember the factor
        conds = {rr["field"]: rec.get(rr["field"]) for rr in applied}
        for aid in assume:
            a = pack_assumptions[aid]
            v = conds.get(a["condition"])
            if isinstance(v, str) and " ".join(v.split()) == a["from"]:
                conds[a["condition"]] = a["to"]
                r.assumption, r.factor = aid, float(a["factor"])
        r.measurement["conditions"] = conds
        try:
            parts = tuple((rr["field"], _canon(rr, conds.get(rr["field"])))
                          for rr in applied)
        except UnitError as exc:
            r.status, r.reason = "unparseable", f"conditions: {exc.reason}"
            continue
        dims = str((1.0 * r.q.units).to_base_units().dimensionality)
        r.ckey = (("unit_dimension", dims),) + parts
        r.status = "bound" if r.op is not None else "usable"

    # ---- groups, classes, pairs
    groups: dict = {}
    for r in recs:
        if r.status in ("usable", "bound"):
            groups.setdefault(r.key, []).append(r)
    order = []
    seen = set()
    for r in recs:
        if r.status in ("usable", "bound") and r.key not in seen:
            seen.add(r.key)
            order.append(r.key)

    classes_out, pairs_out = [], []
    cls_info: dict = {}
    cross_cache: dict = {}
    for gk in order:
        members = groups[gk]
        cls_of: dict = {}
        for r in members:
            if r.ckey not in cls_of:
                cls_of[r.ckey] = f"C{len(cls_of) + 1}"
            r.cls = cls_of[r.ckey]
        by_cls: dict = {}
        for r in members:
            by_cls.setdefault(r.cls, []).append(r)
        # per class: a common unit and every member's value in it
        for cid, ms in by_cls.items():
            first = next((m for m in ms if m.op is None), ms[0])
            cunit = first.q.units
            if opts["rel_tol"] > 0 and is_offset_unit(cunit):
                raise InputError(f"--rel-tol cannot be used with {first.unit_text}: its zero "
                                 "is arbitrary; use --abs-tol")
            for m in ms:
                m.val = convert(m.q, cunit) * m.factor
                m.unc = (convert_difference(m.unc_own, m.q.units, cunit) * m.factor
                         if m.unc_own else 0.0)
                if precision == "stated":
                    p = _side_precision(m.measurement, m.written)
                    h = p["implied"]
                    if log_mode:
                        own = float(m.q.magnitude)
                        m.implied = math.log10(1.0 + h / own) if h else 0.0
                    else:
                        m.implied = (convert_difference(h, m.q.units, cunit) * m.factor
                                     if h else 0.0)
            abs_t = 0.0 if log_mode else _option_in(opts["abs_tol"], cunit, "abs_tol")
            floor_t = 0.0 if log_mode else _option_in(opts["floor"], cunit, "floor")
            cls_info[(gk, cid)] = {"unit": cunit, "unit_text": first.unit_text,
                                   "abs_t": abs_t, "floor_t": floor_t,
                                   "counts": {"agree": 0, "within_floor": 0, "disagree": 0,
                                              "undecidable_bounds": 0, "not_stated": 0}}
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                if a.cls == b.cls:
                    info = cls_info[(gk, a.cls)]
                    if not _stated(a.ckey):
                        defs, _ = _check_conditions(a.measurement["conditions"],
                                                    b.measurement["conditions"], applied_pack)
                        defs.sort(key=lambda d: RANK[d["verdict"]])
                        verdict, label = defs[0]["verdict"], _label(defs[0])
                        reasons = [_label(d) for d in defs]
                        diff = None
                    else:
                        verdict, diff = _numeric(a, b, info, opts, logopts, log_mode)
                        label, reasons = verdict, []
                    info["counts"][verdict] = info["counts"].get(verdict, 0) + 1
                else:
                    ck = (a.ckey, b.ckey)
                    if ck not in cross_cache:
                        defs = []
                        if a.ckey[0] != b.ckey[0]:
                            defs.append(_defect("not_comparable", "unit",
                                                "different_dimensions",
                                                f"{a.unit_text} vs {b.unit_text}"))
                        cd, _ = _check_conditions(a.measurement["conditions"],
                                                  b.measurement["conditions"], applied_pack)
                        defs.extend(cd)
                        if not defs:   # cannot happen: different classes always differ
                            defs.append(_defect("not_comparable", "class", "differs"))
                        defs.sort(key=lambda d: RANK[d["verdict"]])
                        cross_cache[ck] = (defs[0]["verdict"], _label(defs[0]),
                                           [_label(d) for d in defs])
                    verdict, label, reasons = cross_cache[ck]
                    diff = None
                pairs_out.append({"key": gk, "a": a.row, "b": b.row, "a_id": a.rid,
                                  "b_id": b.rid, "verdict": verdict, "label": label,
                                  "reasons": reasons, "difference": diff,
                                  "a_class": a.cls, "b_class": b.cls,
                                  "assumption": ";".join(sorted({x for x in (a.assumption,
                                                                           b.assumption)
                                                                if x}))})
        # consensus, pooled value, bounds check
        for cid, ms in by_cls.items():
            info = cls_info[(gk, cid)]
            c = info["counts"]
            usable = [m for m in ms if m.op is None]
            stated = _stated(ms[0].ckey)
            if len(ms) == 1:
                consensus = "single"
            elif not stated:
                consensus = "not_stated"     # its pairs are not_stated: nothing compared
            elif not usable:
                consensus = "bounds_only"
            elif c["disagree"]:
                consensus = "disagree"
            elif c["within_floor"]:
                consensus = "within_floor"
            else:
                consensus = "agree"
            pooled, preason, bcons = None, "", ""
            if not stated:
                preason = "a condition is not stated"
            elif consensus in CONSENSUS_POOLABLE and usable:
                pooled = _median([m.val for m in usable], log_mode)
                bounds = [m for m in ms if m.op is not None]
                if bounds:
                    ok = True
                    for bm in bounds:
                        v_, _ = _bound_vs_value(bm, pooled, info, opts, logopts, log_mode)
                        ok = ok and v_ != "disagree"
                    bcons = "true" if ok else "false"
            elif consensus == "bounds_only":
                preason = "only bounds: no value to pool"
            elif consensus == "disagree":
                preason = "the class disagrees inside"
            ex = ms[0]
            cond_disp = {f: _display(cv) for f, cv in ex.ckey[1:]}
            methods = sorted({str(_plain(_cell(m.fields.get("method"))))
                              for m in ms if _cell(m.fields.get("method")) is not None})
            info.update(consensus=consensus, stated=stated)
            classes_out.append({
                "key": gk, "class": cid, "conditions": cond_disp,
                "unit_dimension": ex.ckey[0][1],
                "n_records": len(ms), "n_usable": len(usable),
                "n_bounds": len(ms) - len(usable),
                "pairs": dict(c), "consensus": consensus, "class_stated": stated,
                "pooled_value": pooled, "pooled_unit": info["unit_text"] if pooled is not None
                else None, "pooled_scale": ("log10 median" if log_mode else "median")
                if pooled is not None else None,
                "pooled_reason": preason, "bounds_consistent": bcons,
                "assumption": ";".join(sorted({m.assumption for m in ms if m.assumption})),
                "methods": methods})

    # ---- record-level outputs
    records_out = []
    for r in recs:
        consensus = stated = None
        if r.status in ("usable", "bound"):
            info = cls_info[(r.key, r.cls)]
            consensus, stated = info["consensus"], info["stated"]
        if r.status == "excluded":
            pv, pr = False, f"excluded({r.reason.split(':')[0]})"
        elif r.status == "unparseable":
            pv, pr = False, f"unparseable({r.reason})"
        elif r.status == "bound":
            pv, pr = False, "bound"
        elif not stated:
            nf = [f for f, cv in r.ckey[1:] if not _stated(cv)]
            pv, pr = False, f"condition_not_stated({','.join(nf)})"
        elif consensus == "disagree":
            pv, pr = False, "class_disagrees"
        else:
            pv, pr = True, ""
        records_out.append({
            "row": r.row, "id": r.rid, "key": r.key,
            "value": _plain(_cell(r.fields.get("value"))),
            "relation": _plain(_cell(r.fields.get("relation"))) if has_relation else None,
            "unit": _plain(_cell(r.fields.get("unit"))) if has_unit else None,
            "record_status": r.status if r.status in ("usable", "bound") else
            f"{r.status}({r.reason})",
            "condition_class": r.cls, "class_consensus": consensus,
            "class_stated": stated, "pool_valid": pv, "pool_reason": pr,
            "assumption": r.assumption})

    # ---- summary
    n_groups = len(order)
    multi = sum(1 for gk in order if len({r.cls for r in groups[gk]}) > 1)
    status_counts: dict = {}
    excluded_by: dict = {}
    for r in recs:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
        if r.status == "excluded":
            rid = r.reason.split(":")[0]
            excluded_by[rid] = excluded_by.get(rid, 0) + 1
        if r.status == "unparseable":
            excluded_by["unparseable:" + r.reason] = excluded_by.get(
                "unparseable:" + r.reason, 0) + 1
    verdicts: dict = {}
    cross_by: dict = {}
    within = {"agree": 0, "within_floor": 0, "disagree": 0, "undecidable_bounds": 0,
              "not_stated": 0}
    for p in pairs_out:
        verdicts[p["verdict"]] = verdicts.get(p["verdict"], 0) + 1
        if p["a_class"] == p["b_class"]:
            within[p["verdict"]] = within.get(p["verdict"], 0) + 1
        else:
            cross_by[p["label"]] = cross_by.get(p["label"], 0) + 1
    consensus_counts: dict = {}
    for c in classes_out:
        consensus_counts[c["consensus"]] = consensus_counts.get(c["consensus"], 0) + 1
    exit_code = 3 if status_counts.get("unparseable") else (
        1 if within.get("disagree") else 0)
    summary = {
        "records": len(recs), "groups": n_groups,
        "groups_with_more_than_one_class": multi,
        "record_status": dict(sorted(status_counts.items())),
        "excluded_or_unparseable_by_reason": dict(sorted(excluded_by.items())),
        "classes": len(classes_out),
        "class_consensus": dict(sorted(consensus_counts.items())),
        "pairs": len(pairs_out),
        "pair_verdicts": dict(sorted(verdicts.items())),
        "pairs_within_classes": dict(sorted(within.items())),
        "pairs_across_classes_by_reason": dict(sorted(cross_by.items(),
                                                      key=lambda kv: (-kv[1], kv[0]))),
        "pool_valid_records": sum(1 for r in records_out if r["pool_valid"]),
        "not_checked_column_absent": {"conditions": not_applied, "record_rules": rr_not_applied},
        "key": key,
        "scale": "log10" if log_mode else "linear",
        "exit_code": exit_code,
    }
    text = _plain_text(summary, ps, cmap, logopts, given, assume)
    summary["text"] = text

    # ---- options as recorded
    rec_opts = dict(given)
    if log_mode:
        rec_opts["log_tol"], rec_opts["log_floor"] = l_tol, l_floor
    if from_pack:
        rec_opts["defaults_from_pack"] = True
    rec_opts["precision"] = precision
    rec_opts["key"] = key
    rec_opts["assume"] = assume

    files = {}
    texts = _render(records_out, classes_out, pairs_out, summary, key)
    if out is not None:
        od = Path(out)
        od.mkdir(parents=True, exist_ok=True)
        if "path" not in input_desc:
            # an in-memory table: save it, so the receipt can be re-run from a file
            data = (json.dumps(_canonical_json_rows(rows), ensure_ascii=False, indent=0)
                    + "\n").encode("utf-8")
            (od / "input.json").write_bytes(data)
            input_desc = {"path": "input.json", "format": "records-json",
                          "sha256": sha256_bytes(data), "from": input_desc["kind"]}
        for name in OUTPUT_FILES:
            (od / name).write_bytes(texts[name])
    files = {name: sha256_bytes(texts[name]) for name in OUTPUT_FILES}

    receipt = {
        "receipt": TABLE_RECEIPT_SCHEMA,
        "command": "compare-table",
        "consilience_version": __version__,
        "pint_version": PINT_VERSION,
        "input": input_desc,
        "map": (dict(cmap.describe(), content=cmap.content) if cmap is not None else None),
        "pack": (dict(ps.describe(), content=ps.content) if ps is not None else None),
        "options": rec_opts,
        "outputs": files,
        "summary": {k: v for k, v in summary.items() if k != "text"},
    }
    receipt["sha256"] = sha256_json(receipt)
    if out is not None:
        (Path(out) / "receipt.json").write_text(
            json.dumps(receipt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return TableResult(summary=summary, records=records_out, classes=classes_out,
                       pairs=pairs_out, receipt=receipt, text=text, files=files)


# ------------------------------------------------------------------ numeric core
def _median(vals: list, log_mode: bool) -> float:
    """The median; on the log scale the geometric median. An odd count returns the
    middle value itself (no rounding through logarithms)."""
    v = sorted(vals)
    n = len(v)
    if n % 2:
        return v[n // 2]
    lo, hi = v[n // 2 - 1], v[n // 2]
    return math.sqrt(lo * hi) if log_mode else (lo + hi) / 2
def _numeric(a: _Rec, b: _Rec, info: dict, opts: dict, logopts: dict, log_mode: bool):
    """Verdict and difference for two records of one class, by compare's rules (values
    already in the class unit; implied precision and uncertainties per record)."""
    implied = a.implied + b.implied
    if log_mode:
        la, lb = math.log10(a.val), math.log10(b.val)
        scale = max(abs(la), abs(lb), 1.0)
        tol = logopts.get("log_tol", 0.0)
        fl = max(logopts.get("log_floor", 0.0),
                 math.log10(1.0 + a.unc / a.val) if a.unc else 0.0,
                 math.log10(1.0 + b.unc / b.val) if b.unc else 0.0)
        x, y = la, lb
    else:
        x, y = a.val, b.val
        scale = max(abs(x), abs(y))
        tol = max(info["abs_t"], opts["rel_tol"] * scale)
        fl = max(info["floor_t"], a.unc, b.unc)
    if a.op is None and b.op is None:
        diff = abs(x - y)
        if _close(x, y, scale, tol + implied):
            return "agree", diff
        if fl > 0 and _close(x, y, scale, fl + implied):
            return "within_floor", diff
        return "disagree", diff
    return _bounded(x, a.op, y, b.op, scale, tol, fl, implied)


def _bound_vs_value(bm: _Rec, pooled: float, info, opts, logopts, log_mode):
    """Does the pooled value satisfy a bound of the class (within the floor)?"""
    probe = _Rec(row=0, rid=None, key=(), fields={})
    probe.val, probe.op, probe.unc, probe.implied = pooled, None, 0.0, 0.0
    return _numeric(bm, probe, info, opts, logopts, log_mode)


# --------------------------------------------------------------------- rendering
def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(v)


def _csv(header: list, rows: list) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow([_fmt(x) for x in r])
    return buf.getvalue().encode("utf-8")


def _render(records, classes, pairs, summary, key) -> dict:
    rec_h = ["row", "id"] + list(key) + ["value", "relation", "unit", "record_status",
                                         "condition_class", "class_consensus",
                                         "class_stated", "pool_valid", "pool_reason",
                                         "assumption"]
    rec_rows = [[r["row"], r["id"], *r["key"], r["value"], r["relation"], r["unit"],
                 r["record_status"], r["condition_class"], r["class_consensus"],
                 r["class_stated"], r["pool_valid"], r["pool_reason"], r["assumption"]]
                for r in records]
    cls_h = list(key) + ["class", "conditions", "unit_dimension", "n_records", "n_usable",
                         "n_bounds", "pairs_agree", "pairs_within_floor", "pairs_disagree",
                         "pairs_undecidable_bounds", "consensus", "class_stated",
                         "pooled_value", "pooled_unit", "pooled_scale", "pooled_reason",
                         "bounds_consistent", "assumption", "methods"]
    cls_rows = [[*c["key"], c["class"], c["conditions"], c["unit_dimension"], c["n_records"],
                 c["n_usable"], c["n_bounds"], c["pairs"]["agree"],
                 c["pairs"]["within_floor"], c["pairs"]["disagree"],
                 c["pairs"]["undecidable_bounds"], c["consensus"], c["class_stated"],
                 c["pooled_value"], c["pooled_unit"], c["pooled_scale"], c["pooled_reason"],
                 c["bounds_consistent"], c["assumption"], ";".join(c["methods"])]
                for c in classes]
    pair_h = list(key) + ["a_row", "b_row", "a_id", "b_id", "a_class", "b_class", "verdict",
                          "label", "reasons", "difference", "assumption"]
    pair_rows = [[*p["key"], p["a"], p["b"], p["a_id"], p["b_id"], p["a_class"],
                  p["b_class"], p["verdict"], p["label"], ";".join(p["reasons"]),
                  p["difference"], p["assumption"]] for p in pairs]
    return {"records.csv": _csv(rec_h, rec_rows), "classes.csv": _csv(cls_h, cls_rows),
            "pairs.csv": _csv(pair_h, pair_rows),
            "summary.json": (json.dumps(summary, indent=1, ensure_ascii=False,
                                        sort_keys=True) + "\n").encode("utf-8")}


def _plain_text(s: dict, ps, cmap, logopts, given, assume) -> str:
    rs = s["record_status"]
    lines = [f"Consilience pooling check"
             + (f" (pack {ps.version})" if ps is not None else " (no pack: conditions not "
                "checked)") + f": {s['records']} records, {s['groups']} groups "
             f"({' + '.join(s['key'])})."]
    ex = rs.get("excluded", 0)
    if ex:
        top = sorted(((k, v) for k, v in s["excluded_or_unparseable_by_reason"].items()
                      if not k.startswith("unparseable:")), key=lambda kv: -kv[1])[:4]
        lines.append(f"- {ex} records left out by a rule: "
                     + ", ".join(f"{k} {v}" for k, v in top) + ".")
    if rs.get("unparseable"):
        lines.append(f"- {rs['unparseable']} records could not be read (listed in "
                     "records.csv).")
    if rs.get("bound"):
        lines.append(f"- {rs['bound']} records are bounds (\">\", \"<\"): kept as bounds, "
                     "never averaged.")
    lines.append(f"- {s['groups_with_more_than_one_class']} groups contain records that "
                 "must not be pooled together (more than one condition class).")
    cross = list(s["pairs_across_classes_by_reason"].items())[:5]
    if cross:
        lines.append("  Pairs refused, by first reason: "
                     + ", ".join(f"{k} {v}" for k, v in cross) + ".")
    w = s["pairs_within_classes"]
    scale = (f"{logopts.get('log_tol', 0)} log units" if logopts else "the tolerance")
    flo = (f"{logopts.get('log_floor', 0)} log units" if logopts else "the floor")
    lines.append(f"- Pairs inside a class: {w.get('agree', 0)} agree within {scale}, "
                 f"{w.get('within_floor', 0)} only within {flo}, {w.get('disagree', 0)} "
                 f"disagree, {w.get('undecidable_bounds', 0)} are two bounds that can "
                 "both hold.")
    lines.append(f"- {s['pool_valid_records']} records are pool_valid (poolable with the "
                 "others of their condition class).")
    na = s["not_checked_column_absent"]
    if na["conditions"] or na["record_rules"]:
        lines.append("- Not checked (column absent from the table): "
                     + ", ".join(na["conditions"] + na["record_rules"]) + ".")
    if assume:
        lines.append(f"- Assumptions switched on: {', '.join(assume)}.")
    return "\n".join(lines)


# ------------------------------------------------------------------------ verify
def verify_table(receipt: dict, *, input_path=None, receipt_path: Optional[Path] = None):
    """Re-run a compare-table receipt from its input file. Returns (ok, steps, note)."""
    steps = []
    recorded = receipt.get("sha256")
    body = {k: v for k, v in receipt.items() if k != "sha256"}
    integrity = sha256_json(body)
    steps.append(("receipt hash", integrity == recorded,
                  "matches its contents" if integrity == recorded else
                  "the receipt was edited"))
    inp = receipt.get("input") or {}
    path = input_path
    if path is None and inp.get("path"):
        cands = [Path(inp["path"])]
        if receipt_path is not None and not Path(inp["path"]).is_absolute():
            cands.append(Path(receipt_path).parent / inp["path"])
            cands.append(Path(receipt_path).parent / Path(inp["path"]).name)
        path = next((c for c in cands if c.is_file()), None)
    if path is None:
        raise InputError("the table this receipt was made from was not found; pass it "
                         "with --input")
    p = Path(path)
    if not p.is_file():
        raise InputError(f"input not found: {path}")
    got = sha256_bytes(p.read_bytes())
    dok = got == inp.get("sha256")
    steps.append(("input hash", dok, f"{p} " + ("matches" if dok else
                                               "differs: the input changed")))
    if not dok:
        steps.append(("re-run", False, "not re-run (the input changed)"))
        return False, steps, ""
    from .maps import map_from_dict
    from .rules import rules_from_dict
    cmap = map_from_dict(receipt["map"]["content"]) if receipt.get("map") else None
    ps = rules_from_dict(receipt["pack"]["content"]) if receipt.get("pack") else None
    if cmap is not None:
        steps.append(("map hash", cmap.sha256 == receipt["map"]["sha256"], cmap.version))
    if ps is not None:
        steps.append(("rule hash", ps.sha256 == receipt["pack"]["sha256"], ps.version))
    o = receipt["options"]
    tol = {} if o.get("defaults_from_pack") else dict(
        abs_tol=o.get("abs_tol"), rel_tol=o.get("rel_tol"), floor=o.get("floor"),
        log_tol=o.get("log_tol"), log_floor=o.get("log_floor"))
    if inp.get("format") == "records-json":
        rows = json.loads(p.read_text(encoding="utf-8"))
        table = rows
    else:
        table = p
    fresh = compare_table(table, key=o["key"], pack=ps, map=cmap, assume=o.get("assume", []),
                          precision=o.get("precision", "stated"), **tol).receipt
    f = {k: v for k, v in fresh.items() if k != "sha256"}
    for k in ("consilience_version", "pint_version"):
        f[k] = receipt.get(k)
    f["input"] = receipt.get("input")
    same = sha256_json(f) == recorded == integrity
    steps.append(("re-run", same, "same outputs and summary" if same else
                  "the re-run gives different outputs"))
    note = ""
    if receipt.get("consilience_version") != __version__:
        note = (f"receipt made with consilience {receipt.get('consilience_version')}; "
                f"re-run with {__version__}")
    return all(s[1] for s in steps), steps, note


__all__ = ["compare_table", "TableResult", "read_table", "verify_table",
           "TABLE_RECEIPT_SCHEMA"]
