"""Cascade deletion command preserving removed definitions for undo."""

from pygeolab.commands.base import Command
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject


class DeleteObjectCommand(Command):
    """Delete one object and descendants, restoring the exact definitions on undo."""

    def __init__(self, document: Document, object_id: str) -> None:
        self.document = document
        self.object_id = object_id
        self._removed: tuple[GeoObject, ...] | None = None

    def execute(self) -> None:
        """Delete the target cascade and remember the resulting definitions."""
        self._removed = self.document.remove(self.object_id)

    def undo(self) -> None:
        """Restore all definitions deleted by the command."""
        if self._removed is None:
            raise RuntimeError("La commande de suppression n'a pas encore été exécutée")
        self.document.restore(self._removed)


class DeleteObjectsCommand(Command):
    """Delete several roots and their descendants as one reversible history entry."""

    def __init__(self, document: Document, object_ids: set[str] | frozenset[str]) -> None:
        if not object_ids:
            raise ValueError("Une suppression groupée nécessite au moins un objet")
        self.document = document
        self.object_ids = frozenset(object_ids)
        self._removed: tuple[GeoObject, ...] | None = None
        self._original_order: tuple[str, ...] | None = None

    def execute(self) -> None:
        """Delete every still-present selected root and retain unique definitions."""
        self._original_order = tuple(self.document.objects)
        removed: dict[str, GeoObject] = {}
        for object_id in tuple(self.document.objects):
            if object_id in self.object_ids and object_id in self.document.objects:
                removed.update((obj.id, obj) for obj in self.document.remove(object_id))
        self._removed = tuple(removed.values())

    def undo(self) -> None:
        """Restore the complete deleted subgraph atomically."""
        if self._removed is None or self._original_order is None:
            raise RuntimeError("La commande de suppression n'a pas encore été exécutée")
        self.document.restore(self._removed)
        self.document.set_order(self._original_order)
