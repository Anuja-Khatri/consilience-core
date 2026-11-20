"""Function minimisation example (README, config.yaml): minimise
f(x, y) = sin(x) cos(y) + sin(x y) + (x^2 + y^2) / 20 over the plane. The candidate's run_search()
returns (x, y, value); value is a self-report of f(x, y) (claimed)."""
import math


def f_value(c):
    x, y = float(c["x"]), float(c["y"])
    return math.sin(x) * math.cos(y) + math.sin(x * y) + (x * x + y * y) / 20.0


def compose(out, cand):
    """The evaluator returns an EvaluationResult object; its metrics dict is the scorer's output
    (an 'error' key marks a rejection). No change to any value."""
    return getattr(out, "metrics", out)


quantities = {"value": f_value}
