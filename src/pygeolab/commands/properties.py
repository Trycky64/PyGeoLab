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


class ChangeNumberValueCommand(Command):
    """Change a numeric variable value reversibly while preserving slider metadata."""

    def __init__(self, document: Document, object_id: str, value: float) -> None:
        from pygeolab.model.variables import slider_params

        self.document = document
        self.object_id = object_id
        current = document.get(object_id)
        self.before = dict(current.params)
        self.after = slider_params(current, value)

    def execute(self) -> None:
        """Apply the snapped numeric value and trigger dependency recomputation."""
        self.document.update(self.object_id, params=self.after)

    def undo(self) -> None:
        """Restore the previous numeric parameters."""
        self.document.update(self.object_id, params=self.before)
