"""Commands for reversible names and visual object properties."""

from __future__ import annotations

from pygeolab.commands.base import Command
from pygeolab.model.document import Document
from pygeolab.model.styles import Style


class RenameObjectCommand(Command):
    """Rename one object reversibly."""

    def __init__(self, document: Document, object_id: str, new_name: str) -> None:
        self.document = document
        self.object_id = object_id
        self.before = document.get(object_id).name
        self.after = new_name

    def execute(self) -> None:
        """Apply the requested object name."""
        self.document.update(self.object_id, name=self.after)

    def undo(self) -> None:
        """Restore the previous object name."""
        self.document.update(self.object_id, name=self.before)


class ChangeStyleCommand(Command):
    """Replace one object's style reversibly."""

    def __init__(self, document: Document, object_id: str, new_style: Style) -> None:
        self.document = document
        self.object_id = object_id
        self.before = document.get(object_id).style
        self.after = new_style

    def execute(self) -> None:
        """Apply the requested visual style."""
        self.document.update(self.object_id, style=self.after)

    def undo(self) -> None:
        """Restore the previous visual style."""
        self.document.update(self.object_id, style=self.before)


class ChangeVisibilityCommand(Command):
    """Toggle one object's visibility reversibly."""

    def __init__(self, document: Document, object_id: str, visible: bool) -> None:
        self.document = document
        self.object_id = object_id
        self.before = document.get(object_id).visible
        self.after = visible

    def execute(self) -> None:
        """Apply the requested visibility state."""
        self.document.update(self.object_id, visible=self.after)

    def undo(self) -> None:
        """Restore the previous visibility state."""
        self.document.update(self.object_id, visible=self.before)
