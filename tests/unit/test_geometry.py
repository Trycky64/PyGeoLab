"""Verify primitive invariants, degeneracies and scale-independent line operations."""

import math

import pytest

from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D, Vector2D


@pytest.mark.parametrize("x,y", [(0, 0), (3, 4), (-7.25, 12), (1e8, -1e8)])
def test_distance_and_vector_invariants(x: float, y: float) -> None:
    a, b = Point2D(0, 0), Point2D(x, y)
    v = Vector2D.between(a, b)
    assert a.distance_to(b) == pytest.approx(b.distance_to(a))
    assert v.norm == pytest.approx(a.distance_to(b))
    assert v.rotated(math.pi / 2).dot(v) == pytest.approx(0, abs=max(1e-12, v.norm**2 * 1e-14))
    if v.norm:
        assert v.normalized().norm == pytest.approx(1)
    else:
        assert v.normalized() is None


@pytest.mark.parametrize("factor", [1e-15, 1, -7, 1e15])
def test_line_normalization_projection_and_constructions(factor: float) -> None:
    line = Line2D(3 * factor, 4 * factor, -5 * factor)
    point = Point2D(9, -2)
    foot = line.project(point)
    assert line.distance(foot) < 1e-8
    assert point.distance_to(foot) == pytest.approx(line.distance(point))
    assert line.parallel(point).distance(point) < 1e-8
    assert line.direction.dot(line.perpendicular(point).direction) == pytest.approx(0)


def test_degenerate_and_bounded_primitives() -> None:
    a, b = Point2D(1, 1), Point2D(3, 1)
    assert Line2D.from_points(a, a) is None
    assert Segment2D(a, a).closest_point(b) == a
    segment = Segment2D(a, b)
    assert segment.closest_point(Point2D(4, 7)) == b
    assert segment.closest_point(Point2D(2, 7)) == Point2D(2, 1)
    assert segment.bounding_box == (1, 1, 3, 1)
    ray = Ray2D(a, b)
    assert ray.contains(Point2D(20, 1))
    assert not ray.contains(Point2D(0, 1))
    assert Ray2D(a, a).line is None


def test_polygon_orientation_centroid_boundary_and_translation() -> None:
    vertices = (Point2D(0, 0), Point2D(4, 0), Point2D(4, 2), Point2D(0, 2))
    polygon = Polygon2D(vertices)
    assert polygon.area == 8
    assert polygon.perimeter == 12
    assert polygon.centroid == Point2D(2, 1)
    assert polygon.orientation == 1
    assert Polygon2D(tuple(reversed(vertices))).orientation == -1
    assert polygon.contains(Point2D(0, 1))
    assert polygon.contains(Point2D(2, 1))
    assert not polygon.contains(Point2D(5, 1))
    shifted = Polygon2D(tuple(Point2D(p.x + 1e9, p.y + 1e9) for p in vertices))
    assert shifted.area == pytest.approx(8)
    assert shifted.centroid == Point2D(1e9 + 2, 1e9 + 1)
    flat = Polygon2D((Point2D(0, 0), Point2D(1, 0), Point2D(2, 0)))
    assert flat.centroid is None


@pytest.mark.parametrize("number", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_coordinates_rejected(number: float) -> None:
    with pytest.raises(ValueError):
        Point2D(number, 0)
    with pytest.raises(ValueError):
        Circle2D(Point2D(0, 0), number)


def test_invalid_radius_and_normal_rejected() -> None:
    with pytest.raises(ValueError):
        Circle2D(Point2D(0, 0), -1)
    with pytest.raises(ValueError):
        Line2D(0, 0, 1)
