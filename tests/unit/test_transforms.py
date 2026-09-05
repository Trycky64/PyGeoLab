"""Verify Euclidean transformation invariants and degenerate constructions."""

from math import pi, sqrt

import pytest

from pygeolab.geometry.primitives import Line2D, Point2D, Vector2D
from pygeolab.geometry.transforms import (
    angle,
    angle_bisector,
    circumcircle,
    midpoint,
    perpendicular_bisector,
    reflect_line,
    reflect_point,
    rotate,
    scale,
    translate,
)


def test_translation_and_midpoint() -> None:
    first, second = Point2D(-4.0, 2.0), Point2D(6.0, 8.0)
    assert midpoint(first, second) == Point2D(1.0, 5.0)
    assert translate(first, Vector2D(10.0, 6.0)) == second
    assert midpoint(first, first) == first


def test_midpoint_avoids_overflow() -> None:
    assert midpoint(Point2D(1e308, 1e308), Point2D(1e308, 1e308)) == Point2D(1e308, 1e308)


@pytest.mark.parametrize("radians", [0.0, pi / 3.0, pi / 2.0, pi, -pi / 4.0, 2.0 * pi])
def test_rotation_preserves_distance_and_is_invertible(radians: float) -> None:
    center, point = Point2D(2.0, -1.0), Point2D(5.0, 3.0)
    transformed = rotate(point, radians, center)
    assert transformed.distance_to(center) == pytest.approx(point.distance_to(center))
    assert rotate(transformed, -radians, center).almost_equals(point)


def test_counterclockwise_rotation_about_origin() -> None:
    assert rotate(Point2D(2.0, 0.0), pi / 2.0).almost_equals(Point2D(0.0, 2.0))


def test_scaling_allows_negative_and_zero_factors() -> None:
    point, center = Point2D(4.0, 6.0), Point2D(1.0, 2.0)
    assert scale(point, 0.0, center) == center
    assert scale(point, 2.0, center) == Point2D(7.0, 10.0)
    assert scale(point, -1.0, center) == Point2D(-2.0, -2.0)
    assert scale(point, 0.5) == Point2D(2.0, 3.0)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_transform_parameters_must_be_finite(value: float) -> None:
    with pytest.raises(ValueError):
        rotate(Point2D(1.0, 0.0), value)
    with pytest.raises(ValueError):
        scale(Point2D(1.0, 0.0), value)


def test_central_reflection_is_involution() -> None:
    point, center = Point2D(4.0, 3.0), Point2D(-1.0, 2.0)
    reflected = reflect_point(point, center)
    assert midpoint(point, reflected) == center
    assert reflect_point(reflected, center) == point


@pytest.mark.parametrize("line", [Line2D(1.0, 0.0, -2.0), Line2D(1.0, -1.0, 0.0)])
def test_axial_reflection_preserves_distance_and_projection(line: Line2D) -> None:
    point = Point2D(4.0, -3.0)
    reflected = reflect_line(point, line)
    assert line.distance(point) == pytest.approx(line.distance(reflected))
    assert midpoint(point, reflected).almost_equals(line.project(point))
    assert reflect_line(reflected, line).almost_equals(point)


def test_perpendicular_bisector_is_equidistance_locus() -> None:
    first, second = Point2D(-1.0, 2.0), Point2D(5.0, 4.0)
    bisector = perpendicular_bisector(first, second)
    assert bisector is not None
    for probe in (Point2D(0.0, 0.0), Point2D(-7.0, 9.0)):
        projected = bisector.project(probe)
        assert projected.distance_to(first) == pytest.approx(projected.distance_to(second))
    assert perpendicular_bisector(first, first) is None


def test_angle_and_internal_bisector() -> None:
    first, vertex, second = Point2D(2.0, 0.0), Point2D(0.0, 0.0), Point2D(0.0, 7.0)
    assert angle(first, vertex, second) == pytest.approx(pi / 2.0)
    bisector = angle_bisector(first, vertex, second)
    assert bisector is not None
    assert bisector.distance(Point2D(1.0, 1.0)) == pytest.approx(0.0)
    assert angle(vertex, vertex, second) is None
    assert angle_bisector(vertex, vertex, second) is None


def test_straight_and_zero_angles_have_defined_bisector_lines() -> None:
    vertex, first = Point2D(0.0, 0.0), Point2D(1.0, 0.0)
    opposite = Point2D(-1.0, 0.0)
    straight = angle_bisector(first, vertex, opposite)
    same = angle_bisector(first, vertex, first)
    assert angle(first, vertex, opposite) == pytest.approx(pi)
    assert straight is not None and straight.distance(Point2D(0.0, 8.0)) == pytest.approx(0.0)
    assert same is not None and same.distance(Point2D(8.0, 0.0)) == pytest.approx(0.0)


@pytest.mark.parametrize("offset", [0.0, 1e8])
def test_circumcircle_is_stable_far_from_origin(offset: float) -> None:
    vertices = (
        Point2D(offset, offset),
        Point2D(offset + 4.0, offset),
        Point2D(offset, offset + 2.0),
    )
    circle = circumcircle(*vertices)
    assert circle is not None
    assert circle.center == Point2D(offset + 2.0, offset + 1.0)
    assert circle.radius == pytest.approx(sqrt(5.0))
    assert all(
        point.distance_to(circle.center) == pytest.approx(circle.radius) for point in vertices
    )


def test_circumcircle_rejects_collinear_or_repeated_vertices() -> None:
    assert circumcircle(Point2D(0.0, 0.0), Point2D(1.0, 1.0), Point2D(2.0, 2.0)) is None
    assert circumcircle(Point2D(0.0, 0.0), Point2D(0.0, 0.0), Point2D(1.0, 2.0)) is None
