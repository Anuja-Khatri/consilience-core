def to_scorer(c):
    return [[int(t) for t in c['B']]]
def compose(out, c):
    return out[0] if isinstance(out, tuple) else out
