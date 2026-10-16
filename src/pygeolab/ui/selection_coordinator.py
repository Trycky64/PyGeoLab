"""Coordinate object selection across viewport and auxiliary panels without tight coupling."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    pass


class SelectionCoordinator(QObject):
    """Centralize selection state and dispatch updates without re-entrant cycles."""

    selectionChanged = Signal(object, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current_selection: frozenset[str] = frozenset()
        self._listeners: dict[str, Callable[[frozenset[str]], None]] = {}
        self._is_updating: bool = False

    @property
    def current_selection(self) -> frozenset[str]:
        """Return the immutable set of currently selected object identifiers."""
        return self._current_selection

    def register_listener(self, name: str, callback: Callable[[frozenset[str]], None]) -> None:
        """Register a panel or view selection updater callback."""
        self._listeners[name] = callback

    def unregister_listener(self, name: str) -> None:
        """Remove a registered selection updater callback."""
        self._listeners.pop(name, None)

    def set_selection(self, object_ids: frozenset[str] | set[str], source: str = "") -> None:
        """Update selection and notify all registered listeners except the triggering source."""
        normalized = frozenset(object_ids)
        if self._is_updating:
            return
        if normalized == self._current_selection and source:
            return
        self._current_selection = normalized
        self._is_updating = True
        try:
            for name, callback in list(self._listeners.items()):
                if name != source:
                    callback(normalized)
            self.selectionChanged.emit(normalized, source)
        finally:
            self._is_updating = False

    def clear(self, source: str = "") -> None:
        """Clear current selection across all listeners."""
        self.set_selection(frozenset(), source=source)
