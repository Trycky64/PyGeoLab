"""Composite command transaction for logically grouped user operations."""

from __future__ import annotations

from collections.abc import Iterable

from pygeolab.commands.base import Command


class CompositeCommand(Command):
    """Execute several commands as one history entry with rollback on failure."""

    def __init__(self, commands: Iterable[Command]) -> None:
        self.commands = tuple(commands)
        if not self.commands:
            raise ValueError("Une commande composée ne peut pas être vide")

    def execute(self) -> None:
        """Execute in order and undo already-applied members if one fails."""
        completed: list[Command] = []
        try:
            for command in self.commands:
                command.execute()
                completed.append(command)
        except Exception:
            for command in reversed(completed):
                command.undo()
            raise

    def undo(self) -> None:
        """Undo members in reverse order."""
        for command in reversed(self.commands):
            command.undo()
