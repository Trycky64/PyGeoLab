"""Verify snapping candidates, priorities, screen thresholds and camera invariance."""

from dataclasses import replace

import pytest

from pygeolab.geometry import Point2D
from pygeolab.interaction.snapping import SnapEngine, SnapKind, SnappingOptions
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.rendering.viewport import Viewport


def _point(name: str, x: float, y: float, **changes: object) -> GeoObject:
    point = GeoObject("point", name, params={"x": x, "y": y})
    return replace(point, **changes)


def _screen(viewport: Viewport, point: Point2D) -> tuple[float, float]:
    return viewport.world_to_screen(point)


def test_existing_point_has_priority_and_can_be_excluded() -> None:
    document = Document()
    point = document.add(_point("A", 1.08, 1.0))
    viewport = Viewport(width=800, height=600, scale=80)
    cursor = _screen(viewport, Point2D(1.0, 1.0))

    result = SnapEngine().snap(document, viewport, *cursor)

    assert result is not None
    assert result.kind is SnapKind.POINT
    assert result.point == Point2D(1.08, 1.0)
    assert result.source_ids == (point.id,)
    excluded = SnapEngine().snap(document, viewport, *cursor, exclude_ids=frozenset({point.id}))
    assert excluded is not None
    assert excluded.kind is SnapKind.GRID


def test_grid_snap_respects_pixel_threshold() -> None:
    document = Document()
    viewport = Viewport(width=800, height=600, scale=80)
    engine = SnapEngine()
    near = _screen(viewport, Point2D(2.05, -0.04))
    far = _screen(viewport, Point2D(2.20, -0.20))

    result = engine.snap(document, viewport, *near, SnappingOptions(threshold_px=6))

    assert result is not None
    assert result.kind is SnapKind.GRID
    assert result.point == Point2D(2, 0)
    assert engine.snap(document, viewport, *far, SnappingOptions(threshold_px=6)) is None


def test_projection_clamps_to_segment_and_projects_to_circle() -> None:
    document = Document()
    a = _point("A", 0, 0)
    b = _point("B", 2, 0)
    center = _point("C", 5, 0)
    edge = _point("D", 6, 0)
    segment = GeoObject("segment", "s", (a.id, b.id))
    circle = GeoObject("circle", "c", (center.id, edge.id))
    document.restore((a, b, center, edge, segment, circle))
    viewport = Viewport(width=800, height=600, scale=80)
    projection_only = SnappingOptions(points=False, grid=False, intersections=False)

    segment_result = SnapEngine().snap(
        document, viewport, *_screen(viewport, Point2D(2.02, 0.08)), projection_only
    )
    circle_result = SnapEngine().snap(
        document, viewport, *_screen(viewport, Point2D(5.72, 0.72)), projection_only
    )

    assert segment_result is not None
    assert segment_result.kind is SnapKind.PROJECTION
    assert segment_result.point == Point2D(2, 0)
    assert circle_result is not None
    assert circle_result.kind is SnapKind.PROJECTION
    assert circle_result.point.distance_to(Point2D(5, 0)) == pytest.approx(1)


def test_nearby_intersection_beats_projection() -> None:
    document = Document()
    a, b = _point("A", -2, 0), _point("B", 2, 0)
    c, d = _point("C", 0, -2), _point("D", 0, 2)
    horizontal = GeoObject("line", "h", (a.id, b.id))
    vertical = GeoObject("line", "v", (c.id, d.id))
    document.restore((a, b, c, d, horizontal, vertical))
    viewport = Viewport(width=800, height=600, scale=80)

    result = SnapEngine().snap(document, viewport, *_screen(viewport, Point2D(0.06, 0.04)))

    assert result is not None
    assert result.kind is SnapKind.INTERSECTION
    assert result.point == Point2D(0, 0)
    assert set(result.source_ids) == {horizontal.id, vertical.id}


@pytest.mark.parametrize("scale", [20.0, 80.0, 800.0])
def test_threshold_is_constant_in_screen_pixels_across_zoom(scale: float) -> None:
    document = Document()
    point = document.add(_point("A", 3, -2))
    viewport = Viewport(center=Point2D(1, -1), width=900, height=700, scale=scale)
    px, py = _screen(viewport, Point2D(3, -2))
    engine = SnapEngine()

    inside = engine.snap(document, viewport, px + 9.5, py, SnappingOptions(threshold_px=10))
    outside = engine.snap(
        document,
        viewport,
        px + 10.5,
        py,
        SnappingOptions(threshold_px=10, grid=False, projections=False),
    )

    assert inside is not None and inside.source_ids == (point.id,)
    assert inside.distance_px == pytest.approx(9.5)
    assert outside is None


def test_pan_changes_screen_location_without_changing_world_target() -> None:
    document = Document()
    document.add(_point("A", 4, 3))
    original = Viewport(width=800, height=600, scale=80)
    panned = original.panned_pixels(137, -53)
    engine = SnapEngine()

    before = engine.snap(document, original, *_screen(original, Point2D(4, 3)))
    after = engine.snap(document, panned, *_screen(panned, Point2D(4, 3)))

    assert before is not None and after is not None
    assert before.point == after.point == Point2D(4, 3)


def test_disabled_suppressed_hidden_and_invalid_targets_are_ignored() -> None:
    document = Document()
    hidden = document.add(_point("A", 1.03, 1, visible=False))
    viewport = Viewport(width=800, height=600, scale=80)
    cursor = _screen(viewport, Point2D(1, 1))
    point_only = SnappingOptions(grid=False, projections=False, intersections=False)
    engine = SnapEngine()

    assert hidden.id in document.objects
    assert engine.snap(document, viewport, *cursor, point_only) is None
    assert engine.snap(document, viewport, *cursor, SnappingOptions(enabled=False)) is None
    assert engine.snap(document, viewport, *cursor, suppressed=True) is None


@pytest.mark.parametrize("threshold", [0, 0.5, 101, float("nan"), float("inf")])
def test_invalid_threshold_is_rejected(threshold: float) -> None:
    with pytest.raises(ValueError):
        SnappingOptions(threshold_px=threshold)
