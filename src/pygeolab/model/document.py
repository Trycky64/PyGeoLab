"""Own construction objects and publish validated, atomic document changes.

The registry is read-only to callers. Geometry failures remain recoverable object
states, while structural errors reject the entire edit before any notification.
Dependency traversal and dirty recomputation are delegated to the dependency layer.
"""

import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from types import MappingProxyType
from typing import TypedDict, Unpack

from pygeolab.dependency.graph import DependencyGraph
from pygeolab.dependency.resolver import DirtyFlags, recompute_objects
from pygeolab.dependency.validation import validate_object_graph
from pygeolab.geometry import Point2D
from pygeolab.model.constructions import evaluate
from pygeolab.model.objects import GeoObject, JsonValue
from pygeolab.model.styles import Style


class ObjectChanges(TypedDict, total=False):
    """Editable definition fields; identity and computed state are never writable."""

    kind: str
    name: str
    dependencies: tuple[str, ...]
    params: Mapping[str, JsonValue]
    visible: bool
    locked: bool
    style: Style


class Document:
    """Manage stable identities, unique names, dependency state and observers."""

    def __init__(self, name: str = "Sans titre") -> None:
        self.name = name
        self.metadata: dict[str, JsonValue] = {}
        self.scene: dict[str, JsonValue] = {}
        self.revision = 0
        self.last_recomputed: tuple[str, ...] = ()
        self.last_dirty: Mapping[str, DirtyFlags] = MappingProxyType({})
        self._objects: dict[str, GeoObject] = {}
        self._graph = DependencyGraph()
        self._observers: list[Callable[[], None]] = []

    @property
    def objects(self) -> Mapping[str, GeoObject]:
        """Expose the current object registry without allowing external replacement."""
        return MappingProxyType(self._objects)

    def get(self, object_id: str) -> GeoObject:
        """Find the current value for a UUID; missing identities raise KeyError."""
        return self._objects[object_id]

    def add(self, obj: GeoObject) -> GeoObject:
        """Evaluate a new definition after validating its name and parent identities."""
        self.restore((obj,))
        return self.get(obj.id)

    def update(self, object_id: str, **changes: Unpack[ObjectChanges]) -> GeoObject:
        """Replace editable fields and recompute only geometrically affected descendants."""
        current = self.get(object_id)
        reserved = {"id", "geometry", "valid", "error_state", "revision"}
        if reserved.intersection(changes):
            raise ValueError("L'identité et l'état calculé ne sont pas modifiables")
        if not changes:
            return current

        updated = replace(current, **changes)
        draft = dict(self._objects)
        draft[object_id] = updated
        graph = validate_object_graph(draft)

        geometry_changed = bool({"kind", "params", "dependencies"}.intersection(changes))
        flags = DirtyFlags(
            geometry_dirty=geometry_changed,
            style_dirty="style" in changes,
            visibility_dirty="visible" in changes,
        )
        dirty_flags: dict[str, DirtyFlags] = {object_id: flags}
        geometry_dirty = graph.descendants({object_id}) if geometry_changed else set()
        if geometry_changed:
            for descendant in geometry_dirty:
                if descendant == object_id:
                    dirty_flags[descendant] = DirtyFlags(
                        geometry_dirty=True,
                        style_dirty=flags.style_dirty,
                        visibility_dirty=flags.visibility_dirty,
                    )
                else:
                    dirty_flags[descendant] = DirtyFlags(geometry_dirty=True)
        else:
            draft[object_id] = replace(updated, revision=current.revision + 1)

        self._commit(draft, graph, geometry_dirty, dirty_flags)
        return self.get(object_id)

    def move_point(self, object_id: str, point: Point2D) -> GeoObject:
        """Move an unlocked free point in world coordinates and update descendants."""
        obj = self.get(object_id)
        if not obj.movable:
            raise ValueError("Seul un point libre non verrouillé peut être déplacé")
        return self.update(object_id, params={**obj.params, "x": point.x, "y": point.y})

    def remove(self, object_id: str) -> tuple[GeoObject, ...]:
        """Remove an object and all descendants, returning definitions suitable for undo."""
        self.get(object_id)
        current_graph = self._graph
        removed_ids = current_graph.descendants({object_id})
        removed = tuple(
            self._objects[key]
            for key in current_graph.topological_order()
            if key in removed_ids
        )
        draft = {key: obj for key, obj in self._objects.items() if key not in removed_ids}
        graph = validate_object_graph(draft)
        dirty = {key: DirtyFlags(geometry_dirty=True) for key in removed_ids}
        self._commit(draft, graph, set(), dirty)
        return removed

    def restore(self, objects: Iterable[GeoObject]) -> None:
        """Atomically insert definitions, accepting parents in any input order."""
        additions = tuple(objects)
        if not additions:
            return
        draft = dict(self._objects)
        for obj in additions:
            if obj.id in draft:
                raise ValueError(f"Identifiant déjà présent : {obj.id}")
            draft[obj.id] = obj
        graph = validate_object_graph(draft)
        roots = {obj.id for obj in additions}
        geometry_dirty = graph.descendants(roots)
        dirty = {key: DirtyFlags(geometry_dirty=True) for key in geometry_dirty}
        self._commit(draft, graph, geometry_dirty, dirty)

    def unique_name(self, prefix: str) -> str:
        """Use the requested name when available, otherwise append a numeric suffix."""
        if not prefix.strip():
            raise ValueError("Un nom de base non vide est nécessaire")
        names = {obj.name for obj in self._objects.values()}
        if prefix not in names:
            return prefix
        suffix = 1
        while f"{prefix}{suffix}" in names:
            suffix += 1
        return f"{prefix}{suffix}"

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Observe committed changes and return an idempotent unsubscription action."""
        self._observers.append(callback)
        active = True

        def unsubscribe() -> None:
            nonlocal active
            if active:
                active = False
                self._observers.remove(callback)

        return unsubscribe

    def _commit(
        self,
        draft: dict[str, GeoObject],
        graph: DependencyGraph,
        geometry_dirty: set[str],
        dirty_flags: Mapping[str, DirtyFlags],
    ) -> None:
        """Recompute dirty geometry and atomically publish one validated document state."""
        result = recompute_objects(draft, graph, geometry_dirty, evaluate)
        self._objects = result.objects
        self._graph = graph
        self.last_recomputed = result.recomputed
        self.last_dirty = MappingProxyType(dict(dirty_flags))
        self.revision += 1
        for callback in tuple(self._observers):
            try:
                callback()
            except Exception:
                logging.getLogger(__name__).exception("Échec de notification d'un observateur")
