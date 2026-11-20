# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/tammes_problem/tammes_problem.ipynb, notebook code cells 1 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
import numpy as np
import dataclasses
import enum
import scipy
import scipy.spatial


NEGATIVE_INFINITY = -1e10


class ErrorMessage(enum.Enum):
  NO_ERROR = 0
  WRONG_OUTPUT_SHAPE = 1
  FUNCTION_IS_TOO_LARGE = 2
  ZERO_FUNCTION_SCORE = 3
  STOCHASTIC_FUNCTION = 4
  OTHER_ERROR = 5
  NO_POLYGON_SET = 6
  POINTS_NOT_FLOATS = 7


@dataclasses.dataclass
class ConfigurationEvaluationLog:
  energy: float
  error_message: ErrorMessage


def get_energy(points: np.ndarray | list[float]) -> ConfigurationEvaluationLog:
  """Calculates the energy of the given configuration of points."""
  points_array = np.array(points)
  n = points_array.shape[0]
  if n <= 1:
    # No pairs to calculate energy for
    return ConfigurationEvaluationLog(
        energy=0.0,
        error_message=ErrorMessage.NO_POLYGON_SET,
    )

  points_array /= np.linalg.norm(points_array, axis=1)[..., None]

  pairwise_distances = scipy.spatial.distance.pdist(
      points_array, metric="euclidean"
  )

  if np.any(pairwise_distances < 1e-12):
    print(
        "Warning: Some points are coincident or extremely close. Potential"
        " energy approaches infinity."
    )
    pairwise_distances[pairwise_distances < 1e-12] = 1e-12

  total_energy = np.min(pairwise_distances)

  return ConfigurationEvaluationLog(
      energy=total_energy,
      error_message=ErrorMessage.NO_ERROR,
  )


def get_score(x: np.ndarray | list[float]) -> float:
  """Computes the area of a given configuration of triangles."""
  config_eval_log = get_energy(x)
  if config_eval_log.error_message != ErrorMessage.NO_ERROR:
    return NEGATIVE_INFINITY
  return config_eval_log.energy
