"""Screen-distance hit testing shared by selection and construction tools."""

from __future__ import annotations

from dataclasses import dataclass

from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D, Vector2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.rendering.viewport import Viewport


@dataclass(frozen=True, slots=True)
class HitResult:
    """One selectable object ranked by semantic priority and screen distance."""

    object_id: str
    distance_px: float
    priority: int


_PRIORITY = {
    Point2D: 0,
    Segment2D: 2,
    Circle2D: 3,
    Ray2D: 4,
    Line2D: 4,
    Polygon2D: 5,
    Vector2D: 5,
}


def hit_test(
    document: Document,
    viewport: Viewport,
    screen_x: float,
    screen_y: float,
    tolerance_px: float = 8.0,
) -> tuple[HitResult, ...]:
    """Return visible valid objects under a screen point, best candidate first."""
    if tolerance_px <= 0:
        raise ValueError("La tolérance de hit-testing doit être positive")
    world = viewport.screen_to_world(screen_x, screen_y)
    hits: list[HitResult] = []
    for obj in document.objects.values():
        if not obj.visible or not obj.valid or obj.geometry is None:
            continue
        distance = _distance_px(document, obj, world, viewport.scale)
        if distance is not None and distance <= tolerance_px:
            hits.append(HitResult(obj.id, distance, _PRIORITY.get(type(obj.geometry), 99)))
    hits.sort(key=lambda hit: (hit.priority, hit.distance_px, hit.object_id))
    return tuple(hits)


def first_hit(
    document: Document,
    viewport: Viewport,
    screen_x: float,
    screen_y: float,
    tolerance_px: float = 8.0,
    kinds: frozenset[str] | None = None,
) -> GeoObject | None:
    """Return the highest-ranked hit, optionally restricted by GeoObject kind."""
    for hit in hit_test(document, viewport, screen_x, screen_y, tolerance_px):
        obj = document.get(hit.object_id)
        if kinds is None or obj.kind in kinds:
            return obj
    return None


def _distance_px(document: Document, obj: GeoObject, point: Point2D, scale: float) -> float | None:
    geometry = obj.geometry
    if isinstance(geometry, Point2D):
        return geometry.distance_to(point) * scale
    if isinstance(geometry, Segment2D):
        return geometry.closest_point(point).distance_to(point) * scale
    if isinstance(geometry, Ray2D):
        return geometry.closest_point(point).distance_to(point) * scale
    if isinstance(geometry, Line2D):
        return geometry.distance(point) * scale
    if isinstance(geometry, Circle2D):
        return abs(geometry.center.distance_to(point) - geometry.radius) * scale
    if isinstance(geometry, Polygon2D):
        return min(edge.closest_point(point).distance_to(point) for edge in geometry.edges) * scale
    if isinstance(geometry, Vector2D) and obj.dependencies:
        start = document.get(obj.dependencies[0]).geometry
        if isinstance(start, Point2D):
            end = Point2D(start.x + geometry.x, start.y + geometry.y)
            return Segment2D(start, end).closest_point(point).distance_to(point) * scale
    return None
