"""Evaluator contracts for `consilience stress` (spec v1.0 §6).

A contract says how to call a scoring function, what a valid answer is (independently of the
scorer), which transformations must not change the true score, which direction is better, and
the record as published. `load_contract` validates and normalises it, and fails with a named
error on anything it does not understand. Nothing is guessed.
"""

from __future__ import annotations

import ast
import decimal
import hashlib
import importlib.util
import re
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from ..hashing import sha256_json

KIND = "evaluator-contract"

HARNESS_KINDS = ("function", "py_path", "cli_json", "sdk_dict", "template")
FIELD_TYPES = ("real", "int", "real_array", "int_array", "complex_array", "int_set", "graph", "ragged")
INT_TYPES = ("int", "int_array", "int_set")
ROLES = ("construction", "claimed", "fixed", "derived")
RULES = ("finite", "range", "shape", "count", "integral", "distinct", "alphabet", "sum", "norm",
         "in_disk", "in_box", "pairwise_separation", "convex_position", "convex_polygon_ordered",
         "no_k_collinear", "no_k_coplanar", "graph_simple", "predicate")
EQUALITY_RULES = ("sum", "norm")             # equalities on reals: tolerance required
TRANSFORMS = ("permute", "cyclic_shift", "conjugate", "scale", "translate", "rotate", "dihedral",
              "reflect", "negate", "relabel")
RECORD_KINDS = ("best_known", "threshold")
GLUE_FUNCTIONS = ("to_scorer", "compose", "project")
GLUE_TABLES = ("quantities", "predicates", "maps")


class ContractError(ValueError):
    """A contract that cannot be used as written. The message names the place and the problem."""


def _err(where: str, msg: str) -> ContractError:
    return ContractError(f"{where}: {msg}")


def _only(d: dict, allowed: set, where: str) -> None:
    extra = sorted(set(d) - allowed)
    if extra:
        raise _err(where, f"unknown key(s) {extra}; allowed: {sorted(allowed)}")


def _need(d: dict, key: str, where: str):
    if key not in d or d[key] is None:
        raise _err(where, f"'{key}' is required")
    return d[key]


def _decimal_text(v, where: str) -> str:
    """Numbers that set precision are written as strings, so their written digits are kept."""
    if isinstance(v, bool) or not isinstance(v, str):
        raise _err(where, f"must be written as a string (e.g. \"1.4557\") so its precision is known; got {v!r}")
    try:
        d = decimal.Decimal(v.strip())
    except decimal.InvalidOperation:
        raise _err(where, f"not a decimal number: {v!r}") from None
    if not d.is_finite():
        raise _err(where, f"must be finite: {v!r}")
    return v.strip()


def record_resolution(text: str) -> float:
    """Half a unit in the last written digit; 0 for integers (the engine's written-digit rule)."""
    exp = decimal.Decimal(text).as_tuple().exponent
    return 0.5 * 10.0 ** exp if exp < 0 else 0.0


# ---------------------------------------------------------------- shape and derived expressions

_TOK = re.compile(r"\s*(?:(\d+)|([A-Za-z_]\w*)|([+*()]))")


def eval_dim_expr(expr: Union[int, str], dims: dict, where: str) -> int:
    """Evaluate a shape entry: an int, a dim name, or + and * of those (with parentheses)."""
    if isinstance(expr, bool):
        raise _err(where, f"bad shape entry {expr!r}")
    if isinstance(expr, int):
        return expr
    if not isinstance(expr, str):
        raise _err(where, f"bad shape entry {expr!r}")
    toks, pos = [], 0
    while pos < len(expr):
        m = _TOK.match(expr, pos)
        if not m or m.end() == pos:
            if expr[pos:].strip() == "":
                break
            raise _err(where, f"bad shape expression {expr!r}")
        toks.append(m.group(1) or m.group(2) or m.group(3))
        pos = m.end()
    i = 0

    def atom():
        nonlocal i
        t = toks[i] if i < len(toks) else None
        if t is None:
            raise _err(where, f"bad shape expression {expr!r}")
        i += 1
        if t == "(":
            v = add()
            if i >= len(toks) or toks[i] != ")":
                raise _err(where, f"unbalanced parentheses in {expr!r}")
            i += 1
            return v
        if t.isdigit():
            return int(t)
        if t in dims:
            return int(dims[t])
        raise _err(where, f"unknown dim {t!r} in {expr!r} (dims: {sorted(dims)})")

    def mul():
        nonlocal i
        v = atom()
        while i < len(toks) and toks[i] == "*":
            i += 1
            v *= atom()
        return v

    def add():
        nonlocal i
        v = mul()
        while i < len(toks) and toks[i] == "+":
            i += 1
            v += mul()
        return v

    v = add()
    if i != len(toks):
        raise _err(where, f"bad shape expression {expr!r}")
    return v


_DERIVED = re.compile(r"^\s*(?:len\(\s*([A-Za-z_]\w*)\s*\)|([A-Za-z_]\w*)\.shape\[\s*(\d+)\s*\])\s*$")


def parse_derived(expr: str, where: str) -> tuple:
    """`len(x)` or `x.shape[i]` (a closed set); anything else must be a glue function."""
    m = _DERIVED.match(expr or "")
    if not m:
        raise _err(where, f"derived expression must be len(name) or name.shape[i]; got {expr!r}")
    return ("len", m.group(1)) if m.group(1) else ("shape", m.group(2), int(m.group(3)))


# ---------------------------------------------------------------- glue

def load_glue(path: Path, where: str):
    """Load a glue file. It must not import the scorer (spec §6.5), checked from its AST."""
    if not path.is_file():
        raise _err(where, f"glue file not found: {path}")
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        raise _err(where, f"glue file does not parse: {exc}") from None
    spec = importlib.util.spec_from_file_location(f"consilience_glue_{uuid.uuid4().hex[:8]}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    return mod, tree


def glue_imports(tree) -> set:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


# ---------------------------------------------------------------- contract

@dataclass
class Contract:
    data: dict                      # normalised contract (paths relative to `base`)
    base: Path                      # folder the contract's paths are relative to
    hash: str                       # sha256 of the normalised contract
    glue: Any = None                # loaded glue module or None
    glue_hash: Optional[str] = None
    origin: str = "<dict>"
    file_hashes: dict = field(default_factory=dict)   # relative path -> sha256 of every file the run reads

    # convenience views
    @property
    def fields(self) -> dict:
        return {f["name"]: f for f in self.data["fields"]}

    @property
    def construction(self) -> list:
        return [f["name"] for f in self.data["fields"] if f["role"] == "construction"]

    @property
    def claimed(self) -> list:
        return [f for f in self.data["fields"] if f["role"] == "claimed"]

    @property
    def direction_sign(self) -> float:
        return 1.0 if self.data["score"]["direction"] == "maximize" else -1.0

    def path(self, rel: str) -> Path:
        return (self.base / rel).resolve()

    def glue_fn(self, table: Optional[str], name: str):
        if self.glue is None:
            raise ContractError(f"{self.origin}: glue function {name!r} needed but no glue file is given")
        if table is None:
            fn = getattr(self.glue, name, None)
        else:
            fn = (getattr(self.glue, table, None) or {}).get(name)
        if not callable(fn):
            where = name if table is None else f"{table}[{name!r}]"
            raise ContractError(f"{self.origin}: glue has no callable {where}")
        return fn


def _norm_harness(h: dict, where: str) -> dict:
    if not isinstance(h, dict):
        raise _err(where, "must be a mapping")
    allowed = {"kind", "evaluator", "entry", "program_function", "argv", "result_file", "score_key",
               "reject", "timeout_s", "call_args", "program_template", "block_start", "block_end"}
    _only(h, allowed, where)
    kind = _need(h, "kind", where)
    if kind not in HARNESS_KINDS:
        raise _err(where, f"kind must be one of {list(HARNESS_KINDS)}; got {kind!r}")
    out = {"kind": kind, "evaluator": str(_need(h, "evaluator", where)),
           "timeout_s": float(h.get("timeout_s", 30)), "score_key": h.get("score_key"),
           "call_args": dict(h.get("call_args") or {})}
    if out["timeout_s"] <= 0:
        raise _err(where, "timeout_s must be positive")
    if kind in ("function", "py_path", "sdk_dict", "template"):
        out["entry"] = str(_need(h, "entry", where))
    if kind in ("py_path", "cli_json", "sdk_dict", "template"):
        out["program_function"] = str(_need(h, "program_function", where))
        if out["score_key"] is None:
            raise _err(where, f"score_key is required for kind {kind!r}")
    if kind == "cli_json":
        argv = _need(h, "argv", where)
        if not (isinstance(argv, list) and all(isinstance(a, str) for a in argv)):
            raise _err(where, "argv must be a list of strings")
        out["argv"] = list(argv)
        out["result_file"] = str(_need(h, "result_file", where))
    if kind == "template":
        out["program_template"] = str(_need(h, "program_template", where))
        out["block_start"] = str(_need(h, "block_start", where))
        out["block_end"] = str(_need(h, "block_end", where))
    rej = h.get("reject") or {}
    if not isinstance(rej, dict):
        raise _err(where + ".reject", "must be a mapping")
    _only(rej, {"keys_present", "values", "file"}, where + ".reject")
    vals = rej.get("values") or []
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
        raise _err(where + ".reject.values", "must be numbers")
    rf = rej.get("file")
    if rf is not None:
        if not isinstance(rf, dict):
            raise _err(where + ".reject.file", "must be a mapping {path, key, equals}")
        _only(rf, {"path", "key", "equals"}, where + ".reject.file")
        for k in ("path", "key"):
            _need(rf, k, where + ".reject.file")
        if "equals" not in rf:
            raise _err(where + ".reject.file", "'equals' is required")
    out["reject"] = {"keys_present": [str(k) for k in (rej.get("keys_present") or [])],
                     "values": [float(v) for v in vals], "file": rf}
    return out


def _norm_fields(fields, dims: dict, where: str) -> list:
    if not isinstance(fields, list) or not fields:
        raise _err(where, "must be a non-empty list")
    out, seen = [], set()
    for i, f in enumerate(fields):
        w = f"{where}[{i}]"
        if not isinstance(f, dict):
            raise _err(w, "must be a mapping")
        _only(f, {"name", "type", "shape", "role", "quantity", "value", "from", "dtype_note"}, w)
        name = str(_need(f, "name", w))
        if name in seen:
            raise _err(w, f"duplicate field name {name!r}")
        seen.add(name)
        typ = _need(f, "type", w)
        if typ not in FIELD_TYPES:
            raise _err(w, f"type must be one of {list(FIELD_TYPES)}; got {typ!r}")
        role = _need(f, "role", w)
        if role not in ROLES:
            raise _err(w, f"role must be one of {list(ROLES)}; got {role!r}")
        nf = {"name": name, "type": typ, "role": role}
        if "shape" in f and f["shape"] is not None:
            if not isinstance(f["shape"], list):
                raise _err(w, "shape must be a list")
            nf["shape"] = [eval_dim_expr(e, dims, w + ".shape") for e in f["shape"]]
        if role == "claimed":
            nf["quantity"] = str(_need(f, "quantity", w))
            if typ not in ("real", "int"):
                raise _err(w, "a claimed field must be of type real or int")
        if role == "fixed":
            if "value" not in f:
                raise _err(w, "a fixed field needs 'value'")
            nf["value"] = f["value"]
        if role == "derived":
            frm = str(_need(f, "from", w))
            if frm.startswith("glue:"):
                nf["from"] = frm
            else:
                parse_derived(frm, w + ".from")
                nf["from"] = frm
        out.append(nf)
    if not any(f["role"] == "construction" for f in out):
        raise _err(where, "at least one field must have role 'construction'")
    return out


def _norm_rule(r: dict, names: dict, where: str, glue_needed: set, dims: Optional[dict] = None) -> dict:
    if not isinstance(r, dict):
        raise _err(where, "must be a mapping")
    rule = _need(r, "rule", where)
    if rule not in RULES:
        raise _err(where, f"rule must be one of {list(RULES)}; got {rule!r}")
    common = {"rule", "field", "tolerance"}
    extra = {
        "finite": set(), "integral": set(), "distinct": set(), "convex_position": set(),
        "convex_polygon_ordered": set(), "graph_simple": {"n_from"},
        "range": {"min", "max"}, "shape": {"shape"}, "count": {"equals", "min", "max"},
        "alphabet": {"values"}, "sum": {"equals", "axis"}, "norm": {"equals", "axis"},
        "in_disk": {"radius", "center"}, "in_box": {"box", "margin_from"},
        "pairwise_separation": {"radii_from", "min_distance"},
        "no_k_collinear": {"k"}, "no_k_coplanar": {"k"},
        "predicate": {"call", "equality", "name"},
    }[rule]
    _only(r, common | extra, where)
    out = {"rule": rule}
    if rule != "predicate" or "field" in r:
        fname = _need(r, "field", where) if rule != "predicate" else r.get("field")
        if fname is not None:
            if fname not in names:
                raise _err(where, f"unknown field {fname!r}")
            out["field"] = fname
    tol = r.get("tolerance")
    out["tolerance"] = _decimal_text(tol, where + ".tolerance") if tol is not None else "0"
    if rule == "range":
        if "min" not in r and "max" not in r:
            raise _err(where, "range needs min and/or max")
        for k in ("min", "max"):
            if k in r and r[k] is not None:
                out[k] = _decimal_text(r[k], f"{where}.{k}")
    elif rule == "shape":
        sh = _need(r, "shape", where)
        if not isinstance(sh, list):
            raise _err(where, "shape must be a list")
        out["shape"] = [eval_dim_expr(e, dims or {}, where + ".shape") for e in sh]
    elif rule == "count":
        for k in ("equals", "min", "max"):
            if k in r and r[k] is not None:
                if isinstance(r[k], bool) or not isinstance(r[k], int):
                    raise _err(where, f"{k} must be an integer")
                out[k] = int(r[k])
        if not any(k in out for k in ("equals", "min", "max")):
            raise _err(where, "count needs equals, min or max")
    elif rule == "alphabet":
        vals = _need(r, "values", where)
        out["values"] = [_decimal_text(str(v) if not isinstance(v, str) else v, where + ".values") for v in vals]
    elif rule in EQUALITY_RULES:
        out["equals"] = _decimal_text(_need(r, "equals", where), where + ".equals")
        if r.get("tolerance") is None:
            raise _err(where, f"'{rule}' is an equality on real numbers: a 'tolerance' must be stated")
        if "axis" in r and r["axis"] is not None:
            out["axis"] = int(r["axis"])
    elif rule == "in_disk":
        out["radius"] = _decimal_text(_need(r, "radius", where), where + ".radius")
        c = r.get("center", ["0", "0"])
        out["center"] = [_decimal_text(str(v) if not isinstance(v, str) else v, where + ".center") for v in c]
    elif rule == "in_box":
        box = _need(r, "box", where)
        out["box"] = [[_decimal_text(str(v) if not isinstance(v, str) else v, where + ".box") for v in pair] for pair in box]
        if r.get("margin_from") is not None:
            if r["margin_from"] not in names:
                raise _err(where, f"unknown field {r['margin_from']!r}")
            out["margin_from"] = r["margin_from"]
    elif rule == "pairwise_separation":
        if r.get("radii_from") is None and r.get("min_distance") is None:
            raise _err(where, "needs radii_from or min_distance")
        if r.get("radii_from") is not None:
            if r["radii_from"] not in names:
                raise _err(where, f"unknown field {r['radii_from']!r}")
            out["radii_from"] = r["radii_from"]
        if r.get("min_distance") is not None:
            out["min_distance"] = _decimal_text(r["min_distance"], where + ".min_distance")
    elif rule in ("no_k_collinear", "no_k_coplanar"):
        k = r.get("k", 3 if rule == "no_k_collinear" else 4)
        if isinstance(k, bool) or not isinstance(k, int) or k < (3 if rule == "no_k_collinear" else 4):
            raise _err(where, "k too small")
        out["k"] = k
    elif rule == "graph_simple":
        if r.get("n_from") is not None:
            out["n_from"] = r["n_from"]
    elif rule == "predicate":
        out["call"] = str(_need(r, "call", where))
        out["name"] = str(r.get("name") or out["call"])
        out["equality"] = bool(r.get("equality", False))
        if out["equality"] and r.get("tolerance") is None:
            raise _err(where, "an equality predicate needs a stated 'tolerance'")
        glue_needed.add(("predicates", out["call"]))
    return out


def _norm_invariance(t: dict, names: dict, where: str) -> dict:
    if not isinstance(t, dict):
        raise _err(where, "must be a mapping")
    T = _need(t, "transform", where)
    if T not in TRANSFORMS:
        raise _err(where, f"transform must be one of {list(TRANSFORMS)}; got {T!r}")
    _only(t, {"transform", "field", "score_exponent", "dims", "order", "invariance_tolerance"}, where)
    f = _need(t, "field", where)
    if f not in names:
        raise _err(where, f"unknown field {f!r}")
    out = {"transform": T, "field": f}
    if T == "scale":
        se = _need(t, "score_exponent", where)
        if isinstance(se, bool) or not isinstance(se, (int, float)):
            raise _err(where, "score_exponent must be a number")
        out["score_exponent"] = se
    if T == "rotate":
        d = int(t.get("dims", 2))
        if d not in (2, 3):
            raise _err(where, "rotate dims must be 2 or 3")
        out["dims"] = d
    if T == "dihedral":
        o = t.get("order", 4)
        if isinstance(o, bool) or not isinstance(o, int) or o < 1:
            raise _err(where, "dihedral order must be a positive integer")
        out["order"] = o
    if t.get("invariance_tolerance") is not None:
        out["invariance_tolerance"] = _decimal_text(t["invariance_tolerance"], where + ".invariance_tolerance")
    return out


def _norm_score(s: dict, where: str, glue_needed: set) -> dict:
    if not isinstance(s, dict):
        raise _err(where, "must be a mapping")
    _only(s, {"direction", "record", "bound"}, where)
    d = _need(s, "direction", where)
    if d not in ("maximize", "minimize"):
        raise _err(where, f"direction must be maximize or minimize; got {d!r}")
    out = {"direction": d, "record": None, "bound": None}
    rec = s.get("record")
    if rec is not None:
        w = where + ".record"
        if not isinstance(rec, dict):
            raise _err(w, "must be a mapping")
        _only(rec, {"value", "kind", "source", "success", "margin", "quantity", "map"}, w)
        r = {"value": _decimal_text(_need(rec, "value", w), w + ".value"),
             "kind": rec.get("kind", "best_known"), "source": str(_need(rec, "source", w))}
        if r["kind"] not in RECORD_KINDS:
            raise _err(w, f"kind must be one of {list(RECORD_KINDS)}")
        if r["kind"] == "threshold":
            r["success"] = rec.get("success", ">")
            if r["success"] not in (">", ">="):
                raise _err(w, "success must be '>' or '>='")
            r["margin"] = _decimal_text(rec.get("margin", "0"), w + ".margin")
        elif "success" in rec or "margin" in rec:
            raise _err(w, "success/margin apply only to kind: threshold")
        if (rec.get("quantity") is None) != (rec.get("map") is None):
            raise _err(w, "quantity and map go together")
        if rec.get("map") is not None:
            r["quantity"] = str(rec["quantity"])
            r["map"] = str(rec["map"])
            glue_needed.add(("maps", r["map"]))
        out["record"] = r
    b = s.get("bound")
    if b is not None:
        w = where + ".bound"
        if not isinstance(b, dict):
            raise _err(w, "must be a mapping")
        _only(b, {"value", "kind", "source"}, w)
        if b.get("kind", "proven") != "proven":
            raise _err(w, "only proven bounds are accepted")
        out["bound"] = {"value": _decimal_text(_need(b, "value", w), w + ".value"), "kind": "proven",
                        "source": str(_need(b, "source", w))}
    return out


TOP = {"kind", "name", "harness", "dims", "fields", "returns", "validity", "caller_enforced",
       "invariances", "score", "noise", "reference", "initial", "claimed_best", "glue",
       "contract_author", "description"}


def contract_from_dict(data: dict, base: Union[str, Path] = ".", origin: str = "<dict>") -> Contract:
    if not isinstance(data, dict):
        raise ContractError(f"{origin}: a contract must be a mapping at the top level")
    _only(data, TOP, origin)
    if data.get("kind") != KIND:
        raise ContractError(f"{origin}: 'kind' must be {KIND!r} (got {data.get('kind')!r})")
    base = Path(base)
    dims = data.get("dims") or {}
    if not isinstance(dims, dict) or not all(isinstance(v, int) and not isinstance(v, bool) for v in dims.values()):
        raise ContractError(f"{origin}.dims: must map names to integers")
    glue_needed: set = set()
    harness = _norm_harness(_need(data, "harness", origin), origin + ".harness")
    fields = _norm_fields(_need(data, "fields", origin), dims, origin + ".fields")
    names = {f["name"]: f for f in fields}
    for f in fields:
        if f["role"] == "claimed":
            glue_needed.add(("quantities", f["quantity"]))
        if f["role"] == "derived" and f["from"].startswith("glue:"):
            glue_needed.add((None, f["from"][5:]))
    returns = data.get("returns") or [f["name"] for f in fields]
    if not isinstance(returns, list) or any(r not in names for r in returns):
        raise ContractError(f"{origin}.returns: must list field names (unknown: "
                            f"{[r for r in returns if r not in names] if isinstance(returns, list) else returns})")
    validity = [_norm_rule(r, names, f"{origin}.validity[{i}]", glue_needed, dims)
                for i, r in enumerate(data.get("validity") or [])]
    caller = [_norm_rule(r, names, f"{origin}.caller_enforced[{i}]", glue_needed, dims)
              for i, r in enumerate(data.get("caller_enforced") or [])]
    invs = [_norm_invariance(t, names, f"{origin}.invariances[{i}]") for i, t in enumerate(data.get("invariances") or [])]
    score = _norm_score(_need(data, "score", origin), origin + ".score", glue_needed)
    noise = data.get("noise") or {}
    if not isinstance(noise, dict):
        raise ContractError(f"{origin}.noise: must be a mapping")
    _only(noise, {"probe_repeats"}, origin + ".noise")
    pr = noise.get("probe_repeats", 3)
    if isinstance(pr, bool) or not isinstance(pr, int) or pr < 1:
        raise ContractError(f"{origin}.noise.probe_repeats: must be a positive integer")
    files = {}
    for key in ("reference", "initial", "claimed_best"):
        v = data.get(key)
        if v is None:
            if key == "reference":
                raise ContractError(f"{origin}: 'reference' is required (a known-valid candidate)")
            continue
        if not isinstance(v, dict) or set(v) != {"file"}:
            raise ContractError(f"{origin}.{key}: must be {{file: <path to .npz>}}")
        files[key] = {"file": str(v["file"])}
    if glue_needed and not data.get("glue"):
        raise ContractError(f"{origin}: glue functions are referenced ({sorted(n for _, n in glue_needed)}) "
                            "but no 'glue' file is given")
    author = data.get("contract_author", "human")
    if author not in ("human", "model"):
        raise ContractError(f"{origin}.contract_author: must be 'human' or 'model'")
    norm = {
        "kind": KIND, "name": str(_need(data, "name", origin)), "harness": harness, "dims": dict(dims),
        "fields": fields, "returns": list(returns), "validity": validity, "caller_enforced": caller,
        "invariances": invs, "score": score, "noise": {"probe_repeats": pr}, **files,
        "glue": data.get("glue"), "contract_author": author,
    }
    c = Contract(data=norm, base=base, hash=sha256_json(norm), origin=origin)
    # load glue, check it does not import the scorer, check every referenced glue function exists
    if norm["glue"]:
        gp = c.path(norm["glue"])
        mod, tree = load_glue(gp, origin + ".glue")
        ev_mod = Path(harness["evaluator"]).stem
        if ev_mod in glue_imports(tree):
            raise ContractError(f"{origin}.glue: the glue file imports the scorer module {ev_mod!r}; "
                                "glue must be independent of the scorer")
        c.glue = mod
        c.glue_hash = hashlib.sha256(gp.read_bytes()).hexdigest()
        for table, name in sorted(glue_needed, key=lambda t: (str(t[0]), t[1])):
            c.glue_fn(table, name)
    # hash every file the run reads
    for rel in [harness["evaluator"]] + [v["file"] for v in files.values()] + \
               ([norm["glue"]] if norm["glue"] else []) + \
               ([harness["program_template"]] if harness.get("program_template") else []):
        p = c.path(rel)
        if not p.is_file():
            raise ContractError(f"{origin}: file not found: {rel} (relative to {base})")
        c.file_hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return c


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _no_dups(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise ContractError(f"duplicate key {key!r} (line {key_node.start_mark.line + 1})")
        seen.add(key)
    return loader.construct_mapping(node, deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dups)


def load_contract(spec: Union[str, Path, dict, Contract], base: Union[str, Path, None] = None) -> Contract:
    """Load a contract from a YAML file, a dict (with `base` for relative paths) or pass one through."""
    if isinstance(spec, Contract):
        return spec
    if isinstance(spec, dict):
        return contract_from_dict(spec, base or ".", "<dict>")
    p = Path(spec)
    if not p.is_file():
        raise ContractError(f"contract not found: {p}")
    try:
        data = yaml.load(p.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise ContractError(f"{p}: not valid YAML: {exc}") from None
    return contract_from_dict(data, p.parent, str(p.name))
