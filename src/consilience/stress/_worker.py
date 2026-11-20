"""Worker process for in-process harness kinds (function, py_path, sdk_dict, template).

Started by `harness.Harness`. Imports the scorer (and glue) once, then answers JSON-line requests on
a private copy of stdout; the scorer's own prints go to stderr. Each request names a candidate .npz
written by the parent; the reply is the raw output (a number, a dict, or an error description).
Not a sandbox: it runs the scorer's code with the caller's permissions.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import traceback
import uuid


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _jsonable(o):
    import numpy as np
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.generic):
        o = o.item()
    if isinstance(o, np.ndarray):
        return {"$ndarray_shape": list(o.shape)}
    if isinstance(o, float) and not math.isfinite(o):
        return {"$float": "nan" if math.isnan(o) else ("inf" if o > 0 else "-inf")}
    if isinstance(o, (bool, int, float, str)) or o is None:
        return o
    return {"$repr": repr(o)[:200]}


def _program_text(cfg, npz):
    """A candidate program whose function returns the construction exactly, loaded from the npz."""
    ret = []
    for name, typ in cfg["returns"]:
        if typ == "real":
            ret.append(f"float(_d[{name!r}])")
        elif typ == "int":
            ret.append(f"int(_d[{name!r}])")
        else:
            ret.append(f"_d[{name!r}]")
    expr = ret[0] if len(ret) == 1 else "(" + ", ".join(ret) + ")"
    body = (f"def {cfg['program_function']}(*args, **kwargs):\n"
            f"    import numpy as _np\n"
            f"    _d = _np.load({npz!r}, allow_pickle=False)\n"
            f"    return {expr}\n")
    if cfg["kind"] == "template":
        with open(cfg["program_template"], encoding="utf-8") as fh:
            tpl = fh.read()
        a, b = cfg["block_start"], cfg["block_end"]
        i, j = tpl.find(a), tpl.find(b)
        if i < 0 or j < 0 or j < i:
            raise ValueError("template markers not found in program_template")
        return tpl[: i + len(a)] + "\n" + body + tpl[j:]
    return body


def main():
    cfg = json.loads(sys.argv[1])
    proto = os.fdopen(os.dup(1), "w", buffering=1)
    os.dup2(2, 1)                                 # scorer prints go to stderr, never into the protocol
    sys.stdout = sys.stderr
    ev_dir = os.path.dirname(cfg["evaluator"])
    sys.path.insert(0, ev_dir)
    os.chdir(ev_dir)
    try:
        ev = _load(cfg["evaluator"], "consilience_scorer_" + uuid.uuid4().hex[:8])
        glue = _load(cfg["glue"], "consilience_glue_w_" + uuid.uuid4().hex[:8]) if cfg.get("glue") else None
        entry = getattr(ev, cfg["entry"])
    except BaseException:
        proto.write(json.dumps({"ready": False, "error": traceback.format_exc()[-2000:]}) + "\n")
        return 1
    proto.write(json.dumps({"ready": True}) + "\n")
    import numpy as np
    for line in sys.stdin:
        req = json.loads(line)
        if req.get("op") == "quit":
            break
        try:
            d = np.load(req["npz"], allow_pickle=False)
            cand = {k: d[k] for k in d.files}
            if cfg["kind"] == "function":
                if glue is not None and hasattr(glue, "to_scorer"):
                    args = glue.to_scorer(cand)
                else:
                    args = []
                    for name, typ in cfg["returns"]:
                        v = cand[name]
                        args.append(float(v) if typ == "real" else int(v) if typ == "int" else v)
                out = entry(*args, **cfg.get("call_args", {}))
            else:
                prog = os.path.join(req["dir"], "cand_" + uuid.uuid4().hex[:12] + ".py")
                text = _program_text(cfg, req["npz"])
                with open(prog, "w", encoding="utf-8") as fh:
                    fh.write(text)
                if cfg["kind"] == "sdk_dict":
                    out = entry({"content": {"files": [{"path": os.path.basename(prog), "content": text}]}})
                else:
                    out = entry(prog)
                try:
                    os.remove(prog)
                except OSError:
                    pass
            if glue is not None and hasattr(glue, "compose"):
                out = glue.compose(out, cand)
            proto.write(json.dumps({"ok": True, "out": _jsonable(out)}) + "\n")
        except BaseException as exc:  # the scorer raising is information, not a crash of the tool
            proto.write(json.dumps({"ok": False, "exc": type(exc).__name__, "msg": str(exc)[:300]}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
