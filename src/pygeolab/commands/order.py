"""Reversible commands for document drawing order."""

from pygeolab.commands.base import Command
from pygeolab.model.document import Document


class ReorderObjectCommand(Command):
    """Move one object to a new drawing index and restore its former index on undo."""

    def __init__(self, document: Document, object_id: str, new_index: int) -> None:
        self.document = document
        self.object_id = object_id
        self.before = tuple(document.objects).index(object_id)
        self.after = new_index

    def execute(self) -> None:
        """Apply the requested drawing index."""
        self.document.reorder(self.object_id, self.after)

    def undo(self) -> None:
        """Restore the previous drawing index."""
        self.document.reorder(self.object_id, self.before)


class ReorderObjectsCommand(Command):
    """Move a group to either drawing-order edge while preserving relative order."""

    def __init__(
        self, document: Document, object_ids: set[str] | frozenset[str], *, to_front: bool
    ) -> None:
        if not object_ids:
            raise ValueError("Un changement d'ordre nécessite au moins un objet")
        self.document = document
        self.before = tuple(document.objects)
        selected = [object_id for object_id in self.before if object_id in object_ids]
        remaining = [object_id for object_id in self.before if object_id not in object_ids]
        self.after = tuple(remaining + selected if to_front else selected + remaining)

    def execute(self) -> None:
        """Apply the grouped drawing order."""
        self.document.set_order(self.after)

    def undo(self) -> None:
        """Restore the complete previous drawing order."""
        self.document.set_order(self.before)
