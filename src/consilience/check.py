"""Check a table (CSV) against a rule file of limits and physical bounds.

Two kinds of rule (full format in docs/RULES.md):

    bound   a column must lie within [min, max] (physical bounds, e.g. not below 0 K)
    limit   a column must be at most (or at least) the value in another column of the
            same row, within a margin (e.g. a reading must not exceed its own recorded
            instrument limit)

Every number cell a rule needs is read strictly (see ``consilience.units``). A cell that
cannot be read is reported with its line, column, text and reason, and counted; it is
never skipped silently and never guessed. An empty cell is refused too, unless the rule
says ``if_empty: skip`` (then it is counted as skipped). A row with the wrong number of
cells is refused whole. Lines starting with ``#`` before the header are comments.

Exit codes: 0 no violations and every needed cell read; 1 violations found; 3 some cells
could not be read (the check is incomplete; any violations are still listed);
64 unusable input (missing file or column, bad rule file).

Each violation carries a row receipt::

    row_sha256 = sha256(canonical_json({"rules_sha256": ..., "rule": <id>,
                                        "line": <line number>, "cells": {header: text}}))

and the whole report is a receipt that ``consilience verify`` can re-run.
"""

from __future__ import annotations

import copy
import csv
import html
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from . import __version__
from .compare import PINT_VERSION, RECEIPT_SCHEMA, ROUNDING, InputError
from .hashing import sha256_bytes, sha256_json
from .rules import RuleSet, load_rules
from .units import UnitError, as_quantity, convert, convert_difference, parse_number, \
    parse_unit

EXIT_CLEAN, EXIT_VIOLATIONS, EXIT_UNPARSEABLE = 0, 1, 3


@dataclass
class CheckResult:
    summary: dict
    violations: list
    unparseable: list
    rules: dict
    receipt: dict = field(repr=False)

    @property
    def exit_code(self) -> int:
        if self.summary["unparseable_cells"]:
            return EXIT_UNPARSEABLE
        return EXIT_VIOLATIONS if self.summary["violations"] else EXIT_CLEAN

    def to_dict(self) -> dict:
        return copy.deepcopy(self.receipt)

    def to_html(self) -> str:
        return render_html(self.receipt)


class _Bad(Exception):
    def __init__(self, column, reason, detail=""):
        self.column, self.reason, self.detail = column, reason, detail


def _read_table(path: Path):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InputError(f"{path}: not UTF-8 text") from None
    lines = text.splitlines(keepends=True)
    skip = 0
    while skip < len(lines) and lines[skip].lstrip().startswith("#"):
        skip += 1
    reader = csv.reader(io.StringIO("".join(lines[skip:])), strict=True)
    try:
        header = next(reader)
    except StopIteration:
        raise InputError(f"{path}: no header row") from None
    except csv.Error as exc:
        raise InputError(f"{path}: cannot read the header: {exc}") from None
    header = [h.strip() for h in header]
    if not header or any(not h for h in header):
        raise InputError(f"{path}: the header has an empty column name")
    dup = sorted({h for h in header if header.count(h) > 1})
    if dup:
        raise InputError(f"{path}: duplicate column name(s) {dup}")
    rows = []
    prev = reader.line_num
    try:
        for cells in reader:
            rows.append((skip + prev + 1, cells))
            prev = reader.line_num
    except csv.Error as exc:
        raise InputError(f"{path}: line {skip + reader.line_num}: {exc}") from None
    return raw, header, rows


def check(data: Union[str, Path], rules: Union[str, Path, RuleSet]) -> CheckResult:
    """Check the CSV file ``data`` against ``rules`` (a path or a loaded RuleSet).

    Raises ``InputError`` (missing file, unreadable CSV, a declared column absent) or
    ``RuleFileError`` (an unusable rule file).
    """
    rs = load_rules(rules)
    if rs.kind != "check-rules":
        raise InputError(f"{rs.origin} is a {rs.kind} file; `check` needs a check-rules file")
    p = Path(data)
    if not p.is_file():
        raise InputError(f"file not found: {data}")
    raw, header, rows = _read_table(p)
    C = rs.content
    cols = C["columns"]
    needed = set(cols) | {c["unit_column"] for c in cols.values() if "unit_column" in c}
    if C.get("id_column"):
        needed.add(C["id_column"])
    missing = sorted(needed - set(header))
    if missing:
        raise InputError(f"{data}: column(s) {missing} named in the rule file are not in the "
                         f"header {header}")
    fixed_units = {c: parse_unit(s["unit"]) for c, s in cols.items() if "unit" in s}

    violations, issues = [], {}
    by_rule = {r["id"]: {"violations": 0, "unparseable": 0, "skipped": 0, "passed": 0}
               for r in C["rules"]}
    n_rows = blank = 0

    def report(line, rid, ident, column, reason, text, detail=""):
        key = (line, column, reason)
        if key not in issues:
            issues[key] = {"line": line, "id": ident, "column": column, "reason": reason,
                           "text": text, "detail": detail, "rules": []}
        if rid not in issues[key]["rules"]:
            issues[key]["rules"].append(rid)

    for line, cells in rows:
        if not cells:
            blank += 1
            continue
        n_rows += 1
        ident = None
        if len(cells) != len(header):
            report(line, None, None, None, "row_length", ",".join(cells),
                   f"{len(cells)} cells, header has {len(header)}")
            for r in C["rules"]:
                by_rule[r["id"]]["unparseable"] += 1
            issues[(line, None, "row_length")]["rules"] = [r["id"] for r in C["rules"]]
            continue
        row = dict(zip(header, cells))
        if C.get("id_column"):
            ident = row[C["id_column"]]

        def unit_of(col):
            if col in fixed_units:
                return fixed_units[col]
            ucol = cols[col]["unit_column"]
            try:
                return parse_unit(row[ucol])
            except UnitError as exc:
                raise _Bad(ucol, exc.reason, exc.detail) from None

        def unit_written(col):
            return (cols[col]["unit"] if col in fixed_units
                    else row[cols[col]["unit_column"]].strip())

        def value_of(col):
            t = row[col].strip()
            if not t:
                return None
            try:
                num = parse_number(t)
            except UnitError as exc:
                raise _Bad(col, exc.reason, exc.detail) from None
            return num, unit_of(col)

        def dim_column(*cs):
            for c in cs:
                if "unit_column" in cols[c]:
                    return cols[c]["unit_column"]
            return cs[0]

        for r in C["rules"]:
            rid, col = r["id"], r["column"]
            st = by_rule[rid]
            try:
                v = value_of(col)
                if v is None:
                    if r["if_empty"] == "skip":
                        st["skipped"] += 1
                        continue
                    raise _Bad(col, "empty", "the rule needs a number here")
                num, u = v
                scale = abs(num)
                base = {"rule": r["id"], "line": line, "id": ident, "column": col,
                        "value": row[col].strip(), "unit": unit_written(col),
                        "plain_english": r["plain_english"]}
                hit = None
                if r["kind"] == "bound":
                    for side in ("min", "max"):
                        if side not in r:
                            continue
                        q = as_quantity(r[side])
                        try:
                            lim = (float(q.magnitude) if str(q.units) == "dimensionless"
                                   else convert(q, u))
                        except UnitError as exc:
                            raise _Bad(dim_column(col), exc.reason, exc.detail) from None
                        sl = ROUNDING * max(scale, abs(lim))
                        incl = r[f"{side}_inclusive"]
                        if side == "min":
                            bad = num < lim - sl if incl else num <= lim + sl
                        else:
                            bad = num > lim + sl if incl else num >= lim - sl
                        if bad:
                            hit = dict(base, bound=side, limit=lim, limit_unit=unit_written(col),
                                       inclusive=incl)
                            break
                else:
                    lcol = r["limit_column"]
                    route = "recorded_limit"
                    lv = value_of(lcol)
                    try:
                        if lv is None:
                            fb = r["if_limit_empty"]
                            if fb == "skip":
                                st["skipped"] += 1
                                continue
                            if fb == "refuse":
                                raise _Bad(lcol, "empty", "the rule needs a limit here")
                            q = as_quantity(fb)
                            lim = (convert(as_quantity(float(q.magnitude)) * unit_of(lcol), u)
                                   if str(q.units) == "dimensionless" else convert(q, u))
                            route, ltext = "fallback_limit", str(fb)
                        else:
                            lim = convert(as_quantity(lv[0]) * lv[1], u)
                            ltext = row[lcol].strip()

                        def diff(x):
                            qx = as_quantity(x)
                            if str(qx.units) == "dimensionless":
                                return float(qx.magnitude)   # in the column's own unit
                            return convert_difference(qx.magnitude, qx.units, u)
                        margin, off = diff(r["margin"]), diff(r["value_offset"])
                    except UnitError as exc:
                        raise _Bad(dim_column(col, lcol), exc.reason, exc.detail) from None
                    x = num + off
                    sl = ROUNDING * max(abs(x), abs(lim))
                    bad = (x > lim + margin + sl) if r["must_be"] == "at_most" else \
                        (x < lim - margin - sl)
                    if bad:
                        hit = dict(base, limit_column=lcol, limit_text=ltext, limit=lim,
                                   limit_unit=unit_written(col), margin=margin,
                                   value_offset=off, must_be=r["must_be"], route=route)
                if hit is None:
                    st["passed"] += 1
                else:
                    hit["row_sha256"] = sha256_json({"rules_sha256": rs.sha256,
                                                     "rule": rid, "line": line,
                                                     "cells": row})
                    violations.append(hit)
                    st["violations"] += 1
            except _Bad as b:
                st["unparseable"] += 1
                report(line, rid, ident, b.column, b.reason,
                       row.get(b.column, ""), b.detail)

    unparseable = sorted(issues.values(), key=lambda i: (i["line"], i["column"] or ""))
    summary = {
        "rows": n_rows,
        "blank_lines": blank,
        "rules": len(C["rules"]),
        "violations": len(violations),
        "unparseable_cells": len(unparseable),
        "skipped_empty": sum(s["skipped"] for s in by_rule.values()),
        "by_rule": by_rule,
    }
    result = {"summary": summary, "violations": violations, "unparseable": unparseable,
              "header": header}
    exit_code = (EXIT_UNPARSEABLE if unparseable else
                 EXIT_VIOLATIONS if violations else EXIT_CLEAN)
    result["exit_code"] = exit_code
    receipt = {
        "receipt": RECEIPT_SCHEMA,
        "command": "check",
        "consilience_version": __version__,
        "pint_version": PINT_VERSION,
        "inputs": {"data": {"path": str(data), "sha256": sha256_bytes(raw),
                            "bytes": len(raw)}},
        "rules": dict(rs.describe(), content=rs.content),
        "result": result,
    }
    receipt["sha256"] = sha256_json(receipt)
    return CheckResult(summary=summary, violations=violations, unparseable=unparseable,
                       rules=rs.describe(), receipt=receipt)


# --------------------------------------------------------------------- HTML
_CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:2rem;color:#1b1b1b;
max-width:72rem}
h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{border:1px solid #ccc;padding:.3rem .5rem;text-align:left;vertical-align:top}
th{background:#f2f2f2}code{font-size:.85rem}.hash{font-family:monospace;font-size:.75rem;
word-break:break-all}.note{color:#555}
"""


def _fmt(x) -> str:
    if isinstance(x, float):
        return f"{x:.6g}"
    return "" if x is None else str(x)


def render_html(receipt: dict) -> str:
    """A self-contained HTML page for a check receipt. Every value is escaped."""
    e = html.escape
    res, rules = receipt["result"], receipt["rules"]
    s = res["summary"]
    rule_text = {r["id"]: r["plain_english"] for r in rules["content"]["rules"]}
    out = ["<!DOCTYPE html>", '<html lang="en"><head><meta charset="utf-8">',
           f"<title>Data check: {e(receipt['inputs']['data']['path'])}</title>",
           f"<style>{_CSS}</style></head><body>",
           f"<h1>Data check: {e(receipt['inputs']['data']['path'])}</h1>",
           "<table>",
           f"<tr><th>Rules</th><td>{e(rules['name'])} ({e(rules['version'])})<br>"
           f"<span class='hash'>sha256 {e(rules['sha256'])}</span></td></tr>",
           f"<tr><th>Data</th><td>{s['rows']} rows, {receipt['inputs']['data']['bytes']} "
           f"bytes<br><span class='hash'>sha256 {e(receipt['inputs']['data']['sha256'])}"
           "</span></td></tr>",
           f"<tr><th>Violations</th><td>{s['violations']}</td></tr>",
           f"<tr><th>Cells that could not be read</th><td>{s['unparseable_cells']}"
           + (" (the check is incomplete for these rows)" if s["unparseable_cells"] else "")
           + "</td></tr>",
           f"<tr><th>Empty cells skipped by rule</th><td>{s['skipped_empty']}</td></tr>",
           f"<tr><th>Blank lines</th><td>{s['blank_lines']}</td></tr>",
           f"<tr><th>Report receipt</th><td class='hash'>sha256 {e(receipt['sha256'])}</td>"
           "</tr>",
           f"<tr><th>Made with</th><td>consilience {e(receipt['consilience_version'])}"
           "</td></tr>",
           "</table>",
           "<h2>Rules</h2><table><tr><th>Rule</th><th>What it says</th><th>Violations</th>"
           "<th>Could not check</th><th>Skipped</th><th>Passed</th></tr>"]
    for rid, st in s["by_rule"].items():
        out.append(f"<tr><td>{e(rid)}</td><td>{e(rule_text.get(rid, ''))}</td>"
                   f"<td>{st['violations']}</td><td>{st['unparseable']}</td>"
                   f"<td>{st['skipped']}</td><td>{st['passed']}</td></tr>")
    out.append("</table><h2>Violations</h2>")
    if res["violations"]:
        out.append("<table><tr><th>Line</th><th>Row id</th><th>Rule</th><th>Column</th>"
                   "<th>Value</th><th>Limit</th><th>Row receipt</th></tr>")
        for v in res["violations"]:
            if "bound" in v:
                lim = e(f"{v['bound']} {_fmt(v['limit'])} {v['limit_unit']}"
                        + ("" if v["inclusive"] else " (exclusive)"))
            else:
                op = "&le;" if v["must_be"] == "at_most" else "&ge;"
                lim = (f"{op} {e(v['limit_column'])} = "
                       + e(f"{_fmt(v['limit'])} {v['limit_unit']}, margin {_fmt(v['margin'])} "
                           f"{v['limit_unit']}"
                           + (f", value offset {_fmt(v['value_offset'])} {v['limit_unit']}"
                              if v["value_offset"] else "")
                           + (" (fallback limit)" if v["route"] == "fallback_limit" else "")))
            out.append(f"<tr><td>{v['line']}</td><td>{e(_fmt(v['id']))}</td>"
                       f"<td>{e(v['rule'])}</td><td>{e(v['column'])}</td>"
                       f"<td>{e(v['value'])} {e(v['unit'])}</td>"
                       f"<td>{lim}</td>"
                       f"<td class='hash'>{e(v['row_sha256'])}</td></tr>")
        out.append("</table>")
    else:
        out.append("<p>None.</p>")
    out.append("<h2>Cells that could not be read</h2>")
    if res["unparseable"]:
        out.append("<p class='note'>These cells were not guessed. Fix them and run the "
                   "check again.</p><table><tr><th>Line</th><th>Row id</th><th>Column</th>"
                   "<th>Text</th><th>Reason</th><th>Needed by</th></tr>")
        for u in res["unparseable"]:
            out.append(f"<tr><td>{u['line']}</td><td>{e(_fmt(u['id']))}</td>"
                       f"<td>{e(_fmt(u['column']) or '(whole row)')}</td>"
                       f"<td><code>{e(u['text'])}</code></td>"
                       f"<td>{e(u['reason'])}{': ' + e(u['detail']) if u['detail'] else ''}"
                       f"</td><td>{e(', '.join(x for x in u['rules'] if x))}</td></tr>")
        out.append("</table>")
    else:
        out.append("<p>None.</p>")
    out.append("<p class='note'>Re-run this report and confirm its hash with "
               "<code>consilience verify &lt;receipt.json&gt;</code>.</p></body></html>")
    return "\n".join(out) + "\n"


__all__ = ["CheckResult", "InputError", "check", "render_html"]
