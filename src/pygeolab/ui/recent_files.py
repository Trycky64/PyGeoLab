"""Persistent, self-cleaning recent project paths."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings


class RecentFiles:
    """Store a bounded MRU list and remove paths that no longer exist."""

    KEY = "files/recent"

    def __init__(self, settings: QSettings | None = None, limit: int = 10) -> None:
        self._settings = settings if settings is not None else QSettings()
        self.limit = limit

    def paths(self) -> tuple[Path, ...]:
        """Return existing files in most-recent-first order and persist pruning."""
        raw = self._settings.value(self.KEY, [])
        values = [raw] if isinstance(raw, str) else raw if isinstance(raw, list) else []
        paths: list[Path] = []
        for value in values:
            if not isinstance(value, str):
                continue
            path = Path(value).expanduser()
            if path.is_file() and path not in paths:
                paths.append(path)
        self._store(paths)
        return tuple(paths)

    def add(self, path: str | Path) -> None:
        """Move one existing project to the front of the list."""
        candidate = Path(path).expanduser().resolve()
        if not candidate.is_file():
            return
        paths = [item for item in self.paths() if item != candidate]
        self._store([candidate, *paths][: self.limit])

    def clear(self) -> None:
        """Forget every recent path."""
        self._store([])

    def _store(self, paths: list[Path]) -> None:
        self._settings.setValue(self.KEY, [str(path) for path in paths])
        self._settings.sync()
