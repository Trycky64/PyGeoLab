"""Dirty-state tracking and incremental geometry recomputation for document objects."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from math import isfinite

from pygeolab.dependency.graph import DependencyGraph
from pygeolab.model.objects import Geometry, GeoObject


@dataclass(frozen=True, slots=True)
class DirtyFlags:
    """Describe which presentation or geometry aspects changed during one edit."""

    geometry_dirty: bool = False
    style_dirty: bool = False
    visibility_dirty: bool = False

    @property
    def any(self) -> bool:
        """Return whether at least one tracked aspect is dirty."""
        return self.geometry_dirty or self.style_dirty or self.visibility_dirty


@dataclass(frozen=True, slots=True)
class RecomputeResult:
    """Return rebuilt object values together with their actual recomputation order."""

    objects: dict[str, GeoObject]
    recomputed: tuple[str, ...]


def recompute_objects(
    objects: Mapping[str, GeoObject],
    graph: DependencyGraph,
    dirty: set[str],
    evaluator: Callable[[GeoObject, tuple[GeoObject, ...]], Geometry | None],
) -> RecomputeResult:
    """Recompute only dirty identities in topological order and propagate invalidity."""
    draft = dict(objects)
    recomputed: list[str] = []
    for key in graph.topological_order(dirty):
        obj = draft[key]
        parents = tuple(draft[parent] for parent in obj.dependencies)
        geometry: Geometry | None = None
        error: str | None = None
        if any(not parent.valid for parent in parents):
            error = "Une dépendance est invalide"
        else:
            try:
                geometry = evaluator(obj, parents)
                if isinstance(geometry, float) and not isfinite(geometry):
                    geometry = None
                    raise ValueError("Le résultat numérique n'est pas fini")
                if geometry is None:
                    error = "Cette construction est actuellement impossible"
            except (ValueError, ArithmeticError, IndexError) as exception:
                error = str(exception) or "Définition de construction invalide"
        draft[key] = replace(
            obj,
            geometry=geometry,
            valid=error is None,
            error_state=error,
            revision=obj.revision + 1,
        )
        recomputed.append(key)
    return RecomputeResult(draft, tuple(recomputed))
