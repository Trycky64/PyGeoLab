"""Classify geometric intersections, including tangencies and bounded line domains.

Normal configurations without a unique answer are represented by an explicit
result kind. Collinear overlaps are coincident even when the overlap is bounded.
"""

from dataclasses import dataclass
from enum import Enum
from math import inf, isfinite, sqrt

from pygeolab.geometry.primitives import (
    EPSILON,
    Circle2D,
    Line2D,
    Point2D,
    Ray2D,
    Segment2D,
    Vector2D,
)

type Intersectable = Line2D | Segment2D | Ray2D | Circle2D
type LinearObject = Line2D | Segment2D | Ray2D


class IntersectionKind(Enum):
    """Distinguish empty, finite and infinitely many common points."""

    NONE = "none"
    ONE = "one"
    TWO = "two"
    COINCIDENT = "coincident"


@dataclass(frozen=True, slots=True)
class IntersectionResult:
    """Store isolated intersection points; coincident sets have no finite list."""

    kind: IntersectionKind
    points: tuple[Point2D, ...] = ()

    def __post_init__(self) -> None:
        expected = {IntersectionKind.ONE: 1, IntersectionKind.TWO: 2}.get(self.kind, 0)
        if len(self.points) != expected:
            raise ValueError("Intersection kind and point count disagree")


def line_line(first: Line2D, second: Line2D) -> IntersectionResult:
    """Solve normalized implicit equations and classify parallel supporting lines."""
    determinant = first.a * second.b - second.a * first.b
    if abs(determinant) <= EPSILON:
        anchor = Point2D(-second.a * second.c, -second.b * second.c)
        kind = (
            IntersectionKind.COINCIDENT
            if first.distance(anchor) <= EPSILON
            else IntersectionKind.NONE
        )
        return IntersectionResult(kind)
    point = Point2D(
        (first.b * second.c - second.b * first.c) / determinant,
        (first.c * second.a - second.c * first.a) / determinant,
    )
    return IntersectionResult(IntersectionKind.ONE, (point,))


def line_circle(line: Line2D, circle: Circle2D) -> IntersectionResult:
    """Use the center projection to avoid solving an ill-conditioned quadratic."""
    distance = line.distance(circle.center)
    tolerance = EPSILON * max(1.0, circle.radius)
    if distance > circle.radius + tolerance:
        return IntersectionResult(IntersectionKind.NONE)
    projection = line.project(circle.center)
    if abs(distance - circle.radius) <= tolerance:
        return IntersectionResult(IntersectionKind.ONE, (projection,))
    offset = sqrt(max(0.0, (circle.radius - distance) * (circle.radius + distance)))
    direction = line.direction
    points = (
        Point2D(projection.x - direction.x * offset, projection.y - direction.y * offset),
        Point2D(projection.x + direction.x * offset, projection.y + direction.y * offset),
    )
    return IntersectionResult(IntersectionKind.TWO, points)


def circle_circle(first: Circle2D, second: Circle2D) -> IntersectionResult:
    """Find intersections along the line of centers, including radius-zero loci."""
    displacement = Vector2D.between(first.center, second.center)
    distance = displacement.norm
    tolerance = EPSILON * max(1.0, first.radius, second.radius)
    if distance <= tolerance:
        if abs(first.radius - second.radius) > tolerance:
            return IntersectionResult(IntersectionKind.NONE)
        if max(first.radius, second.radius) <= EPSILON:
            return IntersectionResult(IntersectionKind.ONE, (first.center,))
        return IntersectionResult(IntersectionKind.COINCIDENT)
    if distance > first.radius + second.radius + tolerance:
        return IntersectionResult(IntersectionKind.NONE)
    if distance < abs(first.radius - second.radius) - tolerance:
        return IntersectionResult(IntersectionKind.NONE)
    along = (
        distance + (first.radius - second.radius) * ((first.radius + second.radius) / distance)
    ) / 2.0
    direction = Vector2D(displacement.x / distance, displacement.y / distance)
    base = Point2D(first.center.x + along * direction.x, first.center.y + along * direction.y)
    if (
        abs(distance - first.radius - second.radius) <= tolerance
        or abs(distance - abs(first.radius - second.radius)) <= tolerance
    ):
        return IntersectionResult(IntersectionKind.ONE, (base,))
    height = sqrt(max(0.0, (first.radius - along) * (first.radius + along)))
    points = (
        Point2D(base.x - direction.y * height, base.y + direction.x * height),
        Point2D(base.x + direction.y * height, base.y - direction.x * height),
    )
    return IntersectionResult(IntersectionKind.TWO, points)


def _supporting_line(value: LinearObject) -> Line2D | None:
    if isinstance(value, Line2D):
        return value
    end = value.end if isinstance(value, Segment2D) else value.through
    return Line2D.from_points(value.start, end)


def _contains(value: Intersectable, point: Point2D) -> bool:
    if isinstance(value, Circle2D):
        distance = Vector2D.between(value.center, point).norm
        return abs(distance - value.radius) <= EPSILON * max(1.0, value.radius)
    if isinstance(value, Line2D):
        return value.distance(point) <= EPSILON
    return value.contains(point)


def _interval(value: LinearObject, anchor: Point2D, direction: Vector2D) -> tuple[float, float]:
    if isinstance(value, Line2D):
        return -inf, inf
    start = Vector2D.between(anchor, value.start).dot(direction)
    end_point = value.end if isinstance(value, Segment2D) else value.through
    end = Vector2D.between(anchor, end_point).dot(direction)
    if isinstance(value, Segment2D):
        return min(start, end), max(start, end)
    return (start, inf) if end > start else (-inf, start)


def _collinear_overlap(
    first: LinearObject, second: LinearObject, line: Line2D
) -> IntersectionResult:
    anchor = Point2D(-line.a * line.c, -line.b * line.c)
    direction = line.direction
    first_low, first_high = _interval(first, anchor, direction)
    second_low, second_high = _interval(second, anchor, direction)
    low, high = max(first_low, second_low), min(first_high, second_high)
    if low > high + EPSILON:
        return IntersectionResult(IntersectionKind.NONE)
    if isfinite(low) and isfinite(high) and abs(high - low) <= EPSILON:
        along = low + (high - low) / 2.0
        point = Point2D(anchor.x + along * direction.x, anchor.y + along * direction.y)
        return IntersectionResult(IntersectionKind.ONE, (point,))
    return IntersectionResult(IntersectionKind.COINCIDENT)


def intersections(first: Intersectable, second: Intersectable) -> IntersectionResult:
    """Intersect loci and filter supporting-line answers by segment/ray bounds.

    Zero-length segments and rays are treated as point loci. A collinear shared
    endpoint is an isolated intersection; a nonzero overlap is coincident.
    """
    if isinstance(first, Circle2D):
        if isinstance(second, Circle2D):
            return circle_circle(first, second)
        return intersections(second, first)
    first_line = _supporting_line(first)
    if first_line is None:
        assert isinstance(first, (Segment2D, Ray2D))
        points: tuple[Point2D, ...] = (first.start,) if _contains(second, first.start) else ()
        return IntersectionResult(IntersectionKind.ONE if points else IntersectionKind.NONE, points)
    if isinstance(second, Circle2D):
        result = line_circle(first_line, second)
    else:
        second_line = _supporting_line(second)
        if second_line is None:
            return intersections(second, first)
        result = line_line(first_line, second_line)
        if result.kind is IntersectionKind.COINCIDENT:
            return _collinear_overlap(first, second, first_line)
    points = tuple(point for point in result.points if _contains(first, point))
    if not isinstance(second, Circle2D):
        points = tuple(point for point in points if _contains(second, point))
    kinds = (IntersectionKind.NONE, IntersectionKind.ONE, IntersectionKind.TWO)
    return IntersectionResult(kinds[len(points)], points)
