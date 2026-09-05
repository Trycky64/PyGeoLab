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
