# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/no_5_on_a_sphere/no_5_on_a_sphere.ipynb, notebook code cells 0 (0-based, counting code cells only), functions verify_3d_construction (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import itertools
import numpy as np

def verify_3d_construction(points):
    """
    Verifies that no five points in the set are co-spherical or co-planar.
    """
    print("Starting verification...")
    # To check a new point, we only need to check combinations of 4 existing points plus the new one.
    # This is much faster than re-checking the whole set every time.
    for five_points in itertools.combinations(points, 5):
        matrix = np.zeros((5, 5), dtype=np.float64)
        for i, p in enumerate(five_points):
            matrix[i, 0] = p[0]
            matrix[i, 1] = p[1]
            matrix[i, 2] = p[2]
            matrix[i, 3] = p[0]**2 + p[1]**2 + p[2]**2
            matrix[i, 4] = 1
        det = np.linalg.det(matrix)
        if np.isclose(det, 0):
            print(f"Verification FAILED: Found 5 co-spherical/co-planar points: {five_points}")
            return False
    return True
