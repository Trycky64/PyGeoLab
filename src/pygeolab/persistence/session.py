"""Track one open project, its path and unsaved-change state independently of Qt."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pygeolab.model.document import Document
from pygeolab.persistence.loader import load_project, save_project
from pygeolab.persistence.serializer import serialize_document


class ProjectSession:
    """Own current document/path and compare current content with the saved snapshot."""

    def __init__(self, document: Document | None = None) -> None:
        self.document = document or Document()
        self.path: Path | None = None
        self._saved_snapshot: dict[str, Any] = serialize_document(self.document)

    @property
    def dirty(self) -> bool:
        """Return whether serializable document content differs from last save/load."""
        return serialize_document(self.document) != self._saved_snapshot

    def new(self) -> Document:
        """Replace current state with a fresh untitled document."""
        self.document = Document()
        self.path = None
        self._saved_snapshot = serialize_document(self.document)
        return self.document

    def open(self, path: str | Path) -> Document:
        """Load a validated project and mark its content clean."""
        self.document = load_project(path)
        self.path = Path(path)
        self._saved_snapshot = serialize_document(self.document)
        return self.document

    def save(self, path: str | Path | None = None) -> Path:
        """Save to an explicit path or the existing project path and mark clean."""
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ValueError("Aucun chemin d'enregistrement défini")
        self.path = save_project(self.document, target)
        self._saved_snapshot = serialize_document(self.document)
        return self.path
