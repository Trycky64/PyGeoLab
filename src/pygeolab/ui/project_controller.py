"""Coordinate project lifecycle, persistence session, autosave, and recovery."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from pygeolab.model.document import Document
from pygeolab.persistence import ProjectSession, RecoveryManager
from pygeolab.ui.preferences import Preferences
from pygeolab.ui.recent_files import RecentFiles

LOGGER = logging.getLogger(__name__)


class ProjectController(QObject):
    """Encapsulate document session mutation, file persistence, autosave and recovery."""

    documentAdopted = Signal(object)
    titleChanged = Signal()
    statusMessageRequested = Signal(str, int)
    errorReported = Signal(str, str, object, object)

    def __init__(
        self,
        preferences: Preferences,
        recent_files: RecentFiles | None = None,
        recovery: RecoveryManager | None = None,
        session: ProjectSession | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.preferences = preferences
        self.recent_files = recent_files or RecentFiles()
        self.recovery = recovery or RecoveryManager()
        self.session = session or ProjectSession()
        self._unsubscribe_dirty: Callable[[], None] | None = None
        self._subscribe_document()

    @property
    def document(self) -> Document:
        """Return the active document held by the current session."""
        return self.session.document

    @property
    def dirty(self) -> bool:
        """Return True when the current project has unsaved changes."""
        return self.session.dirty

    @property
    def project_path(self) -> Path | None:
        """Return the active project filesystem location, if already saved."""
        return self.session.path

    def _subscribe_document(self) -> None:
        if self._unsubscribe_dirty is not None:
            self._unsubscribe_dirty()
        self._unsubscribe_dirty = self.document.subscribe(self._on_document_changed)

    def _on_document_changed(self) -> None:
        self.titleChanged.emit()

    def new_project(self) -> None:
        """Create a fresh document in the project session."""
        self.session.new()
        self.discard_recovery()
        self._adopt_session_document()
        LOGGER.info("New project created")

    def open_path(self, path: str) -> bool:
        """Load a project file into the session and record it in recent files."""
        try:
            self.session.open(path)
        except ValueError as exc:
            self.errorReported.emit(
                "Ouverture impossible",
                "Le projet n'a pas pu être ouvert. Le document courant a été conservé.",
                exc,
                path,
            )
            return False
        self.discard_recovery()
        self.recent_files.add(path)
        self._adopt_session_document()
        LOGGER.info("Project opened: %s", path)
        return True

    def save_project(self) -> bool:
        """Save to the current path, or signal that SaveAs is required."""
        if self.session.path is None:
            return False
        try:
            path = self.session.save()
        except ValueError as exc:
            self.errorReported.emit(
                "Enregistrement impossible",
                "Le projet n'a pas pu être enregistré.",
                exc,
                str(self.session.path) if self.session.path else None,
            )
            return False
        LOGGER.info("Project saved: %s", path)
        self.recent_files.add(path)
        self.discard_recovery()
        self.titleChanged.emit()
        return True

    def save_project_to(self, path: str) -> bool:
        """Save project to a designated path."""
        try:
            saved = self.session.save(path)
        except ValueError as exc:
            self.errorReported.emit(
                "Enregistrement impossible",
                "Le projet n'a pas pu être enregistré.",
                exc,
                path,
            )
            return False
        LOGGER.info("Project saved: %s", saved)
        self.recent_files.add(saved)
        self.discard_recovery()
        self.titleChanged.emit()
        return True

    def autosave(self) -> Path | None:
        """Write current dirty document to the crash recovery storage."""
        if not self.preferences.autosave_enabled or not self.session.dirty:
            return None
        try:
            path = self.recovery.write(self.document)
        except ValueError as exc:
            LOGGER.error(
                "Autosave failed | document=%r revision=%d path=%r error=%s",
                self.document.name,
                self.document.revision,
                str(self.recovery.path),
                exc,
            )
            self.statusMessageRequested.emit(f"Échec de la sauvegarde automatique : {exc}", 8000)
            return None
        LOGGER.info("Recovery autosave written: %s", path)
        self.statusMessageRequested.emit("Sauvegarde automatique effectuée", 3000)
        return path

    def discard_recovery(self) -> None:
        """Remove recovery data from disk."""
        try:
            self.recovery.discard()
        except ValueError as exc:
            LOGGER.warning("Could not clean recovery: %s", exc)

    def recover(self) -> bool:
        """Attempt to restore a recovered crash document."""
        if not self.recovery.available:
            return False
        try:
            self.session.recover(self.recovery.load())
        except ValueError as exc:
            LOGGER.warning("Unreadable recovery | path=%r error=%s", self.recovery.path, exc)
            self.errorReported.emit(
                "Récupération impossible",
                "La récupération est illisible et a été ignorée.",
                exc,
                str(self.recovery.path),
            )
            self.discard_recovery()
            return False
        self._adopt_session_document()
        self.statusMessageRequested.emit("Document de récupération restauré", 5000)
        return True

    def _adopt_session_document(self) -> None:
        self._subscribe_document()
        self.documentAdopted.emit(self.document)
        self.titleChanged.emit()

    def dispose(self) -> None:
        """Release document subscriptions."""
        if self._unsubscribe_dirty is not None:
            self._unsubscribe_dirty()
            self._unsubscribe_dirty = None
