"""Reversible editing for function definitions and their variable dependencies."""

from pygeolab.commands.base import Command
from pygeolab.model.document import Document
from pygeolab.model.objects import JsonValue


class ChangeFunctionCommand(Command):
    """Replace a function's name, expression parameters and slider dependencies."""

    def __init__(
        self,
        document: Document,
        object_id: str,
        name: str,
        dependencies: tuple[str, ...],
        params: dict[str, JsonValue],
    ) -> None:
        self.document = document
        self.object_id = object_id
        current = document.get(object_id)
        self.before = (current.name, current.dependencies, dict(current.params))
        self.after = (name, dependencies, dict(params))

    def execute(self) -> None:
        """Apply and recompute the edited function definition."""
        name, dependencies, params = self.after
        self.document.update(self.object_id, name=name, dependencies=dependencies, params=params)

    def undo(self) -> None:
        """Restore the previous function definition."""
        name, dependencies, params = self.before
        self.document.update(self.object_id, name=name, dependencies=dependencies, params=params)
