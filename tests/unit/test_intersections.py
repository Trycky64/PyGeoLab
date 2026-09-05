"""Verify intersection classifications, coordinates, bounds, and degenerate inputs."""

from math import sqrt

import pytest

from pygeolab.geometry.intersections import (
    IntersectionKind,
    IntersectionResult,
    circle_circle,
    intersections,
    line_circle,
    line_line,
)
from pygeolab.geometry.primitives import Circle2D, Line2D, Point2D, Ray2D, Segment2D

type Intersectable = Line2D | Segment2D | Ray2D | Circle2D


def _assert_result(
    result: IntersectionResult,
    kind: IntersectionKind,
    expected: tuple[tuple[float, float], ...] = (),
) -> None:
    """Compare unordered geometric solutions using an absolute numeric tolerance."""
    assert result.kind is kind
    assert isinstance(result.points, tuple)
    assert len(result.points) == len(expected)
    actual = sorted((point.x, point.y) for point in result.points)
    for coordinates, target in zip(actual, sorted(expected), strict=True):
        assert coordinates == pytest.approx(target, rel=1e-12, abs=1e-8)


@pytest.mark.parametrize(
    ("first", "second", "kind", "expected"),
    [
        (Line2D(1, 0, -2), Line2D(0, 1, -3), IntersectionKind.ONE, ((2, 3),)),
        (Line2D(1, -1, 0), Line2D(1, 1, -4), IntersectionKind.ONE, ((2, 2),)),
        (Line2D(1, 2, -3), Line2D(2, 4, -7), IntersectionKind.NONE, ()),
        (Line2D(1, 2, -3), Line2D(-2, -4, 6), IntersectionKind.COINCIDENT, ()),
        (
            Line2D(1, 0, -1_000_000),
            Line2D(0, 1, 2_000_000),
            IntersectionKind.ONE,
            ((1_000_000, -2_000_000),),
        ),
    ],
    ids=["axis-aligned", "oblique", "parallel", "coincident", "large-offset"],
)
def test_line_line_classifies_and_locates_intersections(
    first: Line2D,
    second: Line2D,
    kind: IntersectionKind,
    expected: tuple[tuple[float, float], ...],
) -> None:
    """Line solutions do not depend on argument order or coefficient orientation."""
    _assert_result(line_line(first, second), kind, expected)
    _assert_result(line_line(second, first), kind, expected)


@pytest.mark.parametrize(
    ("line", "circle", "kind", "expected"),
    [
        (Line2D(0, 1, -3), Circle2D(Point2D(0, 0), 2), IntersectionKind.NONE, ()),
        (Line2D(0, 1, -2), Circle2D(Point2D(0, 0), 2), IntersectionKind.ONE, ((0, 2),)),
        (
            Line2D(0, 1, 0),
            Circle2D(Point2D(0, 0), 2),
            IntersectionKind.TWO,
            ((-2, 0), (2, 0)),
        ),
        (
            Line2D(1, 0, -3),
            Circle2D(Point2D(2, 4), sqrt(2)),
            IntersectionKind.TWO,
            ((3, 3), (3, 5)),
        ),
        (Line2D(0, 1, -4), Circle2D(Point2D(2, 4), 0), IntersectionKind.ONE, ((2, 4),)),
        (Line2D(0, 1, -5), Circle2D(Point2D(2, 4), 0), IntersectionKind.NONE, ()),
    ],
    ids=["separate", "tangent", "secant", "translated", "point-on-line", "point-off-line"],
)
def test_line_circle_classifies_and_locates_intersections(
    line: Line2D,
    circle: Circle2D,
    kind: IntersectionKind,
    expected: tuple[tuple[float, float], ...],
) -> None:
    """Line-circle intersections include translated circles and zero-radius circles."""
    _assert_result(line_circle(line, circle), kind, expected)


@pytest.mark.parametrize("offset", [-1e-10, 0.0, 1e-10])
def test_line_circle_tangency_tolerates_roundoff(offset: float) -> None:
    """A distance difference below the base tolerance remains a single tangency."""
    result = line_circle(Line2D(0, 1, -(1 + offset)), Circle2D(Point2D(0, 0), 1))

    _assert_result(result, IntersectionKind.ONE, ((0, 1),))


@pytest.mark.parametrize(
    ("first", "second", "kind", "expected"),
    [
        (
            Circle2D(Point2D(0, 0), 1),
            Circle2D(Point2D(3, 0), 1),
            IntersectionKind.NONE,
            (),
        ),
        (
            Circle2D(Point2D(0, 0), 1),
            Circle2D(Point2D(2, 0), 1),
            IntersectionKind.ONE,
            ((1, 0),),
        ),
        (
            Circle2D(Point2D(0, 0), 2),
            Circle2D(Point2D(2, 0), 2),
            IntersectionKind.TWO,
            ((1, -sqrt(3)), (1, sqrt(3))),
        ),
        (
            Circle2D(Point2D(0, 0), 3),
            Circle2D(Point2D(2, 0), 1),
            IntersectionKind.ONE,
            ((3, 0),),
        ),
        (
            Circle2D(Point2D(0, 0), 3),
            Circle2D(Point2D(1, 0), 1),
            IntersectionKind.NONE,
            (),
        ),
        (
            Circle2D(Point2D(2, -1), 3),
            Circle2D(Point2D(2, -1), 3),
            IntersectionKind.COINCIDENT,
            (),
        ),
        (
            Circle2D(Point2D(2, -1), 3),
            Circle2D(Point2D(2, -1), 1),
            IntersectionKind.NONE,
            (),
        ),
        (
            Circle2D(Point2D(2, -1), 0),
            Circle2D(Point2D(2, -1), 0),
            IntersectionKind.ONE,
            ((2, -1),),
        ),
        (
            Circle2D(Point2D(2, 0), 0),
            Circle2D(Point2D(0, 0), 2),
            IntersectionKind.ONE,
            ((2, 0),),
        ),
        (
            Circle2D(Point2D(0, 0), 0),
            Circle2D(Point2D(1, 0), 0),
            IntersectionKind.NONE,
            (),
        ),
    ],
    ids=[
        "separate",
        "external-tangent",
        "two",
        "internal-tangent",
        "contained",
        "coincident",
        "concentric",
        "identical-points",
        "point-on-circle",
        "distinct-points",
    ],
)
def test_circle_circle_classifies_and_locates_intersections(
    first: Circle2D,
    second: Circle2D,
    kind: IntersectionKind,
    expected: tuple[tuple[float, float], ...],
) -> None:
    """Circle intersections distinguish nesting, coincidence, tangency, and point circles."""
    _assert_result(circle_circle(first, second), kind, expected)
    _assert_result(circle_circle(second, first), kind, expected)


@pytest.mark.parametrize("offset", [-1e-10, 0.0, 1e-10])
def test_circle_circle_tangency_tolerates_roundoff(offset: float) -> None:
    """External tangencies remain stable when centers differ by sub-tolerance noise."""
    result = circle_circle(Circle2D(Point2D(0, 0), 1), Circle2D(Point2D(2 + offset, 0), 1))

    _assert_result(result, IntersectionKind.ONE, ((1, 0),))


@pytest.mark.parametrize(
    ("first", "second", "kind", "expected"),
    [
        (
            Segment2D(Point2D(-1, 0), Point2D(1, 0)),
            Line2D(1, 0, 0),
            IntersectionKind.ONE,
            ((0, 0),),
        ),
        (
            Segment2D(Point2D(-1, 0), Point2D(1, 0)),
            Line2D(1, 0, -2),
            IntersectionKind.NONE,
            (),
        ),
        (
            Segment2D(Point2D(0, 0), Point2D(1, 0)),
            Segment2D(Point2D(1, 0), Point2D(1, 1)),
            IntersectionKind.ONE,
            ((1, 0),),
        ),
        (
            Segment2D(Point2D(0, 0), Point2D(1, 0)),
            Segment2D(Point2D(2, -1), Point2D(2, 1)),
            IntersectionKind.NONE,
            (),
        ),
        (
            Segment2D(Point2D(-3, 0), Point2D(0, 0)),
            Circle2D(Point2D(0, 0), 2),
            IntersectionKind.ONE,
            ((-2, 0),),
        ),
        (
            Segment2D(Point2D(-1, 0), Point2D(1, 0)),
            Circle2D(Point2D(0, 0), 2),
            IntersectionKind.NONE,
            (),
        ),
        (
            Segment2D(Point2D(-2, 0), Point2D(2, 0)),
            Circle2D(Point2D(0, 0), 2),
            IntersectionKind.TWO,
            ((-2, 0), (2, 0)),
        ),
        (
            Ray2D(Point2D(0, 0), Point2D(1, 0)),
            Line2D(1, 0, -2),
            IntersectionKind.ONE,
            ((2, 0),),
        ),
        (
            Ray2D(Point2D(0, 0), Point2D(1, 0)),
            Line2D(1, 0, 2),
            IntersectionKind.NONE,
            (),
        ),
        (
            Ray2D(Point2D(0, 0), Point2D(1, 0)),
            Circle2D(Point2D(0, 0), 2),
            IntersectionKind.ONE,
            ((2, 0),),
        ),
        (
            Ray2D(Point2D(-3, 0), Point2D(-2, 0)),
            Circle2D(Point2D(0, 0), 2),
            IntersectionKind.TWO,
            ((-2, 0), (2, 0)),
        ),
        (
            Ray2D(Point2D(0, 0), Point2D(1, 0)),
            Ray2D(Point2D(0, 0), Point2D(0, 1)),
            IntersectionKind.ONE,
            ((0, 0),),
        ),
    ],
    ids=[
        "segment-crossing-line",
        "segment-missing-line",
        "segments-share-endpoint",
        "segments-miss",
        "segment-one-circle-root",
        "segment-inside-circle",
        "segment-circle-endpoints",
        "ray-crossing-line",
        "ray-missing-line",
        "ray-one-circle-root",
        "ray-two-circle-roots",
        "rays-share-origin",
    ],
)
def test_dispatch_filters_intersections_to_segment_and_ray_bounds(
    first: Intersectable,
    second: Intersectable,
    kind: IntersectionKind,
    expected: tuple[tuple[float, float], ...],
) -> None:
    """The dispatcher respects finite extents and ray directions in either argument order."""
    _assert_result(intersections(first, second), kind, expected)
    _assert_result(intersections(second, first), kind, expected)


@pytest.mark.parametrize(
    ("first", "second", "kind", "expected"),
    [
        (
            Segment2D(Point2D(0, 0), Point2D(1, 0)),
            Segment2D(Point2D(2, 0), Point2D(3, 0)),
            IntersectionKind.NONE,
            (),
        ),
        (
            Segment2D(Point2D(0, 0), Point2D(1, 0)),
            Segment2D(Point2D(1, 0), Point2D(2, 0)),
            IntersectionKind.ONE,
            ((1, 0),),
        ),
        (
            Segment2D(Point2D(0, 0), Point2D(2, 0)),
            Segment2D(Point2D(3, 0), Point2D(1, 0)),
            IntersectionKind.COINCIDENT,
            (),
        ),
        (
            Ray2D(Point2D(0, 0), Point2D(1, 0)),
            Ray2D(Point2D(-1, 0), Point2D(-2, 0)),
            IntersectionKind.NONE,
            (),
        ),
        (
            Ray2D(Point2D(0, 0), Point2D(1, 0)),
            Ray2D(Point2D(0, 0), Point2D(-1, 0)),
            IntersectionKind.ONE,
            ((0, 0),),
        ),
        (
            Ray2D(Point2D(0, 0), Point2D(1, 0)),
            Ray2D(Point2D(1, 0), Point2D(0, 0)),
            IntersectionKind.COINCIDENT,
            (),
        ),
        (
            Ray2D(Point2D(0, 0), Point2D(1, 0)),
            Segment2D(Point2D(-2, 0), Point2D(-1, 0)),
            IntersectionKind.NONE,
            (),
        ),
        (
            Ray2D(Point2D(0, 0), Point2D(1, 0)),
            Segment2D(Point2D(-2, 0), Point2D(0, 0)),
            IntersectionKind.ONE,
            ((0, 0),),
        ),
    ],
    ids=[
        "segments-disjoint",
        "segments-touch",
        "segments-overlap",
        "rays-disjoint",
        "rays-touch",
        "rays-overlap",
        "ray-segment-disjoint",
        "ray-segment-touch",
    ],
)
def test_collinear_objects_are_classified_using_their_actual_overlap(
    first: Intersectable,
    second: Intersectable,
    kind: IntersectionKind,
    expected: tuple[tuple[float, float], ...],
) -> None:
    """A shared supporting line alone does not imply infinitely many common points."""
    _assert_result(intersections(first, second), kind, expected)
    _assert_result(intersections(second, first), kind, expected)


@pytest.mark.parametrize("point_type", [Segment2D, Ray2D], ids=["segment", "ray"])
@pytest.mark.parametrize(
    ("other", "kind"),
    [
        (Line2D(0, 1, 0), IntersectionKind.ONE),
        (Line2D(0, 1, -1), IntersectionKind.NONE),
        (Segment2D(Point2D(0, 0), Point2D(3, 0)), IntersectionKind.ONE),
        (Segment2D(Point2D(3, 0), Point2D(4, 0)), IntersectionKind.NONE),
        (Ray2D(Point2D(0, 0), Point2D(1, 0)), IntersectionKind.ONE),
        (Ray2D(Point2D(0, 0), Point2D(-1, 0)), IntersectionKind.NONE),
        (Circle2D(Point2D(0, 0), 2), IntersectionKind.ONE),
        (Circle2D(Point2D(0, 0), 3), IntersectionKind.NONE),
        (Segment2D(Point2D(2, 0), Point2D(2, 0)), IntersectionKind.ONE),
        (Segment2D(Point2D(3, 0), Point2D(3, 0)), IntersectionKind.NONE),
    ],
    ids=[
        "on-line",
        "off-line",
        "on-segment",
        "outside-segment",
        "on-ray",
        "behind-ray",
        "on-circle",
        "inside-circle",
        "same-point",
        "different-point",
    ],
)
def test_degenerate_linear_objects_intersect_as_single_points(
    point_type: type[Segment2D] | type[Ray2D],
    other: Intersectable,
    kind: IntersectionKind,
) -> None:
    """Zero-length segments and rays remain usable without a supporting line."""
    point = Point2D(2, 0)
    degenerate = point_type(point, point)
    expected = ((2.0, 0.0),) if kind is IntersectionKind.ONE else ()

    _assert_result(intersections(degenerate, other), kind, expected)
    _assert_result(intersections(other, degenerate), kind, expected)
