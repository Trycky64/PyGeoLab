"""Geometric locus representation and bounded sampling of dependent point trajectories.

A locus represents the curve traced by a target Point2D when a driver object
(slider, point-on-object, or parametric coordinate) varies over a bounded interval.
Evaluated curves are represented as a sequence of connected polyline pieces
(splitting across discontinuities, jumps, or invalid regions).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from pygeolab.geometry.primitives import Point2D, Segment2D

if TYPE_CHECKING:
    from pygeolab.dependency.graph import DependencyGraph
    from pygeolab.model.objects import GeoObject


def _finite(*values: float) -> None:
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Les bornes du lieu géométrique doivent être finies")


@dataclass(frozen=True, slots=True)
class Locus2D:
    """Evaluated polyline pieces of a geometric locus.

    segments: tuple of connected polyline pieces, where each piece is a tuple of Point2D.
    target_id: UUID of the traced dependent point.
    driver_id: UUID of the controlling parameter or point.
    start: starting value of the sweep parameter.
    end: ending value of the sweep parameter.
    samples: number of evaluation steps across [start, end].
    """

    segments: tuple[tuple[Point2D, ...], ...]
    target_id: str
    driver_id: str
    start: float
    end: float
    samples: int = 150

    def __post_init__(self) -> None:
        _finite(self.start, self.end)
        if self.samples < 2:
            raise ValueError("Un lieu géométrique nécessite au moins deux échantillons")

    @property
    def total_points(self) -> int:
        """Total number of sampled points across all continuous segments."""
        return sum(len(segment) for segment in self.segments)

    @property
    def is_empty(self) -> bool:
        """True when no valid points could be evaluated."""
        return not any(self.segments)

    def closest_distance_to(self, point: Point2D) -> float | None:
        """Return the minimum Euclidean distance from a test point to the locus polylines."""
        min_distance: float | None = None
        for segment in self.segments:
            for p1, p2 in zip(segment, segment[1:], strict=False):
                d = Segment2D(p1, p2).closest_point(point).distance_to(point)
                if min_distance is None or d < min_distance:
                    min_distance = d
        return min_distance


def sample_locus(
    objects: Mapping[str, GeoObject],
    graph: DependencyGraph,
    target_id: str,
    driver_id: str,
    start: float,
    end: float,
    *,
    samples: int = 150,
    jump_factor: float = 40.0,
) -> Locus2D:
    """Sample the trajectory of target_id as driver_id sweeps from start to end.

    Supports drivers of kind 'number' (slider value) and 'point_on' (parameter t).
    Only the necessary topological subgraph between driver_id and target_id is recomputed.
    Discontinuities, arithmetic errors, and invalid geometry split the curve into pieces.
    """
    from pygeolab.model.constructions import evaluate

    _finite(start, end)
    bounded_samples = min(500, max(10, samples))

    if driver_id not in objects or target_id not in objects:
        raise KeyError("Pilote ou cible introuvable dans le document")

    driver_obj = objects[driver_id]
    if driver_obj.kind not in {"number", "point_on"}:
        msg = f"Le pilote doit être un curseur ou un point sur objet, non {driver_obj.kind}"
        raise ValueError(msg)

    # The target must depend on the driver
    descendants = graph.descendants({driver_id}, include_roots=True)
    if target_id not in descendants:
        raise ValueError("Le point cible ne dépend pas de la variable pilote")

    # Determine topological evaluation order for the subgraph between driver and target
    # We only need to recompute nodes that are descendants of driver and ancestors of target
    target_ancestors = graph.ancestors(target_id) | {target_id}
    subgraph_nodes = set(descendants).intersection(target_ancestors)
    subgraph_order = [node for node in graph.topological_order() if node in subgraph_nodes]

    step = (end - start) / (bounded_samples - 1) if bounded_samples > 1 else 0.0

    pieces: list[tuple[Point2D, ...]] = []
    current_piece: list[Point2D] = []
    prev_pt: Point2D | None = None
    typical_scale = 1.0

    # Working copy of objects for subgraph evaluation
    local_objects = dict(objects)

    for i in range(bounded_samples):
        val = start + i * step
        # Update driver parameter
        driver_current = local_objects[driver_id]
        new_params = dict(driver_current.params)
        if driver_obj.kind == "number":
            new_params["value"] = val
        elif driver_obj.kind == "point_on":
            new_params["t"] = val

        local_objects[driver_id] = replace(driver_current, params=new_params)

        # Recompute subgraph nodes
        valid_step = True
        for node_id in subgraph_order:
            node_obj = local_objects[node_id]
            parents = tuple(local_objects[p] for p in node_obj.dependencies)
            if any(not p.valid or p.geometry is None for p in parents):
                local_objects[node_id] = replace(node_obj, valid=False, geometry=None)
                if node_id == target_id:
                    valid_step = False
                continue
            try:
                geom = evaluate(node_obj, parents)
                if geom is None:
                    local_objects[node_id] = replace(node_obj, valid=False, geometry=None)
                    if node_id == target_id:
                        valid_step = False
                else:
                    local_objects[node_id] = replace(node_obj, valid=True, geometry=geom)
            except (ValueError, ArithmeticError, IndexError):
                local_objects[node_id] = replace(node_obj, valid=False, geometry=None)
                if node_id == target_id:
                    valid_step = False

        if not valid_step:
            if len(current_piece) >= 2:
                pieces.append(tuple(current_piece))
            current_piece = []
            prev_pt = None
            continue

        target_geom = local_objects[target_id].geometry
        if not isinstance(target_geom, Point2D):
            if len(current_piece) >= 2:
                pieces.append(tuple(current_piece))
            current_piece = []
            prev_pt = None
            continue

        pt = target_geom
        if prev_pt is not None:
            dist = pt.distance_to(prev_pt)
            typical_scale = max(
                typical_scale,
                min(math.hypot(pt.x, pt.y), math.hypot(prev_pt.x, prev_pt.y)),
                1.0,
            )
            discontinuity = dist > jump_factor * typical_scale
            if discontinuity:
                if len(current_piece) >= 2:
                    pieces.append(tuple(current_piece))
                current_piece = []

        current_piece.append(pt)
        prev_pt = pt

    if len(current_piece) >= 2:
        pieces.append(tuple(current_piece))

    return Locus2D(
        segments=tuple(pieces),
        target_id=target_id,
        driver_id=driver_id,
        start=start,
        end=end,
        samples=bounded_samples,
    )
