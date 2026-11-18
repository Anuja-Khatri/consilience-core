"""The ``consilience`` command.

    consilience compare A.json B.json [--pack NAME|FILE] [--abs-tol Q] [--rel-tol X]
                        [--floor Q] [--exact] [--json] [--receipt FILE]
    consilience check DATA.csv --rules RULES.yaml [--json] [--html FILE] [--receipt FILE]
    consilience verify RECEIPT.json [--data FILE]
    consilience examples [DIR] [--force]
    consilience packs
    consilience version

Exit codes
    compare  0 agree or within_floor · 1 disagree · 2 not_comparable, not_stated or
             undecidable_bounds · 3 unparseable
    check    0 no violations · 1 violations · 3 some cells could not be read
    verify   0 re-run reproduces the receipt · 1 it does not
    all      64 usage or input error (missing file, unknown field, bad rule file)

Optional, from a source checkout with ``pip install "consilience[nanopub]"``:
    consilience export --nanopub RECORD.json ... · consilience agent ... ·
    consilience templates publish ...   (these exit 2 when they refuse)
"""

from __future__ import annotations

import argparse
import json
import shutil
import os
import sys
from importlib import resources
from pathlib import Path

from . import __version__
from .check import check
from .compare import InputError, compare
from .rules import BUNDLED_PACKS, RuleFileError, bundled_path, load_rules
from .verify import verify

EXIT_USAGE = 64
REPO_ROOT = Path(__file__).resolve().parents[2]   # a source checkout (nanopub commands)
EXAMPLE_FILES = ("measurement_a.json", "measurement_b.json", "measurement_c.json",
                 "measurement_d.json", "measurement_e.json", "readings.csv",
                 "readings_rules.yaml")


class _Parser(argparse.ArgumentParser):
    """argparse exits 2 on a usage error; 2 is a verdict here, so use 64."""

    def error(self, message: str):  # pragma: no cover - exercised via subprocess
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def _g(x) -> str:
    return f"{x:.6g}" if isinstance(x, float) else str(x)


# ------------------------------------------------------------------ compare
def _side_line(s: dict, unit) -> str:
    ag = s.get("as_given", {})
    given = " ".join(str(ag[k]) for k in ("value", "unit") if ag.get(k) is not None)
    if ag.get("uncertainty") is not None:
        given += f" ± {ag['uncertainty']}"
    if s.get("value") is None:
        out = given or "(no value)"
    else:
        out = f"{_g(s['value'])} {unit}"
        if s.get("bound"):
            out = f"{s['bound']} {out}"
        if s.get("uncertainty"):
            out += f" ± {_g(s['uncertainty'])} {unit}"
        if given and given != out:
            out += f"   (as given: {given})"
    if s.get("label"):
        out += f"   [{s['label']}]"
    return out


def _fmt_compare(r) -> str:
    rec = r.receipt
    res = rec["result"]
    unit = res["unit"] or ""
    if unit.strip() == "1":
        unit = "dimensionless"
    out = [f"verdict:    {r.label}",
           f"a:          {_side_line(res['a'], unit)}",
           f"b:          {_side_line(res['b'], unit)}"]
    comparison = res.get("comparison", "values")
    if r.tolerance is not None and comparison != "values":
        out += _bound_lines(res, r, unit)
    if r.tolerance is not None:
        if comparison == "values":
            out.append(f"difference: {_g(r.difference)} {unit}")
        out += [f"tolerance:  {_g(r.tolerance)} {unit}   (larger of --abs-tol and "
                "--rel-tol x the larger value)",
                f"floor:      {_g(r.floor)} {unit}   (largest of --floor and the two "
                "uncertainties)"]
    out += _precision_lines(res.get("precision"), unit)
    rule_text = {}
    if rec["pack"] is not None:
        rule_text = {c["id"]: c["plain_english"] for c in rec["pack"]["content"]["conditions"]}
    for d in r.defects:
        line = f"  {d['verdict']:<15} {d['target']}"
        if d["verdict"] == "unparseable" or d["reason"] not in ("differs", "missing",
                                                                "unstated"):
            line += f": {d['reason']}"
        if d["detail"]:
            line += f" ({d['detail']})"
        if d.get("rule"):
            line += f"\n                  rule {d['rule']}: {rule_text.get(d['rule'], '')}"
        out.append(line)
    cond = res["conditions"]
    if rec["pack"] is not None:
        p = rec["pack"]
        out.append(f"conditions: checked with pack {p['name']} ({p['version']}): "
                   + (", ".join(cond["checked"])))
        if cond["ignored"]:
            out.append(f"            not checked (not in the pack): {', '.join(cond['ignored'])}")
        out.append(f"pack hash:  {p['sha256']}")
    else:
        out.append("conditions: no pack: every condition on either side must match"
                   + (f" ({', '.join(cond['checked'])})" if cond["checked"] else
                      " (none given)"))
    out.append(f"receipt:    sha256 {rec['sha256']}")
    return "\n".join(out)


def _bound_lines(res, r, unit) -> list:
    """What was compared when one or both sides are bounds."""
    a, b = res["a"], res["b"]
    if res["comparison"] == "value_vs_bound":
        v, bs = ("a", "b") if b.get("bound") else ("b", "a")
        return [f"beyond:     {_g(r.difference)} {unit}   (how far {v} lies past {bs}'s "
                "bound; 0 means it satisfies it)"]
    pair = (f"a {a['bound']} {_g(a['value'])} {unit} and b {b['bound']} "
            f"{_g(b['value'])} {unit}")
    if r.verdict == "undecidable_bounds":
        return [f"bounds:     {pair} can both hold, so there is no single value to "
                "compare"]
    return [f"bounds:     {pair} cannot both hold (they are {_g(r.difference)} {unit} "
            "apart)"]


def _precision_lines(p, unit) -> list:
    """The stated-precision lines of a compare result (none for a 0.1.0 receipt)."""
    if not p:
        return []
    if p["mode"] == "exact":
        return ["precision:  exact (--exact): no tolerance is implied by how the values "
                "are written"]
    if p.get("implied") is None or all(p[s]["rule"] == "uncertainty stated"
                                       for s in ("a", "b")):
        return []
    if p["implied"]:
        out = [f"precision:  ±{_g(p['implied'])} {unit} implied by stated precision (added "
               "to the tolerance and the floor; --exact turns this off)"]
    else:
        out = ["precision:  none implied by stated precision (no value has decimal places "
               "without an uncertainty)"]
    for side in ("a", "b"):
        sp = p[side]
        written = sp["written"] if sp["written"] is not None else "(no written form)"
        line = f"            {side} {written}: {sp['rule']}"
        if sp["implied"]:
            line += f", ±{_g(sp['implied'])} {unit}"
        out.append(line)
    return out


def _write_receipt(path, receipt) -> None:
    Path(path).write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def cmd_compare(args) -> int:
    try:
        r = compare(args.a, args.b, pack=args.pack, abs_tol=args.abs_tol,
                    rel_tol=args.rel_tol, floor=args.floor,
                    precision="exact" if args.exact else "stated")
    except (InputError, RuleFileError) as exc:
        print(f"consilience: error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.receipt:
        _write_receipt(args.receipt, r.receipt)
    if args.json:
        print(json.dumps(r.receipt, indent=2, ensure_ascii=False))
    else:
        print(_fmt_compare(r))
        if args.receipt:
            print(f"wrote:      {args.receipt}")
    return r.exit_code


# -------------------------------------------------------------------- check
def _fmt_check(c, data, rules_arg) -> str:
    rec = c.receipt
    s = c.summary
    res = rec["result"]
    out = [f"data:        {data} ({s['rows']} rows; sha256 {rec['inputs']['data']['sha256']})",
           f"rules:       {rec['rules']['version']} ({rules_arg})",
           f"rule hash:   {rec['rules']['sha256']}",
           f"violations:  {s['violations']}"]
    for v in res["violations"]:
        who = f"{v['id']}  " if v["id"] is not None else ""
        if "bound" in v:
            op = {"min": "<" if v["inclusive"] else "<=",
                  "max": ">" if v["inclusive"] else ">="}[v["bound"]]
            what = f"{op} {v['bound']} {_g(v['limit'])} {v['limit_unit']}"
        else:
            op = ">" if v["must_be"] == "at_most" else "<"
            sign = "+" if v["must_be"] == "at_most" else "-"
            src = "fallback limit" if v["route"] == "fallback_limit" else v["limit_column"]
            what = (f"{op} {src} {_g(v['limit'])} {v['limit_unit']} {sign} margin "
                    f"{_g(v['margin'])} {v['limit_unit']}")
            if v["value_offset"]:
                what = f"(+ offset {_g(v['value_offset'])} {v['limit_unit']}) " + what
        out.append(f"  line {v['line']:<4} {who}{v['rule']}  {v['column']} {v['value']} "
                   f"{v['unit']} {what}   row receipt {v['row_sha256'][:12]}")
    n = s["unparseable_cells"]
    out.append(f"could not read: {n} cell{'s' if n != 1 else ''}"
               + (" (not checked; nothing was guessed)" if n else ""))
    for u in res["unparseable"]:
        who = f"{u['id']}  " if u["id"] is not None else ""
        col = u["column"] or "(whole row)"
        rules = ", ".join(x for x in u["rules"] if x)
        out.append(f"  line {u['line']:<4} {who}{col} {json.dumps(u['text'], ensure_ascii=False)}: "
                   f"{u['reason']} (needed by {rules})")
    out.append(f"skipped empty: {s['skipped_empty']}")
    if s["blank_lines"]:
        out.append(f"blank lines: {s['blank_lines']}")
    meaning = {0: "no violations; every needed cell was read",
               1: "violations found",
               3: "some cells could not be read, so the check is incomplete"}
    out.append(f"result:      exit {c.exit_code}: {meaning[c.exit_code]}")
    out.append(f"receipt:     sha256 {rec['sha256']}")
    return "\n".join(out)


def cmd_check(args) -> int:
    try:
        c = check(args.data, args.rules)
    except (InputError, RuleFileError) as exc:
        print(f"consilience: error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.receipt:
        _write_receipt(args.receipt, c.receipt)
    if args.html:
        Path(args.html).write_text(c.to_html(), encoding="utf-8")
    if args.json:
        print(json.dumps(c.receipt, indent=2, ensure_ascii=False))
    else:
        print(_fmt_check(c, args.data, args.rules))
        for label, path in (("wrote", args.html), ("wrote", args.receipt)):
            if path:
                print(f"{label}:       {path}")
    return c.exit_code


# ------------------------------------------------------------------- verify
def cmd_verify(args) -> int:
    try:
        v = verify(args.receipt, data=args.data)
    except (InputError, RuleFileError) as exc:
        print(f"consilience: error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(f"{'ok' if v.ok else 'FAILED'}: {args.receipt} ({v.command})")
    for name, ok, detail in v.steps:
        print(f"  {'ok ' if ok else 'BAD'} {name}: {detail}")
    if v.recorded_sha256:
        print(f"  recorded sha256   {v.recorded_sha256}")
    if v.recomputed_sha256 and v.recomputed_sha256 != v.recorded_sha256:
        print(f"  recomputed sha256 {v.recomputed_sha256}")
    if v.note:
        print(f"  note: {v.note}")
    return v.exit_code


# ----------------------------------------------------------------- examples
def cmd_examples(args) -> int:
    dest = Path(args.dir)
    dest.mkdir(parents=True, exist_ok=True)
    src = resources.files("consilience").joinpath("data", "examples")
    files = [(src.joinpath(n), n) for n in EXAMPLE_FILES]
    files += [(bundled_path(p), f"{p}.yaml") for p in BUNDLED_PACKS]
    clash = [n for _, n in files if (dest / n).exists()]
    if clash and not args.force:
        print(f"consilience: error: {dest} already has {clash}; use --force to overwrite",
              file=sys.stderr)
        return EXIT_USAGE
    for s, n in files:
        with s.open("rb") as fh, open(dest / n, "wb") as out:
            shutil.copyfileobj(fh, out)
        print(f"wrote {dest / n}")
    print("These examples are MADE UP for trying the tool; they are not real data.")
    return 0


def cmd_packs(args) -> int:
    for name in BUNDLED_PACKS:
        p = load_rules(name)
        print(f"{name}  {p.version}  sha256 {p.sha256}")
        print(f"  {p.content['plain_english']}")
        print(f"  conditions: {', '.join(c['field'] for c in p.rules)}")
    return 0


# ----------------------------------------------------------------- nanopub
def _nanopub(name):
    def run(args) -> int:
        try:
            from . import nanopub_cli as N
        except ImportError as exc:
            print(f"consilience: error: the nanopub commands need the optional "
                  f"dependencies: pip install \"consilience[nanopub]\" ({exc})",
                  file=sys.stderr)
            return EXIT_USAGE
        from .agent import AgentError
        from .export.nanopub import ExportError
        from .receipts import ReceiptError
        if args.config is None:
            args.config = str(REPO_ROOT / "config" / "agent.json")
        if args.templates is None:
            args.templates = str(N.TEMPLATES_CONFIG)
        try:
            return getattr(N, name)(args)
        except (ReceiptError, ExportError, AgentError) as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
    return run


def build_parser() -> argparse.ArgumentParser:
    ap = _Parser(prog="consilience",
                 description="Compare two measurements with units and conditions, and check "
                             "a table against written limits. Every result has a receipt.",
                 epilog="Exit codes: compare 0 agree/within_floor, 1 disagree, 2 "
                        "not_comparable/not_stated/undecidable_bounds, 3 unparseable; check 0 clean, 1 "
                        "violations, 3 unreadable cells; verify 0 ok, 1 failed; 64 usage or "
                        "input error.")
    ap.add_argument("--version", action="version", version=f"consilience {__version__}")
    ap.add_argument("--config", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--templates", default=None, help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", metavar="COMMAND", parser_class=_Parser)

    c = sub.add_parser("compare", help="compare two measurements (exit 0/1/2/3, 64 error)")
    c.add_argument("a", help="measurement A (JSON file)")
    c.add_argument("b", help="measurement B (JSON file)")
    c.add_argument("--pack", help="domain pack: a bundled name (electrochemistry) or a YAML "
                                  "file; without one, every condition must match")
    c.add_argument("--abs-tol", help="absolute tolerance, e.g. '5 mV' (a bare number is in "
                                     "A's unit)")
    c.add_argument("--rel-tol", help="relative tolerance as a fraction, e.g. 0.01 for 1%%")
    c.add_argument("--floor", help="spread below which a difference is within_floor, e.g. "
                                   "'13 mV' (measured lab-to-lab spread)")
    c.add_argument("--exact", action="store_true",
                   help="compare the values exactly as numbers; by default a value written "
                        "with k decimal places (and no uncertainty) carries an implied "
                        "half-unit in its last place, so 0.777 means 0.7765 to 0.7775")
    c.add_argument("--json", action="store_true", help="print the full result as JSON")
    c.add_argument("--receipt", metavar="FILE", help="also write the receipt to FILE")
    c.set_defaults(func=cmd_compare)

    k = sub.add_parser("check", help="check a CSV table against rules (exit 0/1/3, 64 error)")
    k.add_argument("data", help="the table (CSV with a header row)")
    k.add_argument("--rules", required=True, help="the rule file (YAML)")
    k.add_argument("--json", action="store_true", help="print the full report as JSON")
    k.add_argument("--html", metavar="FILE", help="also write a readable HTML report")
    k.add_argument("--receipt", metavar="FILE", help="also write the JSON report to FILE")
    k.set_defaults(func=cmd_check)

    v = sub.add_parser("verify", help="re-run a result from its receipt and confirm the hash")
    v.add_argument("receipt", help="a receipt written by --receipt (or a record envelope)")
    v.add_argument("--data", help="where the data file of a check receipt is now")
    v.set_defaults(func=cmd_verify)

    e = sub.add_parser("examples", help="write the made-up example files into DIR")
    e.add_argument("dir", nargs="?", default=".", help="target directory (default: .)")
    e.add_argument("--force", action="store_true", help="overwrite existing files")
    e.set_defaults(func=cmd_examples)

    sub.add_parser("packs", help="list the bundled domain packs").set_defaults(func=cmd_packs)
    sub.add_parser("version", help="print the version").set_defaults(
        func=lambda a: print(f"consilience {__version__}") or 0)

    # optional nanopublication commands (need the [nanopub] extra and a source checkout)
    x = sub.add_parser("export", help="(nanopub extra) export a record as a nanopublication")
    x.add_argument("--nanopub", required=True, metavar="RECORD_JSON")
    x.add_argument("--dry-run", action="store_true", help="write TriG, do not publish")
    x.add_argument("--unsigned", action="store_true", help="with --dry-run: do not sign")
    x.add_argument("--out", help="output TriG path")
    x.add_argument("--created", help="override dct:created (for reproducible dry runs)")
    x.add_argument("--example", action="store_true",
                   help="publish as an npx:ExampleNanopub (label \"Example: ...\")")
    x.add_argument("--supersedes", metavar="NANOPUB_URI",
                   help="a corrected claim card: supersede this nanopub, keep its claim IRI")
    x.set_defaults(func=_nanopub("cmd_export"))
    a = sub.add_parser("agent", help="(nanopub extra) the engine's software-agent identity")
    a.add_argument("action", choices=["keygen", "introduce"])
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--replace", action="store_true",
                   help="introduce the agent anew (a new agent IRI); the old one is kept in the config")
    a.add_argument("--created")
    a.set_defaults(func=_nanopub("cmd_agent"))
    t = sub.add_parser("templates", help="(nanopub extra) nanopublication templates")
    t.add_argument("action", choices=["publish"])
    t.add_argument("--dry-run", action="store_true")
    t.add_argument("--only", nargs="*")
    t.add_argument("--created")
    t.set_defaults(func=_nanopub("cmd_templates"))
    return ap


EXIT_BROKEN_PIPE = 141  # 128 + SIGPIPE: output reader went away; the verdict was not fully written


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help(sys.stderr)
        return EXIT_USAGE
    try:
        return args.func(args)
    except BrokenPipeError:
        # The reader closed the pipe early (e.g. `| head -1`). Exit quietly with the
        # conventional SIGPIPE status, as standard command-line tools do, instead of
        # printing a traceback. Python's documented recipe: point stdout at devnull so
        # the interpreter's final flush cannot raise again.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return EXIT_BROKEN_PIPE


if __name__ == "__main__":
    sys.exit(main())
