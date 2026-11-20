"""Glue for difference_bases (problem 7). Copied from pilot/dm_diffbases. Independent of the scorer."""


def to_scorer(c):
    return [[int(t) for t in c['B']]]


def compose(out, c):
    # get_score returns a bare float, except for a non-numeric element, where it returns (-inf, False)
    return out[0] if isinstance(out, tuple) else out
