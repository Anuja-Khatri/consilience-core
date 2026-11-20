"""Glue for the_2d_moving_sofa. Construction = path rows (x, y, angle_degrees) of the corridor's inner
corner between the fixed endpoints [0, 0, 0] and [-2, 0, 90] that the scorer adds.

The scorer's entry takes a Corridor object, which glue cannot obtain from the scorer module (glue must
not import it). The class below is therefore a verbatim copy of class Corridor from
https://github.com/google-deepmind/alphaevolve_repository_of_problems @ 8f447457957deac61e28bf1676746f0753b3b2f8,
experiments/the_2d_moving_sofa/the_2d_moving_sofa.ipynb, code cell 1 (Apache-2.0); imports added."""
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import transform


class Corridor:

  def __init__(self):
    """Initializes the corridor.

    Args:
        turns: A list of tuples, where each tuple represents a turn:
          (distance_before_turn, turn_angle_degrees) The first segment starts at
          (0, 0) and extends along the x-axis.
    """
    self.width = 1

  def get_corridor_shape(self, angle_degrees, inner_corner_path):
    """Calculates the polygon representing the corridor at a given angle and inner corner position.

    Args:
        angle_degrees: The current rotation angle of the corridor.
        inner_corner_path: A point (x, y) representing the inner corner.

    Returns:
        A shapely Polygon object representing the corridor.
    """
    angle_radians = np.deg2rad(angle_degrees)
    x_inner, y_inner = inner_corner_path

    big_const = 3

    points = [
        (0, 0),
        (0, -big_const * self.width),
        (self.width, -big_const * self.width),
        (self.width, self.width),
        (-big_const * self.width, self.width),
        (-big_const * self.width, 0),
    ]
    corridor_polygon = Polygon(points)

    # Rotate the corridor
    rotated_polygon = transform(
        lambda x, y: (
            x * np.cos(angle_radians) - y * np.sin(angle_radians),
            x * np.sin(angle_radians) + y * np.cos(angle_radians),
        ),
        corridor_polygon,
    )

    # Translate the corridor so its inner corner is at inner_corner_path
    translated_polygon = transform(
        lambda x, y: (x + x_inner, y + y_inner), rotated_polygon
    )

    return translated_polygon


def to_scorer(c):
    return [Corridor(), [[float(v) for v in row] for row in np.asarray(c['path'], dtype=float)]]


def compose(out, c):
    return float(out[0]) if isinstance(out, (tuple, list)) else out


def _angles_ok(c):
    P = np.asarray(c['path'], dtype=float)
    if P.ndim != 2 or P.shape[1] != 3:
        return (False, float('inf'))
    a = P[:, 2]
    worst = float(max(0.0, -a.min(), a.max() - 90.0))
    return (worst == 0.0, worst)


predicates = {"angles_in_quarter_turn": _angles_ok}
