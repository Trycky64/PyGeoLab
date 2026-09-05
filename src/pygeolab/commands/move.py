"""Point movement command supporting ordinary execution and coalesced drags."""

from pygeolab.commands.base import Command
from pygeolab.geometry import Point2D
from pygeolab.model.document import Document


class MovePointCommand(Command):
    """Move one free point between two world positions."""

    def __init__(self, document: Document, object_id: str, before: Point2D, after: Point2D) -> None:
        self.document = document
        self.object_id = object_id
        self.before = before
        self.after = after

    def execute(self) -> None:
        """Move to the final position."""
        self.document.move_point(self.object_id, self.after)

    def undo(self) -> None:
        """Restore the initial position."""
        self.document.move_point(self.object_id, self.before)
