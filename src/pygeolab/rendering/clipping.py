"""Clip infinite linear primitives to finite viewport world bounds."""

from __future__ import annotations

import math

from pygeolab.geometry import Line2D, Point2D, Ray2D, Vector2D

Bounds = tuple[float, float, float, float]


def _clip_axis(
    origin: float, direction: float, lower: float, upper: float, minimum: float, maximum: float
) -> tuple[float, float] | None:
    """Restrict a parametric interval against one axis-aligned slab."""
    if abs(direction) <= 1e-15:
        return None if origin < lower or origin > upper else (minimum, maximum)
    first = (lower - origin) / direction
    second = (upper - origin) / direction
    if first > second:
        first, second = second, first
    minimum = max(minimum, first)
    maximum = min(maximum, second)
    return None if minimum > maximum else (minimum, maximum)


def _clip_parametric(
    origin: Point2D,
    direction: Vector2D,
    bounds: Bounds,
    minimum: float,
    maximum: float,
) -> tuple[Point2D, Point2D] | None:
    """Clip origin + t*direction against an axis-aligned rectangle."""
    left, bottom, right, top = bounds
    interval = _clip_axis(origin.x, direction.x, left, right, minimum, maximum)
    if interval is None:
        return None
    interval = _clip_axis(origin.y, direction.y, bottom, top, *interval)
    if interval is None:
        return None
    low, high = interval
    if not math.isfinite(low) or not math.isfinite(high):
        return None
    return (
        Point2D(origin.x + low * direction.x, origin.y + low * direction.y),
        Point2D(origin.x + high * direction.x, origin.y + high * direction.y),
    )


def clip_line(line: Line2D, bounds: Bounds) -> tuple[Point2D, Point2D] | None:
    """Return the visible finite chord of an infinite line."""
    origin = line.project(Point2D(0.0, 0.0))
    clipped = _clip_parametric(origin, line.direction, bounds, -math.inf, math.inf)
    if clipped is None:
        return None
    first, second = clipped
    if (first.x, first.y) <= (second.x, second.y):
        return (first, second)
    return (second, first)


def clip_ray(ray: Ray2D, bounds: Bounds) -> tuple[Point2D, Point2D] | None:
    """Return the visible finite portion of a ray, including its origin when visible."""
    direction = Vector2D.between(ray.start, ray.through).normalized()
    if direction is None:
        left, bottom, right, top = bounds
        if left <= ray.start.x <= right and bottom <= ray.start.y <= top:
            return (ray.start, ray.start)
        return None
    return _clip_parametric(ray.start, direction, bounds, 0.0, math.inf)


def clip_segment(start: Point2D, end: Point2D, bounds: Bounds) -> tuple[Point2D, Point2D] | None:
    """Return the visible finite portion of a closed segment."""
    direction = Vector2D.between(start, end)
    if direction.norm <= 1e-15:
        left, bottom, right, top = bounds
        return (start, end) if left <= start.x <= right and bottom <= start.y <= top else None
    return _clip_parametric(start, direction, bounds, 0.0, 1.0)
