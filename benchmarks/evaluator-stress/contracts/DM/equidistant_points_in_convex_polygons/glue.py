def to_scorer(c):
    return [[tuple(map(float, p)) for p in c['P']], 15]
