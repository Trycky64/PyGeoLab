"""Exercise recent-files menus, autosave configuration and startup recovery."""

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.persistence import RecoveryManager, load_project, save_project
from pygeolab.ui import main_window as main_window_module
from pygeolab.ui.dialogs.preferences_dialog import PreferencesDialog
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences
from pygeolab.ui.recent_files import RecentFiles


def _window_services(monkeypatch, tmp_path: Path) -> tuple[RecoveryManager, RecentFiles]:
    recovery = RecoveryManager(tmp_path / "recovery")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    recent = RecentFiles(settings)
    monkeypatch.setattr(main_window_module, "RecoveryManager", lambda: recovery)
    monkeypatch.setattr(main_window_module, "RecentFiles", lambda: recent)
    monkeypatch.setattr(
        Preferences,
        "load",
        classmethod(lambda cls: Preferences(autosave_enabled=True, autosave_interval_minutes=3)),
    )
    monkeypatch.setattr(Preferences, "save", lambda self: None)
    return recovery, recent


def test_main_window_restores_recovery_at_startup(
    qtbot: QtBot, monkeypatch, tmp_path: Path
) -> None:
    recovery, _recent = _window_services(monkeypatch, tmp_path)
    recovered = Document("Après crash")
    recovered.add(GeoObject("point", "A", params={"x": 1, "y": 2}))
    recovery.write(recovered)
    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.document.name == "Après crash"
    assert window.session.dirty
    assert window.session.path is None
    window.session.save(tmp_path / "restored.pgl")
    window._discard_recovery()


def test_main_window_can_ignore_recovery(qtbot: QtBot, monkeypatch, tmp_path: Path) -> None:
    recovery, _recent = _window_services(monkeypatch, tmp_path)
    recovered = Document("Ignoré")
    recovered.add(GeoObject("point", "A", params={"x": 1, "y": 2}))
    recovery.write(recovered)
    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ignore,
    )

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.document.name == "Sans titre"
    assert not recovery.available


def test_autosave_uses_recovery_then_normal_save_cleans_it(
    qtbot: QtBot, monkeypatch, tmp_path: Path
) -> None:
    recovery, recent = _window_services(monkeypatch, tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    point = window.document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))
    user_path = window.session.save(tmp_path / "user.pgl")
    window.document.update(point.id, params={"x": 4, "y": 5})

    window._autosave()

    assert recovery.available
    assert load_project(user_path).get(point.id).params["x"] == 0
    assert recovery.load().get(point.id).params["x"] == 4
    assert window._save_project()
    assert not recovery.available
    assert recent.paths()[0] == user_path


def test_recent_menu_opens_projects_and_can_be_cleared(
    qtbot: QtBot, monkeypatch, tmp_path: Path
) -> None:
    _recovery, recent = _window_services(monkeypatch, tmp_path)
    project = save_project(Document("Récent"), tmp_path / "recent.pgl")
    recent.add(project)
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)

    window._refresh_recent_menu()
    window.recent_menu.actions()[0].trigger()
    assert window.document.name == "Récent"
    window._refresh_recent_menu()
    window.recent_menu.actions()[-1].trigger()
    assert recent.paths() == ()


def test_preferences_dialog_configures_autosave(qtbot: QtBot) -> None:
    dialog = PreferencesDialog(Preferences(autosave_enabled=False, autosave_interval_minutes=7))
    qtbot.addWidget(dialog)

    assert not dialog._autosave.isChecked()
    assert not dialog._autosave_interval.isEnabled()
    dialog._autosave.setChecked(True)
    dialog._autosave_interval.setValue(9)

    preferences = dialog.preferences()
    assert preferences.autosave_enabled
    assert preferences.autosave_interval_minutes == 9
