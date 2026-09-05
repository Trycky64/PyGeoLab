"""Verify viewport transforms, adaptive grid spacing, clipping and painter rendering."""

import math

import pytest

from pygeolab.geometry import Line2D, Point2D, Ray2D
from pygeolab.rendering.clipping import clip_line, clip_ray, clip_segment
from pygeolab.rendering.grid import adaptive_grid, adaptive_step
from pygeolab.rendering.viewport import Viewport


def test_viewport_world_screen_round_trip_and_y_axis_orientation() -> None:
    viewport = Viewport(center=Point2D(3, -2), scale=50, width=800, height=600)
    point = Point2D(7.5, 4.25)
    screen = viewport.world_to_screen(point)

    assert viewport.screen_to_world(*screen).almost_equals(point)
    above = viewport.world_to_screen(Point2D(3, -1))[1]
    origin = viewport.world_to_screen(Point2D(3, -2))[1]
    assert above < origin


def test_pan_and_cursor_centered_zoom_preserve_expected_world_coordinates() -> None:
    viewport = Viewport(scale=100, width=1000, height=700)
    panned = viewport.panned_pixels(100, -50)
    assert panned.center == Point2D(-1, -0.5)

    cursor = (730.0, 240.0)
    before = viewport.screen_to_world(*cursor)
    zoomed = viewport.zoomed_at(2.0, *cursor)
    after = zoomed.screen_to_world(*cursor)
    assert after.almost_equals(before)
    assert zoomed.scale == 200


def test_grid_uses_documented_1_2_5_decimal_steps_and_adapts_to_zoom() -> None:
    for scale in (0.01, 0.1, 1, 10, 100, 1000, 1e5):
        step = adaptive_step(scale)
        exponent = math.floor(math.log10(step))
        normalized = step / (10**exponent)
        assert any(
            normalized == pytest.approx(candidate) for candidate in (1.0, 2.0, 5.0)
        )

    wide = adaptive_grid(Viewport(scale=20, width=800, height=600))
    close = adaptive_grid(Viewport(scale=200, width=800, height=600))
    assert close.step < wide.step
    assert all(-20 <= value <= 20 for value in wide.vertical)


def test_infinite_and_bounded_linear_primitives_clip_to_viewport() -> None:
    bounds = (-2.0, -1.0, 2.0, 1.0)
    line = clip_line(Line2D(0, 1, 0), bounds)
    assert line == (Point2D(-2, 0), Point2D(2, 0))

    ray = clip_ray(Ray2D(Point2D(0, 0), Point2D(1, 0)), bounds)
    assert ray == (Point2D(0, 0), Point2D(2, 0))
    assert clip_ray(Ray2D(Point2D(3, 0), Point2D(4, 0)), bounds) is None

    segment = clip_segment(Point2D(-5, 0.5), Point2D(5, 0.5), bounds)
    assert segment == (Point2D(-2, 0.5), Point2D(2, 0.5))

