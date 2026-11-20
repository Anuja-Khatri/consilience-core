# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 7b6a34b7b5b13d615dd55800e851080df5c3f92d, experiments/furstenberg_sarkozy/furstenberg_sarkozy.ipynb, notebook code cell 2 (0-based over code cells; function(s) check_sarkozy_subset) (Apache-2.0).
# Scoring cells copied verbatim; only imports added

from math import isfinite
def check_sarkozy_subset(m: int, subset: list[int], power: int = 2) -> bool:
    # Python integers are finite, including values too large for a float.
    if not all(isinstance(x, int) or isfinite(x) for x in subset):
        return False
    n = len(subset)
    powers = set(pow(x, power, m) for x in range(1, m))
    for i in range(n):
        for j in range(i+1, n):
            diff = (subset[i] - subset[j]) % m
            diff2 = (subset[j] - subset[i]) % m
            if diff in powers or diff2 in powers:
                return False
    return True
