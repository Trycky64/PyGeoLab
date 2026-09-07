"""Screen-space snapping decisions for geometry tools and free-point drags.

The engine is independent of Qt. It compares every candidate in pixels through
the current viewport so zoom and pan never change the perceived snap radius.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from itertools import combinations

from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D
from pygeolab.geometry.intersections import intersections
from pygeolab.model.document import Document
from pygeolab.rendering.grid import adaptive_step
from pygeolab.rendering.viewport import Viewport


class SnapKind(Enum):
    """Kinds ordered by semantic priority when candidates are equally close."""

    POINT = "point"
    INTERSECTION = "intersection"
    PROJECTION = "projection"
    GRID = "grid"


@dataclass(frozen=True, slots=True)
class SnappingOptions:
    """Control enabled candidate families and the constant screen-space radius."""

    enabled: bool = True
    threshold_px: float = 10.0
    points: bool = True
    grid: bool = True
    projections: bool = True
    intersections: bool = True

    def __post_init__(self) -> None:
        if not math.isfinite(self.threshold_px) or not 1.0 <= self.threshold_px <= 100.0:
            raise ValueError("Le seuil de snapping doit être compris entre 1 et 100 pixels")


@dataclass(frozen=True, slots=True)
class SnapResult:
    """The chosen world position and enough context to render or reuse its source."""

    point: Point2D
    kind: SnapKind
    distance_px: float
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Candidate:
    point: Point2D
    kind: SnapKind
    source_ids: tuple[str, ...]


class SnapEngine:
    """Find the best nearby construction target in deterministic priority order."""

    _PRIORITY = {
        SnapKind.POINT: 0,
        SnapKind.INTERSECTION: 1,
        SnapKind.PROJECTION: 2,
        SnapKind.GRID: 3,
    }

    def snap(
        self,
        document: Document,
        viewport: Viewport,
        screen_x: float,
        screen_y: float,
        options: SnappingOptions | None = None,
        *,
        suppressed: bool = False,
        exclude_ids: frozenset[str] = frozenset(),
    ) -> SnapResult | None:
        """Return the highest-priority candidate inside the configured pixel radius.

        ``exclude_ids`` prevents a dragged point from snapping to its own old
        position. Hidden and invalid objects never contribute candidates.
        """
        options = options or SnappingOptions()
        if suppressed or not options.enabled:
            return None
        pointer = viewport.screen_to_world(screen_x, screen_y)
        candidates = self._candidates(document, viewport, pointer, options, exclude_ids)
        results = (
            SnapResult(
                candidate.point,
                candidate.kind,
                candidate.point.distance_to(pointer) * viewport.scale,
                candidate.source_ids,
            )
            for candidate in candidates
        )
        eligible = [result for result in results if result.distance_px <= options.threshold_px]
        if not eligible:
            return None
        return min(
            eligible,
            key=lambda result: (
                self._PRIORITY[result.kind],
                result.distance_px,
                result.source_ids,
                result.point.x,
                result.point.y,
            ),
        )

    def _candidates(
        self,
        document: Document,
        viewport: Viewport,
        pointer: Point2D,
        options: SnappingOptions,
        exclude_ids: frozenset[str],
    ) -> tuple[_Candidate, ...]:
        objects = tuple(
            obj
            for obj in document.objects.values()
            if obj.visible and obj.valid and obj.geometry is not None and obj.id not in exclude_ids
        )
        candidates: list[_Candidate] = []
        if options.points:
            candidates.extend(
                _Candidate(obj.geometry, SnapKind.POINT, (obj.id,))
                for obj in objects
                if isinstance(obj.geometry, Point2D)
            )
        loci = tuple(
            obj for obj in objects if isinstance(obj.geometry, (Line2D, Segment2D, Ray2D, Circle2D))
        )
        if options.intersections:
            for first, second in combinations(loci, 2):
                first_geometry = first.geometry
                second_geometry = second.geometry
                assert isinstance(first_geometry, (Line2D, Segment2D, Ray2D, Circle2D))
                assert isinstance(second_geometry, (Line2D, Segment2D, Ray2D, Circle2D))
                result = intersections(first_geometry, second_geometry)
                candidates.extend(
                    _Candidate(point, SnapKind.INTERSECTION, (first.id, second.id))
                    for point in result.points
                )
        if options.projections:
            for obj in objects:
                projection = _project(pointer, obj.geometry)
                if projection is not None:
                    candidates.append(_Candidate(projection, SnapKind.PROJECTION, (obj.id,)))
        if options.grid:
            step = adaptive_step(viewport.scale)
            grid = Point2D(round(pointer.x / step) * step, round(pointer.y / step) * step)
            candidates.append(_Candidate(grid, SnapKind.GRID, ()))
        return tuple(candidates)


def _project(pointer: Point2D, geometry: object) -> Point2D | None:
    """Return the closest supported locus point, including polygon boundaries."""
    if isinstance(geometry, Line2D):
        return geometry.project(pointer)
    if isinstance(geometry, (Segment2D, Ray2D)):
        return geometry.closest_point(pointer)
    if isinstance(geometry, Circle2D):
        radius = geometry.radius
        if radius == 0:
            return geometry.center
        dx = pointer.x - geometry.center.x
        dy = pointer.y - geometry.center.y
        length = math.hypot(dx, dy)
        if length == 0:
            return Point2D(geometry.center.x + radius, geometry.center.y)
        return Point2D(
            geometry.center.x + dx * radius / length,
            geometry.center.y + dy * radius / length,
        )
    if isinstance(geometry, Polygon2D):
        return min(
            (edge.closest_point(pointer) for edge in geometry.edges),
            key=pointer.distance_to,
        )
    return None
