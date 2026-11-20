# Contract adapter, NOT vendored (written for this contract). The `template` harness calls entry(path_to_candidate_file);
# Google's evaluator takes the SDK envelope instead. This passes the generated file to the vendored, unmodified
# evaluate.circle_packing_evaluation exactly as the `sdk_dict` harness kind would: {"content": {"files": [{path, content}]}}.
import importlib.util
import os

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("g_circle_packing_evaluate", os.path.join(_here, "evaluate.py"))
_ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ev)


def evaluate_file(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return _ev.circle_packing_evaluation({"content": {"files": [{"path": os.path.basename(path), "content": text}]}})
