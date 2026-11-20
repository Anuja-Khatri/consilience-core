# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/furstenberg_sarkozy/furstenberg_sarkozy.ipynb, notebook code cell 2 (0-based over code cells; function(s) check_sarkozy_subset) (Apache-2.0).
# Scoring cells copied verbatim; only imports added

def check_sarkozy_subset(m: int, subset: list[int], power: int = 2) -> bool:
    n = len(subset)
    powers = set(pow(x, power, m) for x in range(1, m))
    for i in range(n):
        for j in range(i+1, n):
            diff = (subset[i] - subset[j]) % m
            diff2 = (subset[j] - subset[i]) % m
            if diff in powers or diff2 in powers:
                return False
    return True
