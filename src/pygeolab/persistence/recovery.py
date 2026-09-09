"""Atomic autosave recovery files kept separate from user projects."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths

from pygeolab.model.document import Document
from pygeolab.persistence.loader import load_project, save_project


class RecoveryManager:
    """Own the single-window recovery file lifecycle."""

    def __init__(self, directory: str | Path | None = None) -> None:
        root = (
            Path(directory)
            if directory is not None
            else Path(
                QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            )
            / "recovery"
        )
        self.path = root / "autosave-recovery.pgl"

    @property
    def available(self) -> bool:
        """Return whether a recovery candidate exists."""
        return self.path.is_file()

    def write(self, document: Document) -> Path:
        """Atomically replace the recovery snapshot without touching the user project."""
        return save_project(document, self.path)

    def load(self) -> Document:
        """Validate and reconstruct the recovery snapshot."""
        return load_project(self.path)

    def discard(self) -> None:
        """Remove a handled recovery file if present."""
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            raise ValueError(f"Impossible de supprimer la récupération : {exc}") from exc
