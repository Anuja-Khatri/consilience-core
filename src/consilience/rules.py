"""Rule files: comparison packs and data-check rules.

Both kinds are YAML files in one house format (the pattern of lab-gate's
``invariants.yaml``): a ``kind``, a ``name``, a ``version``, a plain-English line for the
file and for every rule, and optionally a rationale and a source. Loading checks every
field and refuses anything it does not know (a misspelt key is an error, not ignored).
The loaded file is normalised and hashed (SHA-256 over canonical JSON), so every result
names the exact rules it used.

    kind: compare-pack      which conditions must match before two measurements compare
    kind: check-rules       which columns of a table must respect which limits and bounds

The full format is in docs/RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from .hashing import sha256_json
from .units import UnitError, as_quantity, parse_unit

KINDS = ("compare-pack", "check-rules")
BUNDLED_PACKS = ("electrochemistry",)


class RuleFileError(ValueError):
    """A rule file that cannot be used. The message names the file and the problem."""


@dataclass(frozen=True)
class RuleSet:
    """A loaded, validated rule file and its hash."""

    kind: str
    name: str
    version: str
    content: dict      # the normalised rule file (what is hashed)
    sha256: str
    origin: str        # "bundled:<name>" or the path it was read from

    @property
    def rules(self) -> list:
        return self.content["conditions" if self.kind == "compare-pack" else "rules"]

    def describe(self) -> dict:
        return {"name": self.name, "version": self.version, "sha256": self.sha256}


# --------------------------------------------------------------------------- helpers
def _err(where: str, msg: str) -> RuleFileError:
    return RuleFileError(f"{where}: {msg}")


def _text(d: dict, key: str, where: str, required: bool = True) -> Optional[str]:
    v = d.get(key)
    if v is None:
        if required:
            raise _err(where, f"'{key}' is required")
        return None
    if not isinstance(v, str) or not v.strip():
        raise _err(where, f"'{key}' must be non-empty text")
    return " ".join(v.split())


def _only(d: dict, allowed: set, where: str) -> None:
    if not isinstance(d, dict):
        raise _err(where, "must be a mapping")
    extra = sorted(set(d) - allowed)
    if extra:
        raise _err(where, f"unknown key(s) {extra}; allowed: {sorted(allowed)}")


def _quantity_text(v, where: str, key: str, unit_required: bool, nonneg: bool = False):
    """Validate a quantity written in a rule file; return it as written (for hashing)."""
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        raise _err(where, f"'{key}' must be a number or a quantity like '0.05 V'")
    try:
        q = as_quantity(v)
    except UnitError as exc:
        raise _err(where, f"'{key}' cannot be read: {exc}") from None
    if unit_required and q.dimensionless and not (isinstance(v, (int, float)) and v == 0):
        raise _err(where, f"'{key}' needs a unit here, e.g. '0.05 V' (got {v!r})")
    if nonneg and q.magnitude < 0:
        raise _err(where, f"'{key}' must not be negative (got {v!r})")
    return v


def _bool(d: dict, key: str, where: str, default: bool) -> bool:
    v = d.get(key, default)
    if not isinstance(v, bool):
        raise _err(where, f"'{key}' must be true or false")
    return v


# --------------------------------------------------------------- compare packs
_PACK_TOP = {"kind", "name", "version", "plain_english", "rationale", "source", "licence",
             "conditions"}
_COND_KEYS = {"id", "field", "predicate", "plain_english", "rationale", "source",
              "ignore_case", "aliases", "tolerance", "words", "also_equal", "parts"}
_PART_KEYS = {"predicate", "ignore_case", "aliases", "tolerance", "words", "also_equal"}
PREDICATES = ("equal", "quantity_equal", "record")


def _predicate_params(d: dict, where: str, allow_record: bool) -> dict:
    pred = d.get("predicate")
    names = PREDICATES if allow_record else PREDICATES[:2]
    if pred not in names:
        raise _err(where, f"'predicate' must be one of {list(names)} (got {pred!r})")
    out: dict[str, Any] = {"predicate": pred}
    if pred == "equal":
        for k in ("tolerance", "words", "also_equal", "parts"):
            if k in d:
                raise _err(where, f"'{k}' does not apply to predicate 'equal'")
        ic = _bool(d, "ignore_case", where, False)
        aliases = d.get("aliases", {}) or {}
        if not isinstance(aliases, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in aliases.items()):
            raise _err(where, "'aliases' must map text to text")
        norm = {}
        for k, v in aliases.items():
            key = " ".join(k.split())
            key = key.casefold() if ic else key
            if key in norm and norm[key] != v:
                raise _err(where, f"alias {k!r} maps to two different names")
            norm[key] = " ".join(v.split())
        out.update(ignore_case=ic, aliases=dict(sorted(norm.items())))
    elif pred == "quantity_equal":
        for k in ("ignore_case", "aliases", "parts"):
            if k in d:
                raise _err(where, f"'{k}' does not apply to predicate 'quantity_equal'")
        out["tolerance"] = _quantity_text(d.get("tolerance", 0), where, "tolerance",
                                          unit_required=True, nonneg=True)
        words = d.get("words", []) or []
        also = d.get("also_equal", []) or []
        for k, lst in (("words", words), ("also_equal", also)):
            if not isinstance(lst, list) or not all(isinstance(x, str) and x for x in lst):
                raise _err(where, f"'{k}' must be a list of names")
        out.update(words=sorted(set(words)), also_equal=sorted(set(also)))
    else:  # record
        for k in ("ignore_case", "aliases", "tolerance", "words", "also_equal"):
            if k in d:
                raise _err(where, f"'{k}' belongs inside 'parts' for predicate 'record'")
        parts = d.get("parts")
        if not isinstance(parts, dict) or not parts:
            raise _err(where, "predicate 'record' needs 'parts': a mapping of part name to rule")
        norm_parts = {}
        for pname, pdef in parts.items():
            pw = f"{where}, part {pname!r}"
            if not isinstance(pname, str) or not pname:
                raise _err(where, "part names must be text")
            _only(pdef, _PART_KEYS, pw)
            norm_parts[pname] = _predicate_params(pdef, pw, allow_record=False)
        out["parts"] = dict(sorted(norm_parts.items()))
    return out


def _normalise_pack(data: dict, where: str) -> dict:
    _only(data, _PACK_TOP, where)
    out = {"kind": "compare-pack",
           "name": _text(data, "name", where),
           "version": _text(data, "version", where),
           "plain_english": _text(data, "plain_english", where),
           "rationale": _text(data, "rationale", where, required=False),
           "source": _text(data, "source", where, required=False),
           "licence": _text(data, "licence", where, required=False)}
    conds = data.get("conditions")
    if not isinstance(conds, list) or not conds:
        raise _err(where, "'conditions' must be a non-empty list")
    seen_ids, seen_fields, norm = set(), set(), []
    for i, c in enumerate(conds):
        cw = f"{where}, conditions[{i}]"
        _only(c, _COND_KEYS, cw)
        cid = _text(c, "id", cw)
        field = _text(c, "field", cw)
        if cid in seen_ids:
            raise _err(cw, f"duplicate id {cid!r}")
        if field in seen_fields:
            raise _err(cw, f"field {field!r} has two rules; use one rule per condition")
        seen_ids.add(cid)
        seen_fields.add(field)
        rule = {"id": cid, "field": field,
                "plain_english": _text(c, "plain_english", cw),
                "rationale": _text(c, "rationale", cw, required=False),
                "source": _text(c, "source", cw, required=False)}
        rule.update(_predicate_params(c, cw, allow_record=True))
        norm.append(rule)
    out["conditions"] = norm
    return out


# --------------------------------------------------------------- check rules
_CHECK_TOP = {"kind", "name", "version", "plain_english", "rationale", "source", "licence",
              "id_column", "columns", "rules"}
_COLUMN_KEYS = {"unit", "unit_column", "plain_english"}
_RULE_COMMON = {"id", "kind", "column", "plain_english", "rationale", "source", "if_empty"}
_BOUND_KEYS = _RULE_COMMON | {"min", "max", "min_inclusive", "max_inclusive"}
_LIMIT_KEYS = _RULE_COMMON | {"limit_column", "must_be", "margin", "value_offset",
                              "if_limit_empty"}


def _normalise_check(data: dict, where: str) -> dict:
    _only(data, _CHECK_TOP, where)
    out = {"kind": "check-rules",
           "name": _text(data, "name", where),
           "version": _text(data, "version", where),
           "plain_english": _text(data, "plain_english", where),
           "rationale": _text(data, "rationale", where, required=False),
           "source": _text(data, "source", where, required=False),
           "licence": _text(data, "licence", where, required=False),
           "id_column": _text(data, "id_column", where, required=False)}
    cols = data.get("columns")
    if not isinstance(cols, dict) or not cols:
        raise _err(where, "'columns' must map each checked column to its unit")
    ncols = {}
    for name, spec in cols.items():
        cw = f"{where}, column {name!r}"
        if not isinstance(name, str) or not name.strip():
            raise _err(where, "column names must be text")
        _only(spec, _COLUMN_KEYS, cw)
        has_u, has_uc = "unit" in spec, "unit_column" in spec
        if has_u == has_uc:
            raise _err(cw, "give exactly one of 'unit' (one unit for the whole column) or "
                           "'unit_column' (a column holding each row's unit)")
        entry = {"plain_english": _text(spec, "plain_english", cw, required=False)}
        if has_u:
            try:
                parse_unit(spec["unit"])
            except UnitError as exc:
                raise _err(cw, f"'unit' cannot be read: {exc}") from None
            entry["unit"] = spec["unit"].strip()
        else:
            entry["unit_column"] = _text(spec, "unit_column", cw)
        ncols[name.strip()] = entry
    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        raise _err(where, "'rules' must be a non-empty list")
    seen, nrules = set(), []
    for i, r in enumerate(rules):
        rw = f"{where}, rules[{i}]"
        if not isinstance(r, dict):
            raise _err(rw, "must be a mapping")
        kind = r.get("kind")
        if kind not in ("bound", "limit"):
            raise _err(rw, f"'kind' must be 'bound' or 'limit' (got {kind!r})")
        _only(r, _BOUND_KEYS if kind == "bound" else _LIMIT_KEYS, rw)
        rid = _text(r, "id", rw)
        if rid in seen:
            raise _err(rw, f"duplicate id {rid!r}")
        seen.add(rid)
        col = _text(r, "column", rw)
        if col not in ncols:
            raise _err(rw, f"column {col!r} is not declared under 'columns'")
        fixed_unit = "unit" in ncols[col]
        if_empty = r.get("if_empty", "refuse")
        if if_empty not in ("refuse", "skip"):
            raise _err(rw, "'if_empty' must be 'refuse' or 'skip'")
        nr = {"id": rid, "kind": kind, "column": col, "if_empty": if_empty,
              "plain_english": _text(r, "plain_english", rw),
              "rationale": _text(r, "rationale", rw, required=False),
              "source": _text(r, "source", rw, required=False)}
        if kind == "bound":
            if "min" not in r and "max" not in r:
                raise _err(rw, "a bound needs 'min', 'max' or both")
            for k in ("min", "max"):
                if k in r:
                    nr[k] = _quantity_text(r[k], rw, k, unit_required=not fixed_unit)
            nr["min_inclusive"] = _bool(r, "min_inclusive", rw, True)
            nr["max_inclusive"] = _bool(r, "max_inclusive", rw, True)
        else:
            lc = _text(r, "limit_column", rw)
            if lc not in ncols:
                raise _err(rw, f"limit column {lc!r} is not declared under 'columns'")
            must = r.get("must_be")
            if must not in ("at_most", "at_least"):
                raise _err(rw, "'must_be' must be 'at_most' (value <= limit + margin) or "
                               "'at_least' (value >= limit - margin)")
            nr.update(limit_column=lc, must_be=must,
                      margin=_quantity_text(r.get("margin", 0), rw, "margin",
                                            unit_required=not fixed_unit, nonneg=True),
                      value_offset=_quantity_text(r.get("value_offset", 0), rw,
                                                  "value_offset",
                                                  unit_required=not fixed_unit))
            ile = r.get("if_limit_empty", "refuse")
            if ile not in ("refuse", "skip"):
                ile = _quantity_text(ile, rw, "if_limit_empty",
                                     unit_required="unit" not in ncols[lc])
            nr["if_limit_empty"] = ile
        nrules.append(nr)
    out["columns"] = dict(sorted(ncols.items()))
    out["rules"] = nrules
    for nr in nrules:
        _check_dimensions(nr, ncols, f"{where}, rule {nr['id']}")
    for c in ncols.values():   # a unit column is read as text, never checked as a number
        if "unit_column" in c and c["unit_column"] in ncols:
            raise _err(where, f"unit column {c['unit_column']!r} is itself declared as a "
                              "number column")
    if out["id_column"] and out["id_column"] in ncols:
        raise _err(where, "'id_column' labels rows; it cannot also be a checked column")
    return out


def _check_dimensions(rule: dict, cols: dict, where: str) -> None:
    """For columns with a fixed unit, every number the rule uses must convert to it."""
    vcol = cols[rule["column"]]
    if "unit" not in vcol:
        return   # per-row units: checked row by row, refusals reported per cell
    vu = parse_unit(vcol["unit"])
    keys = ["min", "max"] if rule["kind"] == "bound" else ["margin", "value_offset"]
    for k in keys:
        if k in rule:
            q = as_quantity(rule[k])
            if not q.dimensionless or str(q.units) != "dimensionless":
                if q.dimensionality != (1 * vu).dimensionality:
                    raise _err(where, f"'{k}' {rule[k]!r} is not in the same kind of unit "
                                      f"as column {rule['column']!r} ({vcol['unit']})")
    if rule["kind"] == "limit":
        lcol = cols[rule["limit_column"]]
        if "unit" in lcol and (1 * parse_unit(lcol["unit"])).dimensionality != \
                (1 * vu).dimensionality:
            raise _err(where, f"limit column {rule['limit_column']!r} ({lcol['unit']}) is not "
                              f"in the same kind of unit as {rule['column']!r} "
                              f"({vcol['unit']})")
        fb = rule["if_limit_empty"]
        if fb not in ("refuse", "skip"):
            q = as_quantity(fb)
            if str(q.units) != "dimensionless" and q.dimensionality != \
                    (1 * vu).dimensionality:
                raise _err(where, f"'if_limit_empty' {fb!r} is not in the same kind of unit "
                                  f"as column {rule['column']!r}")


# ------------------------------------------------------------------ public API
def rules_from_dict(data: dict, origin: str = "<dict>") -> RuleSet:
    """Validate and hash a rule file given as a dict (e.g. one embedded in a receipt)."""
    if not isinstance(data, dict):
        raise RuleFileError(f"{origin}: a rule file must be a mapping at the top level")
    kind = data.get("kind")
    if kind == "compare-pack":
        content = _normalise_pack(data, origin)
    elif kind == "check-rules":
        content = _normalise_check(data, origin)
    else:
        raise RuleFileError(f"{origin}: 'kind' must be one of {list(KINDS)} (got {kind!r})")
    return RuleSet(kind=kind, name=content["name"], version=content["version"],
                   content=content, sha256=sha256_json(content), origin=origin)


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _no_duplicates(loader, node, deep=False):
    keys = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in keys:
            raise RuleFileError(f"duplicate key {key!r} (line {key_node.start_mark.line + 1})")
        keys.add(key)
    return loader.construct_mapping(node, deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def bundled_path(name: str):
    return resources.files("consilience").joinpath("data", "packs", f"{name}.yaml")


def _is_bundled_name(spec: str) -> bool:
    return "/" not in spec and "\\" not in spec and not spec.endswith((".yaml", ".yml"))


def load_rules(spec: Union[str, Path, RuleSet]) -> RuleSet:
    """Load a rule file: a path to a YAML file, or the name of a bundled pack.

    ``load_rules("electrochemistry")`` loads the bundled electrochemistry pack;
    ``load_rules("my_rules.yaml")`` loads a file. Raises ``RuleFileError``.
    """
    if isinstance(spec, RuleSet):
        return spec
    s = str(spec)
    if isinstance(spec, str) and _is_bundled_name(s):
        if s not in BUNDLED_PACKS:
            raise RuleFileError(f"no bundled pack named {s!r} (bundled: {list(BUNDLED_PACKS)}); "
                                "to load a file, give its path ending in .yaml")
        text, origin = bundled_path(s).read_text(encoding="utf-8"), f"bundled:{s}"
    else:
        p = Path(s)
        if not p.is_file():
            raise RuleFileError(f"rule file not found: {s}")
        text, origin = p.read_text(encoding="utf-8"), s
    try:
        data = yaml.load(text, Loader=_UniqueKeyLoader)
    except RuleFileError as exc:
        raise RuleFileError(f"{origin}: {exc}") from None
    except yaml.YAMLError as exc:
        raise RuleFileError(f"{origin}: not valid YAML: {exc}") from None
    return rules_from_dict(data, origin)


__all__ = ["RuleFileError", "RuleSet", "load_rules", "rules_from_dict", "BUNDLED_PACKS",
           "PREDICATES"]
