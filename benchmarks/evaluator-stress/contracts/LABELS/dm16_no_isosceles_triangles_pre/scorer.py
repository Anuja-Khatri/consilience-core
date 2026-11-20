# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/subsets_of_the_grid_with_no_isosceles_triangles/subsets_of_the_grid_with_no_isosceles_triangles.ipynb, notebook code cell 0 (0-based over code cells; function(s) dist_sq, verify_construction) (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import itertools
from math import sqrt
import numpy as np

def dist_sq(p1, p2):
    """Calculates the squared Euclidean distance between two points."""
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2


def verify_construction(points):
    """
    Verifies that for any three distinct points (a, b, c), the distance
    from a to b is not equal to the distance from b to c. This checks for
    both standard and degenerate/flat isosceles triangles.

    Args:
        points (list): A list of (x, y) tuples.

    Returns:
        bool: True if the construction is valid, False otherwise.
    """
    print("Starting verification... (this may take a moment)")
    # Generate all ordered permutations of 3 points from the list
    for a, b, c in itertools.permutations(points, 3):
        # Check if the distance from a to b is the same as b to c.
        if dist_sq(a, b) == dist_sq(b, c):
            d = sqrt(dist_sq(a,b))
            print(f"Verification FAILED: Found a forbidden isosceles configuration.")
            print(f"Points: a={a}, b={b}, c={c}")
            print(f"dist(a,b) = dist(b,c) = {d:.2f}")
            return False

    # If the loop completes, no such configuration was found
    return True
