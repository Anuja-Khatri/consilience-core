"""Column maps: how a table's own column names become the fields ``compare-table`` reads.

A map is a small YAML file (``kind: column-map``). It only renames and translates; it
never computes or guesses a value:

    kind: column-map
    name: chembl
    version: chembl-v1
    plain_english: ChEMBL activity records (API JSON or SQL/CSV export)
    records: activities          # JSON input: the list of records is under this key
    key: [parent_molecule_chembl_id, target_chembl_id]   # default grouping (optional)
    id: activity_id              # a column that identifies each record (optional)
    value: standard_value        # the measured value
    relation: standard_relation  # optional: =, <, <=, >, >= (empty or absent: =)
    unit: standard_units         # the unit column (or fixed_unit: one unit for all records)
    uncertainty: null            # optional
    method: null                 # optional: listed per condition class (e.g. pKa method)
    fields:                      # output name: source column (dotted path into nested JSON)
      assay_type: assay_type
    units:                       # output name: the unit of its bare numbers
      temperature: degC
    lookups:                     # output name: {value as found: value to use}
      assay_variant_mutation: {"UNDEFINED MUTATION": unstated}
      unit: {"ug.mL-1": "ug/mL"}

Every column of the table is kept under its own name; ``fields`` adds renamed copies.
A lookup value of ``unstated`` marks the value as not stated (it is then never equal to
anything, not even another ``unstated``). Without a map, the table must already use the
names ``value`` and ``unit`` (and optionally ``relation``, ``uncertainty``, ``id``).
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Optional, Union

import yaml

from .hashing import sha256_json
from .rules import RuleFileError, _bool, _err, _only, _text, _UniqueKeyLoader  # noqa: F401

BUNDLED_MAPS = ("chembl", "iupac_pka")
_TOP = {"kind", "name", "version", "plain_english", "source", "records", "key", "id",
        "value", "relation", "unit", "fixed_unit", "uncertainty", "method", "fields", "lookups",
        "units"}
_ROLE_KEYS = ("id", "value", "relation", "unit", "uncertainty", "method")


@dataclass(frozen=True)
class ColumnMap:
    name: str
    version: str
    content: dict
    sha256: str
    origin: str

    def describe(self) -> dict:
        return {"name": self.name, "version": self.version, "sha256": self.sha256}

    def role(self, r: str) -> Optional[str]:
        return self.content.get(r)


IDENTITY = None   # no map: the table already uses the engine's names


def map_from_dict(data: dict, origin: str = "<dict>") -> ColumnMap:
    if not isinstance(data, dict):
        raise RuleFileError(f"{origin}: a column map must be a mapping")
    if data.get("kind") != "column-map":
        raise RuleFileError(f"{origin}: 'kind' must be 'column-map'")
    _only(data, _TOP, origin)
    out = {"kind": "column-map", "name": _text(data, "name", origin),
           "version": _text(data, "version", origin),
           "plain_english": _text(data, "plain_english", origin),
           "source": _text(data, "source", origin, required=False)}
    if data.get("records") is not None:
        out["records"] = _text(data, "records", origin)
    if data.get("key") is not None:
        k = data["key"]
        if not isinstance(k, list) or not k or not all(isinstance(x, str) and x for x in k):
            raise _err(origin, "'key' must be a list of field names (the default grouping)")
        out["key"] = list(k)
    out["value"] = _text(data, "value", origin)
    for r in ("id", "relation", "unit", "uncertainty", "method", "fixed_unit"):
        if data.get(r) is not None:
            out[r] = _text(data, r, origin)
    if "unit" in out and "fixed_unit" in out:
        raise _err(origin, "give either 'unit' (a column) or 'fixed_unit' (one unit for "
                           "every record), not both")
    fields = data.get("fields") or {}
    if not isinstance(fields, dict) or not all(
            isinstance(k, str) and k and isinstance(v, str) and v for k, v in fields.items()):
        raise _err(origin, "'fields' must map output names to source columns")
    reserved = {"value", "unit", "relation", "uncertainty", "id", "method"}
    clash = sorted(set(fields) & reserved)
    if clash:
        raise _err(origin, f"'fields' cannot define {clash}; use the top-level keys")
    out["fields"] = dict(sorted(fields.items()))
    lookups = data.get("lookups") or {}
    if not isinstance(lookups, dict):
        raise _err(origin, "'lookups' must map a field to a table of values")
    norm = {}
    for f, table in lookups.items():
        if not isinstance(table, dict) or not all(
                isinstance(k, str) and (v is None or isinstance(v, str)) for k, v in table.items()):
            raise _err(origin, f"lookup {f!r} must map text to text")
        norm[f] = dict(sorted(table.items()))
    out["lookups"] = dict(sorted(norm.items()))
    units = data.get("units") or {}
    if not isinstance(units, dict) or not all(
            isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in units.items()):
        raise _err(origin, "'units' must map a field to the unit its bare numbers are in")
    if units:
        out["units"] = dict(sorted(units.items()))
    return ColumnMap(name=out["name"], version=out["version"], content=out,
                     sha256=sha256_json(out), origin=origin)


def bundled_map_path(name: str):
    return resources.files("consilience").joinpath("data", "maps", f"{name}.yaml")


def load_map(spec: Union[str, Path, dict, ColumnMap, None]) -> Optional[ColumnMap]:
    """A bundled map name (``chembl``, ``iupac_pka``), a YAML path, a dict, or None."""
    if spec is None or isinstance(spec, ColumnMap):
        return spec
    if isinstance(spec, dict):
        return map_from_dict(spec)
    s = str(spec)
    if "/" not in s and "\\" not in s and not s.endswith((".yaml", ".yml")):
        if s not in BUNDLED_MAPS:
            raise RuleFileError(f"no bundled column map named {s!r} (bundled: "
                                f"{list(BUNDLED_MAPS)}); to load a file, give its path")
        text, origin = bundled_map_path(s).read_text(encoding="utf-8"), f"bundled:{s}"
    else:
        p = Path(s)
        if not p.is_file():
            raise RuleFileError(f"column map not found: {s}")
        text, origin = p.read_text(encoding="utf-8"), s
    try:
        data = yaml.load(text, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise RuleFileError(f"{origin}: not valid YAML: {exc}") from None
    return map_from_dict(data, origin)


def _get(row: dict, path: str):
    """A column, or a dotted path into nested JSON objects. (found, value)."""
    if path in row:
        return True, row[path]
    cur = row
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def apply_map(row: dict, cmap: Optional[ColumnMap]) -> tuple[dict, set]:
    """The record under the engine's names, and the set of output names whose source
    column exists in this row (so a column absent from the table can be told apart from
    an empty cell)."""
    if cmap is None:
        rec = dict(row)
        return rec, set(row)
    c = cmap.content
    rec = dict(row)
    present = set(row)
    for out, src in c["fields"].items():
        found, v = _get(row, src)
        if found:
            rec[out] = v
            present.add(out)
    for role in _ROLE_KEYS:
        src = c.get(role)
        if src is None:
            continue
        found, v = _get(row, src)
        if found:
            rec[role] = v
            present.add(role)
    if c.get("fixed_unit") is not None:
        rec["unit"] = c["fixed_unit"]
        present.add("unit")
    for f, table in c["lookups"].items():
        v = rec.get(f)
        if isinstance(v, str):
            key = " ".join(v.split())
            if key in table:
                rec[f] = table[key] if table[key] is not None else None
    for f, unit in c.get("units", {}).items():
        v = rec.get(f)
        text = getattr(v, "text", None) or (v if isinstance(v, str) else
                                            str(v) if isinstance(v, (int, float))
                                            and not isinstance(v, bool) else None)
        if text is not None and _is_bare_number(text):
            rec[f] = f"{text.strip()} {unit}"
    return rec, present


def _is_bare_number(text: str) -> bool:
    from .units import parse_number, UnitError
    try:
        parse_number(text.strip())
        return True
    except (UnitError, ValueError):
        return False


__all__ = ["ColumnMap", "BUNDLED_MAPS", "load_map", "map_from_dict", "apply_map"]
