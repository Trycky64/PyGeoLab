"""Finite immutable Euclidean values and robust scalar geometry algorithms.

Lines store unit normals, making distance tolerances independent of coefficient
scaling. Normal degeneracies return None from construction factories; malformed
values (NaN, infinity, negative radius) are rejected at the domain boundary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

EPSILON = 1e-9


def _finite(*values: float) -> None:
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Les coordonnées doivent être finies")


@dataclass(frozen=True, slots=True)
class Point2D:
    """A finite position in mathematical world coordinates."""

    x: float
    y: float

    def __post_init__(self) -> None:
        _finite(self.x, self.y)

    def distance_to(self, other: Point2D) -> float:
        """Euclidean distance, using hypot to reduce intermediate overflow."""
        return math.hypot(self.x - other.x, self.y - other.y)

    def almost_equals(self, other: Point2D, tolerance: float = EPSILON) -> bool:
        """Compare world-space distance with an explicit absolute tolerance."""
        return self.distance_to(other) <= tolerance


@dataclass(frozen=True, slots=True)
class Vector2D:
    """A finite displacement, independent of any origin."""

    x: float
    y: float

    def __post_init__(self) -> None:
        _finite(self.x, self.y)

    @classmethod
    def between(cls, start: Point2D, end: Point2D) -> Vector2D:
        """Construct the displacement from start to end."""
        return cls(end.x - start.x, end.y - start.y)

    @property
    def norm(self) -> float:
        """Length of the displacement in world units."""
        return math.hypot(self.x, self.y)

    def normalized(self) -> Vector2D | None:
        """Return a unit vector, or None when direction is undefined."""
        length = self.norm
        return None if length <= EPSILON else Vector2D(self.x / length, self.y / length)

    def dot(self, other: Vector2D) -> float:
        """Scalar product used for projections and angles."""
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vector2D) -> float:
        """Signed 2D determinant; positive means counterclockwise."""
        return self.x * other.y - self.y * other.x

    def rotated(self, radians: float) -> Vector2D:
        """Rotate counterclockwise by an angle in radians."""
        cosine, sine = math.cos(radians), math.sin(radians)
        return Vector2D(self.x * cosine - self.y * sine, self.x * sine + self.y * cosine)

    def __add__(self, other: Vector2D) -> Vector2D:
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2D) -> Vector2D:
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, factor: float) -> Vector2D:
        return Vector2D(self.x * factor, self.y * factor)


@dataclass(frozen=True, slots=True)
class Line2D:
    """An infinite line ax + by + c = 0, normalized to a unit normal."""

    a: float
    b: float
    c: float

    def __post_init__(self) -> None:
        _finite(self.a, self.b, self.c)
        length = math.hypot(self.a, self.b)
        if length == 0:
            raise ValueError("Une droite nécessite une normale non nulle")
        for key in ("a", "b", "c"):
            object.__setattr__(self, key, getattr(self, key) / length)
        _finite(self.a, self.b, self.c)

    @classmethod
    def from_points(cls, start: Point2D, end: Point2D) -> Line2D | None:
        """Return None for coincident points, whose line direction is undefined."""
        direction = Vector2D.between(start, end).normalized()
        if direction is None:
            return None
        a, b = -direction.y, direction.x
        return cls(a, b, -(a * start.x + b * start.y))

    @property
    def direction(self) -> Vector2D:
        """Unit tangent vector, perpendicular to the normal."""
        return Vector2D(-self.b, self.a)

    def signed_distance(self, point: Point2D) -> float:
        """Oriented distance measured along the unit normal."""
        return self.a * point.x + self.b * point.y + self.c

    def distance(self, point: Point2D) -> float:
        """Shortest distance from a point to the infinite line."""
        return abs(self.signed_distance(point))

    def project(self, point: Point2D) -> Point2D:
        """Orthogonal projection onto the line."""
        distance = self.signed_distance(point)
        return Point2D(point.x - self.a * distance, point.y - self.b * distance)

    def parallel(self, point: Point2D) -> Line2D:
        """Line through point with the same direction."""
        return Line2D(self.a, self.b, -self.a * point.x - self.b * point.y)

    def perpendicular(self, point: Point2D) -> Line2D:
        """Line through point perpendicular to this line."""
        return Line2D(-self.b, self.a, self.b * point.x - self.a * point.y)


@dataclass(frozen=True, slots=True)
class Segment2D:
    """A closed segment, including the valid zero-length case."""

    start: Point2D
    end: Point2D

    @property
    def length(self) -> float:
        """Distance between endpoints."""
        return self.start.distance_to(self.end)

    @property
    def bounding_box(self) -> tuple[float, float, float, float]:
        """Return left, bottom, right, top in world coordinates."""
        return (
            min(self.start.x, self.end.x),
            min(self.start.y, self.end.y),
            max(self.start.x, self.end.x),
            max(self.start.y, self.end.y),
        )

    def closest_point(self, point: Point2D) -> Point2D:
        """Project to the supporting line, clamping to the closed segment."""
        direction = Vector2D.between(self.start, self.end)
        length_squared = direction.dot(direction)
        if length_squared <= EPSILON**2:
            return self.start
        t = min(1.0, max(0.0, Vector2D.between(self.start, point).dot(direction) / length_squared))
        return Point2D(self.start.x + t * direction.x, self.start.y + t * direction.y)

    def contains(self, point: Point2D, tolerance: float = EPSILON) -> bool:
        """Include endpoints and a small absolute distance tolerance."""
        return self.closest_point(point).distance_to(point) <= tolerance


@dataclass(frozen=True, slots=True)
class Ray2D:
    """A half-line starting at start and passing through a distinct point."""

    start: Point2D
    through: Point2D

    @property
    def line(self) -> Line2D | None:
        """Supporting line, undefined when both defining points coincide."""
        return Line2D.from_points(self.start, self.through)

    def closest_point(self, point: Point2D) -> Point2D:
        """Project to the ray, clamping only behind its origin."""
        direction = Vector2D.between(self.start, self.through).normalized()
        if direction is None:
            return self.start
        t = max(0.0, Vector2D.between(self.start, point).dot(direction))
        return Point2D(self.start.x + t * direction.x, self.start.y + t * direction.y)

    def contains(self, point: Point2D, tolerance: float = EPSILON) -> bool:
        """Test distance to the half-line including its origin."""
        return self.closest_point(point).distance_to(point) <= tolerance


@dataclass(frozen=True, slots=True)
class Circle2D:
    """A finite circle with nonnegative radius; zero is a point-circle."""

    center: Point2D
    radius: float

    def __post_init__(self) -> None:
        _finite(self.radius)
        if self.radius < 0:
            raise ValueError("Le rayon doit être positif ou nul")


@dataclass(frozen=True, slots=True)
class Polygon2D:
    """An ordered closed polygon with at least three vertices.

    Signed area follows the winding order. Collinear polygons have no centroid;
    self-crossing polygons use the algebraic shoelace area and even-odd containment.
    """

    vertices: tuple[Point2D, ...]

    def __post_init__(self) -> None:
        if len(self.vertices) < 3:
            raise ValueError("Un polygone nécessite au moins trois sommets")

    @property
    def edges(self) -> tuple[Segment2D, ...]:
        """Closed boundary segments, including the final-to-first edge."""
        return tuple(
            Segment2D(a, b)
            for a, b in zip(self.vertices, self.vertices[1:] + self.vertices[:1], strict=True)
        )

    @property
    def signed_area(self) -> float:
        """Shoelace area relative to the first vertex to reduce cancellation."""
        origin = self.vertices[0]
        return (
            math.fsum(
                Vector2D.between(origin, edge.start).cross(Vector2D.between(origin, edge.end))
                for edge in self.edges
            )
            / 2
        )

    @property
    def area(self) -> float:
        """Absolute area in squared world units."""
        return abs(self.signed_area)

    @property
    def perimeter(self) -> float:
        """Sum of closed boundary lengths."""
        return math.fsum(edge.length for edge in self.edges)

    @property
    def orientation(self) -> int:
        """Return 1 counterclockwise, -1 clockwise, or 0 for negligible area."""
        area = self.signed_area
        return 0 if abs(area) <= EPSILON else (1 if area > 0 else -1)

    @property
    def centroid(self) -> Point2D | None:
        """Area-weighted centroid, undefined for negligible signed area."""
        area = self.signed_area
        if abs(area) <= EPSILON:
            return None
        origin = self.vertices[0]
        terms = [
            (Vector2D.between(origin, e.start), Vector2D.between(origin, e.end)) for e in self.edges
        ]
        return Point2D(
            origin.x + math.fsum((a.x + b.x) * a.cross(b) for a, b in terms) / (6 * area),
            origin.y + math.fsum((a.y + b.y) * a.cross(b) for a, b in terms) / (6 * area),
        )

    def contains(self, point: Point2D) -> bool:
        """Even-odd horizontal ray test, with boundary points included."""
        inside = False
        for edge in self.edges:
            if edge.contains(point):
                return True
            a, b = edge.start, edge.end
            if (a.y > point.y) != (b.y > point.y):
                crossing = a.x + (point.y - a.y) * (b.x - a.x) / (b.y - a.y)
                if point.x < crossing:
                    inside = not inside
        return inside
