# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/thomson_problem/thomson_problem.ipynb, notebook code cells 2 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
import scipy
import scipy.spatial


def get_score(points):
  """Calculates the score of the given points."""
  points_array = np.array(points)
  n = points_array.shape[0]
  if n <= 1:
    return 0.0  # No pairs to calculate energy for

  points_array /= np.linalg.norm(points_array, axis=1)[..., None]

  pairwise_distances = scipy.spatial.distance.pdist(
      points_array, metric='euclidean'
  )

  if np.any(pairwise_distances < 1e-12):
    print(
        'Warning: Some points are coincident or extremely close. Potential'
        ' energy approaches infinity.'
    )
    pairwise_distances[pairwise_distances < 1e-12] = 1e-12

  inverse_distances = 1.0 / pairwise_distances
  total_energy = np.sum(inverse_distances)

  return -total_energy
