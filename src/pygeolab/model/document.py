"""Own construction objects and publish validated, atomic document changes.

The registry is read-only to callers. Geometry failures remain recoverable object
states, while structural errors reject the entire edit before any notification.
"""

import logging
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from math import isfinite
from types import MappingProxyType
from typing import TypedDict, Unpack

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
    """Manage stable identities, unique names, construction state and observers."""

    def __init__(self, name: str = "Sans titre") -> None:
        self.name = name
        self.metadata: dict[str, JsonValue] = {}
        self.scene: dict[str, JsonValue] = {}
        self.revision = 0
        self.last_recomputed: tuple[str, ...] = ()
        self._objects: dict[str, GeoObject] = {}
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
        """Replace editable definition fields and recompute affected descendants.

        Identity and evaluated caches are controlled by the document. Presentation
        edits notify observers but do not recalculate geometric dependents.
        """
        current = self.get(object_id)
        reserved = {"id", "geometry", "valid", "error_state", "revision"}
        if reserved.intersection(changes):
            raise ValueError("L'identité et l'état calculé ne sont pas modifiables")
        if not changes:
            return current
        updated = replace(current, **changes)
        draft = dict(self._objects)
        draft[object_id] = updated
        geometric = bool({"kind", "params", "dependencies"}.intersection(changes))
        dirty = self._descendants(draft, {object_id}) if geometric else set()
        if not geometric:
            draft[object_id] = replace(updated, revision=current.revision + 1)
        self._apply(draft, dirty)
        return self.get(object_id)

    def move_point(self, object_id: str, point: Point2D) -> GeoObject:
        """Move an unlocked free point in world coordinates and update descendants."""
        obj = self.get(object_id)
        if not obj.movable:
            raise ValueError("Seul un point libre non verrouillé peut être déplacé")
        return self.update(object_id, params={**obj.params, "x": point.x, "y": point.y})

    def remove(self, object_id: str) -> tuple[GeoObject, ...]:
        """Remove an object and its descendants, returning definitions for undo."""
        self.get(object_id)
        removed_ids = self._descendants(self._objects, {object_id})
        removed = tuple(
            self._objects[key] for key in self._validate(self._objects) if key in removed_ids
        )
        draft = {key: obj for key, obj in self._objects.items() if key not in removed_ids}
        self._apply(draft, set())
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
        self._apply(draft, {obj.id for obj in additions})

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

    @staticmethod
    def _descendants(objects: Mapping[str, GeoObject], roots: set[str]) -> set[str]:
        children: dict[str, set[str]] = {key: set() for key in objects}
        for obj in objects.values():
            for parent in obj.dependencies:
                children.setdefault(parent, set()).add(obj.id)
        result = set(roots)
        pending = list(roots)
        while pending:
            for child in children.get(pending.pop(), set()):
                if child not in result:
                    result.add(child)
                    pending.append(child)
        return result

    @staticmethod
    def _validate(objects: Mapping[str, GeoObject]) -> tuple[str, ...]:
        names: set[str] = set()
        children: dict[str, list[str]] = {key: [] for key in objects}
        indegree: dict[str, int] = {}
        for key, obj in objects.items():
            if key != obj.id:
                raise ValueError("L'identité d'un objet ne peut pas changer")
            if not obj.name.strip() or obj.name in names:
                raise ValueError(f"Nom vide ou déjà utilisé : {obj.name}")
            names.add(obj.name)
            indegree[key] = len(obj.dependencies)
            for parent in obj.dependencies:
                if parent not in objects:
                    raise ValueError(f"Dépendance introuvable : {parent}")
                children[parent].append(key)
        pending = deque(key for key, degree in indegree.items() if degree == 0)
        ordered: list[str] = []
        while pending:
            key = pending.popleft()
            ordered.append(key)
            for child in children[key]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    pending.append(child)
        if len(ordered) != len(objects):
            raise ValueError("Une dépendance cyclique est interdite")
        return tuple(ordered)

    def _apply(self, draft: dict[str, GeoObject], dirty: set[str]) -> None:
        ordered = self._validate(draft)
        recomputed: list[str] = []
        for key in ordered:
            if key not in dirty:
                continue
            obj = draft[key]
            parents = tuple(draft[parent] for parent in obj.dependencies)
            geometry = None
            error: str | None = None
            if any(not parent.valid for parent in parents):
                error = "Une dépendance est invalide"
            else:
                try:
                    geometry = evaluate(obj, parents)
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
        self._objects = draft
        self.last_recomputed = tuple(recomputed)
        self.revision += 1
        for callback in tuple(self._observers):
            try:
                callback()
            except Exception:
                logging.getLogger(__name__).exception("Échec de notification d'un observateur")
