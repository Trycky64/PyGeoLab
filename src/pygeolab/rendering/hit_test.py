"""Screen-distance hit testing shared by selection and construction tools."""

from __future__ import annotations

from dataclasses import dataclass

from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D, Vector2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.rendering.clipping import clip_line, clip_ray, clip_segment
from pygeolab.rendering.viewport import Viewport


@dataclass(frozen=True, slots=True)
class HitResult:
    """One selectable object ranked by semantic priority and screen distance."""

    object_id: str
    distance_px: float
    priority: int
    z_index: int = 0


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
    for z_index, obj in enumerate(document.objects.values()):
        if not obj.visible or not obj.valid or obj.geometry is None:
            continue
        distance = _distance_px(document, obj, world, viewport.scale)
        if distance is not None and distance <= tolerance_px:
            hits.append(HitResult(obj.id, distance, _PRIORITY.get(type(obj.geometry), 99), z_index))
    hits.sort(key=lambda hit: (hit.priority, hit.distance_px, -hit.z_index, hit.object_id))
    return tuple(hits)


def objects_in_screen_rect(
    document: Document,
    viewport: Viewport,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
) -> frozenset[str]:
    """Return visible valid spatial objects intersecting a screen-space rectangle."""
    first = viewport.screen_to_world(start_x, start_y)
    second = viewport.screen_to_world(end_x, end_y)
    bounds = (
        min(first.x, second.x),
        min(first.y, second.y),
        max(first.x, second.x),
        max(first.y, second.y),
    )
    return frozenset(
        obj.id
        for obj in document.objects.values()
        if obj.visible and obj.valid and _intersects_bounds(document, obj, bounds)
    )


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


def _intersects_bounds(
    document: Document,
    obj: GeoObject,
    bounds: tuple[float, float, float, float],
) -> bool:
    left, bottom, right, top = bounds
    geometry = obj.geometry
    if isinstance(geometry, Point2D):
        return left <= geometry.x <= right and bottom <= geometry.y <= top
    if isinstance(geometry, Segment2D):
        return clip_segment(geometry.start, geometry.end, bounds) is not None
    if isinstance(geometry, Ray2D):
        return clip_ray(geometry, bounds) is not None
    if isinstance(geometry, Line2D):
        return clip_line(geometry, bounds) is not None
    if isinstance(geometry, Circle2D):
        nearest_x = min(max(geometry.center.x, left), right)
        nearest_y = min(max(geometry.center.y, bottom), top)
        minimum = geometry.center.distance_to(Point2D(nearest_x, nearest_y))
        maximum = max(
            geometry.center.distance_to(Point2D(x, y)) for x in (left, right) for y in (bottom, top)
        )
        return minimum <= geometry.radius <= maximum
    if isinstance(geometry, Polygon2D):
        return any(
            left <= vertex.x <= right and bottom <= vertex.y <= top for vertex in geometry.vertices
        ) or any(clip_segment(edge.start, edge.end, bounds) is not None for edge in geometry.edges)
    if isinstance(geometry, Vector2D) and obj.dependencies:
        start = document.get(obj.dependencies[0]).geometry
        if isinstance(start, Point2D):
            end = Point2D(start.x + geometry.x, start.y + geometry.y)
            return clip_segment(start, end, bounds) is not None
    return False
