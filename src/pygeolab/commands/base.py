"""Command abstractions and bounded undo/redo history for document mutations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Command(ABC):
    """Represent one reversible user-visible mutation."""

    @abstractmethod
    def execute(self) -> None:
        """Apply or reapply the mutation."""

    @abstractmethod
    def undo(self) -> None:
        """Restore the state that existed before execution."""

    def redo(self) -> None:
        """Reapply an undone command; commands may override when needed."""
        self.execute()


class CommandHistory:
    """Maintain undo and redo stacks and execute commands atomically from the UI."""

    def __init__(self, limit: int = 500) -> None:
        if limit <= 0:
            raise ValueError("La limite d'historique doit être positive")
        self.limit = limit
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    @property
    def can_undo(self) -> bool:
        """Return whether one command can currently be undone."""
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        """Return whether one command can currently be redone."""
        return bool(self._redo_stack)

    @property
    def undo_count(self) -> int:
        """Return the number of retained undo entries."""
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        """Return the number of retained redo entries."""
        return len(self._redo_stack)

    def execute(self, command: Command) -> None:
        """Execute a new command, retain it for undo and invalidate redo history."""
        command.execute()
        self._record(command)

    def record_applied(self, command: Command) -> None:
        """Record a command whose final state was already applied interactively.

        This is used for drag coalescing: mouse moves update the document directly,
        then mouse release records one reversible command without replaying it.
        """
        self._record(command)

    def undo(self) -> bool:
        """Undo the latest command and return whether anything changed."""
        if not self._undo_stack:
            return False
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        return True

    def redo(self) -> bool:
        """Redo the latest undone command and return whether anything changed."""
        if not self._redo_stack:
            return False
        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)
        return True

    def clear(self) -> None:
        """Discard both stacks without mutating the document."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    def _record(self, command: Command) -> None:
        self._undo_stack.append(command)
        if len(self._undo_stack) > self.limit:
            del self._undo_stack[: len(self._undo_stack) - self.limit]
        self._redo_stack.clear()
