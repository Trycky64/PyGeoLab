"""Pure point transformations and Euclidean constructions in world coordinates."""

from math import acos, isfinite

from pygeolab.geometry.primitives import EPSILON, Circle2D, Line2D, Point2D, Vector2D


def midpoint(first: Point2D, second: Point2D) -> Point2D:
    """Return the arithmetic midpoint without constructing a supporting line."""
    return Point2D(first.x / 2.0 + second.x / 2.0, first.y / 2.0 + second.y / 2.0)


def translate(point: Point2D, displacement: Vector2D) -> Point2D:
    """Move a point by a world-space vector."""
    return Point2D(point.x + displacement.x, point.y + displacement.y)


def rotate(point: Point2D, radians: float, center: Point2D | None = None) -> Point2D:
    """Rotate counterclockwise about a center; angles use radians."""
    if not isfinite(radians):
        raise ValueError("Rotation angle must be finite")
    center = center if center is not None else Point2D(0.0, 0.0)
    return translate(center, Vector2D.between(center, point).rotated(radians))


def scale(point: Point2D, factor: float, center: Point2D | None = None) -> Point2D:
    """Apply a homothety; zero collapses to the center and negative values reflect."""
    if not isfinite(factor):
        raise ValueError("Scale factor must be finite")
    center = center if center is not None else Point2D(0.0, 0.0)
    return translate(center, Vector2D.between(center, point) * factor)


def reflect_point(point: Point2D, center: Point2D) -> Point2D:
    """Reflect through a center, preserving its midpoint with the source."""
    return scale(point, -1.0, center)


def reflect_line(point: Point2D, line: Line2D) -> Point2D:
    """Reflect across the orthogonal projection onto an implicit line."""
    return reflect_point(point, line.project(point))


def perpendicular_bisector(first: Point2D, second: Point2D) -> Line2D | None:
    """Construct the equidistance locus, or return None for coincident inputs."""
    line = Line2D.from_points(first, second)
    return None if line is None else line.perpendicular(midpoint(first, second))


def angle_bisector(first: Point2D, vertex: Point2D, second: Point2D) -> Line2D | None:
    """Bisect the smaller angle; a straight angle uses its perpendicular bisector.

    Coincident arms have no defined direction and return None. For opposing
    arms the unique bisector line is perpendicular to either arm.
    """
    left = Vector2D.between(vertex, first).normalized()
    right = Vector2D.between(vertex, second).normalized()
    if left is None or right is None:
        return None
    direction = left + right
    if direction.norm <= EPSILON:
        direction = Vector2D(-left.y, left.x)
    return Line2D.from_points(vertex, translate(vertex, direction))


def circumcircle(first: Point2D, second: Point2D, third: Point2D) -> Circle2D | None:
    """Use relative coordinates to avoid cancellation from large world offsets."""
    left = Vector2D.between(first, second)
    right = Vector2D.between(first, third)
    product = left.norm * right.norm
    determinant = 2.0 * left.cross(right)
    if product <= EPSILON * EPSILON or abs(determinant) <= 2.0 * EPSILON * product:
        return None
    left_squared = left.dot(left)
    right_squared = right.dot(right)
    offset = Vector2D(
        (right.y * left_squared - left.y * right_squared) / determinant,
        (left.x * right_squared - right.x * left_squared) / determinant,
    )
    return Circle2D(translate(first, offset), offset.norm)


def angle(first: Point2D, vertex: Point2D, second: Point2D) -> float | None:
    """Return the unsigned angle in [0, pi], or None for a zero-length arm."""
    left = Vector2D.between(vertex, first).normalized()
    right = Vector2D.between(vertex, second).normalized()
    if left is None or right is None:
        return None
    return acos(max(-1.0, min(1.0, left.dot(right))))
