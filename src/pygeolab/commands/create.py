"""Creation commands for one object or an atomic construction batch."""

from __future__ import annotations

from collections.abc import Iterable

from pygeolab.commands.base import Command
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject


class CreateObjectCommand(Command):
    """Create one logical object and remove it with all created descendants on undo."""

    def __init__(self, document: Document, obj: GeoObject) -> None:
        self.document = document
        self.obj = obj

    def execute(self) -> None:
        """Insert the stored definition into the document."""
        self.document.restore((self.obj,))

    def undo(self) -> None:
        """Remove the object created by this command."""
        self.document.remove(self.obj.id)


class CreateObjectsCommand(Command):
    """Create a dependency-linked batch atomically, useful for implicit points."""

    def __init__(self, document: Document, objects: Iterable[GeoObject]) -> None:
        self.document = document
        self.objects = tuple(objects)
        if not self.objects:
            raise ValueError("Une création groupée nécessite au moins un objet")

    def execute(self) -> None:
        """Restore every definition in one validated document transaction."""
        self.document.restore(self.objects)

    def undo(self) -> None:
        """Remove all batch roots; cascade deletion removes dependent batch objects."""
        ids = {obj.id for obj in self.objects}
        roots = [obj for obj in self.objects if not ids.intersection(obj.dependencies)]
        # In construction batches implicit points are roots. If no obvious root exists,
        # removing the first object is still deterministic and validated by Document.
        for obj in roots or self.objects[:1]:
            if obj.id in self.document.objects:
                self.document.remove(obj.id)
