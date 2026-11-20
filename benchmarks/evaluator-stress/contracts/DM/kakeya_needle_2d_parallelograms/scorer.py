# Vendored from https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8, experiments/kakeya_needle_2d/kakeya_needle_2d.ipynb, notebook code cells 2 (Apache-2.0).
# Scoring cells copied verbatim; only imports added
# get_all_triangle_vertices / get_all_parallelogram_vertices are kept for reference; the contract glue builds the polygons.
import numpy as np
import enum
import dataclasses
from typing import Any
from shapely import geometry  # code cell 0 installs shapely; the notebook never imports geometry explicitly


class ErrorMessage(enum.Enum):
  NO_ERROR = 0
  WRONG_OUTPUT_SHAPE = 1
  FUNCTION_IS_TOO_LARGE = 2
  ZERO_FUNCTION_SCORE = 3
  STOCHASTIC_FUNCTION = 4
  OTHER_ERROR = 5
  NO_POLYGON_SET = 6
  POINTS_NOT_FLOATS = 7


@dataclasses.dataclass(frozen=True)
class AreaEvaluationLog:
  area: float
  error_message: ErrorMessage


def get_all_triangle_vertices(x: np.ndarray) -> list[Any]:
  """Generates the list of triangle vertices for a triangle construction."""
  n = len(x)
  delta = 1 / n
  triangle_vertex_list = list()
  for i in range(1, n + 1):
    ai = i / n
    xi = x[i - 1]
    if not isinstance(xi, float):
      return AreaEvaluationLog(
          area=0.0,
          error_message=ErrorMessage.POINTS_NOT_FLOATS,
      )
    vertices = [
        (xi, 0),
        (xi + delta, 0),
        (xi + ai, 1),
    ]
    triangle_vertex_list.append(vertices)
  return triangle_vertex_list


def get_all_parallelogram_vertices(x: np.ndarray) -> list[Any]:
  """Generates the list of triangle vertices of a parallelogram construction."""
  n = len(x)
  delta = 1 / n
  triangle_vertex_list = []
  for i in range(1, n + 1):
    ai = i / n
    xi = x[i - 1]
    if not isinstance(xi, float):
      return AreaEvaluationLog(
          area=0.0,
          error_message=ErrorMessage.POINTS_NOT_FLOATS,
      )

    # For numerical stability, we create two triangles,
    # one for the lower part of the parallelogram and one for the upper part.
    vertices_lower_triangle = [
        (xi, 0),
        (xi + delta, 0),
        (xi + ai, 1),
    ]
    vertices_upper_triangle = [
        (xi + delta, 0),
        (xi + ai + delta, 1),
        (xi + ai, 1),
    ]
    triangle_vertex_list.append(vertices_lower_triangle)
    triangle_vertex_list.append(vertices_upper_triangle)
  return triangle_vertex_list


def get_score_shapely(triangles: list[Any]) -> AreaEvaluationLog:
  """Computes the area of a given configuration of triangles using shapely."""

  if not triangles:
    return -100000

  polygons = list()
  for triangle in triangles:
    polygons.append(geometry.Polygon(triangle))

  # Calculate the union of all triangles
  union_polygon = polygons[0]
  for i in range(1, len(polygons)):
    union_polygon = union_polygon.union(polygons[i])

  return union_polygon.area
