"""Verify recent-file pruning and atomic crash-recovery snapshots."""

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.persistence import ProjectSession, RecoveryManager, load_project, save_project
from pygeolab.ui.recent_files import RecentFiles


def _settings(path: Path) -> QSettings:
    return QSettings(str(path), QSettings.Format.IniFormat)


def test_recent_files_are_mru_bounded_and_prune_missing_entries(tmp_path: Path) -> None:
    first = save_project(Document("Premier"), tmp_path / "first.pgl")
    second = save_project(Document("Second"), tmp_path / "second.pgl")
    missing = tmp_path / "missing.pgl"
    settings = _settings(tmp_path / "settings.ini")
    settings.setValue(RecentFiles.KEY, [str(missing), str(first)])
    recent = RecentFiles(settings, limit=2)

    assert recent.paths() == (first,)
    recent.add(second)
    recent.add(first)
    assert recent.paths() == (first, second)
    first.unlink()
    assert recent.paths() == (second,)
    recent.clear()
    assert recent.paths() == ()


def test_recovery_round_trip_survives_simulated_crash_and_is_atomic(tmp_path: Path) -> None:
    manager = RecoveryManager(tmp_path / "recovery")
    document = Document("Travail récupéré")
    point = document.add(GeoObject("point", "A", params={"x": 2, "y": 3}))

    recovered_path = manager.write(document)

    assert recovered_path == manager.path
    assert manager.available
    assert not manager.path.with_suffix(".pgl.tmp").exists()
    recovered = RecoveryManager(tmp_path / "recovery").load()
    assert recovered.name == "Travail récupéré"
    assert recovered.get(point.id).name == "A"
    manager.discard()
    assert not manager.available


def test_recovery_adoption_is_dirty_even_for_an_empty_document() -> None:
    session = ProjectSession()

    session.recover(Document("Récupéré"))

    assert session.dirty
    assert session.path is None


def test_corrupt_recovery_does_not_mutate_current_session(tmp_path: Path) -> None:
    manager = RecoveryManager(tmp_path)
    manager.path.parent.mkdir(parents=True, exist_ok=True)
    manager.path.write_text("{broken", encoding="utf-8")
    session = ProjectSession()
    existing = session.document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))

    with pytest.raises(ValueError):
        session.recover(manager.load())

    assert session.document.get(existing.id).name == "A"


def test_recovery_never_overwrites_saved_user_project(tmp_path: Path) -> None:
    document = Document()
    point = document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))
    user_path = save_project(document, tmp_path / "user.pgl")
    document.move_point(point.id, Point2D(4, 5))
    manager = RecoveryManager(tmp_path / "recovery")

    manager.write(document)

    assert load_project(user_path).get(point.id).params["x"] == 0
    assert manager.load().get(point.id).params["x"] == 4
