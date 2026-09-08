"""Selection state independent of Qt widgets and rendering details."""

from __future__ import annotations


class SelectionModel:
    """Maintain an ordered-free set of selected object UUIDs."""

    def __init__(self) -> None:
        self._ids: set[str] = set()

    @property
    def ids(self) -> frozenset[str]:
        """Return selected identities as an immutable set."""
        return frozenset(self._ids)

    def replace(self, object_id: str | None) -> None:
        """Select exactly one object, or clear when object_id is None."""
        self._ids = set() if object_id is None else {object_id}

    def toggle(self, object_id: str) -> None:
        """Toggle one identity for Shift-click multi-selection."""
        if object_id in self._ids:
            self._ids.remove(object_id)
        else:
            self._ids.add(object_id)

    def replace_many(self, object_ids: set[str] | frozenset[str]) -> None:
        """Replace the complete selection with the supplied identities."""
        self._ids = set(object_ids)

    def add_many(self, object_ids: set[str] | frozenset[str]) -> None:
        """Add several identities without changing existing selection."""
        self._ids.update(object_ids)

    def toggle_many(self, object_ids: set[str] | frozenset[str]) -> None:
        """Toggle several identities as one selection gesture."""
        self._ids.symmetric_difference_update(object_ids)

    def clear(self) -> None:
        """Remove every selected identity."""
        self._ids.clear()
