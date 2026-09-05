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

    def clear(self) -> None:
        """Remove every selected identity."""
        self._ids.clear()
