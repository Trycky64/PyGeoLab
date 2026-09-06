"""Automate release smoke scenarios while mocking native desktop boundaries."""

from pathlib import Path

from PySide6.QtCore import QPoint, QUrl
from PySide6.QtWidgets import QDialog, QMessageBox
from pytestqt.qtbot import QtBot

from pygeolab.model.variables import numeric_variable, slider_spec
from pygeolab.ui import main_window as main_window_module
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences


def _deterministic_preferences(monkeypatch) -> None:
    monkeypatch.setattr(
        Preferences,
        "load",
        classmethod(lambda cls: Preferences()),
    )
    monkeypatch.setattr(Preferences, "save", lambda self: None)


def test_canvas_creation_undo_redo_is_fully_automated(qtbot: QtBot, monkeypatch) -> None:
    _deterministic_preferences(monkeypatch)
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1000, 700)
    window.show()
    qtbot.waitUntil(window.isVisible)

    window._activate_tool("point")
    view = window.geometry_view
    qtbot.mouseClick(
        view,
        main_window_module.Qt.MouseButton.LeftButton,
        pos=QPoint(view.width() // 2, view.height() // 2),
    )

    assert len(window.document.objects) == 1
    created_id = next(iter(window.document.objects))
    assert window.document.get(created_id).kind == "point"
    assert window.undo_action.isEnabled()

    window._undo()
    assert not window.document.objects
    assert window.redo_action.isEnabled()

    window._redo()
    assert created_id in window.document.objects

    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)
    window.close()


def test_project_save_open_export_preferences_and_logs_smoke(
    qtbot: QtBot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    _deterministic_preferences(monkeypatch)

    class AcceptedSliderDialog:
        def __init__(self, parent=None) -> None:
            del parent

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def variable(self):
            return numeric_variable("a", 2.0, -10.0, 10.0, 0.5)

    monkeypatch.setattr(main_window_module, "SliderDialog", AcceptedSliderDialog)
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window._new_slider()
    variable = next(obj for obj in window.document.objects.values() if obj.kind == "number")
    assert slider_spec(variable).value == 2.0
    assert window.session.dirty

    project_path = tmp_path / "automated-smoke.pgl"
    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(project_path), "Projet PyGeoLab (*.pgl)"),
    )
    assert window._save_project_as()
    assert project_path.exists()
    assert not window.session.dirty

    window.document.update(variable.id, params={**variable.params, "value": 4.0})
    assert window.session.dirty
    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Discard,
    )
    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(project_path), "Projet PyGeoLab (*.pgl)"),
    )
    window._open_project()
    restored = next(obj for obj in window.document.objects.values() if obj.kind == "number")
    assert slider_spec(restored).value == 2.0
    assert not window.session.dirty

    destinations = iter((tmp_path / "smoke.png", tmp_path / "smoke.svg"))
    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(next(destinations)), ""),
    )
    window._export_png()
    window._export_svg()
    assert (tmp_path / "smoke.png").stat().st_size > 100
    assert (tmp_path / "smoke.svg").stat().st_size > 100

    class AcceptedPreferencesDialog:
        def __init__(self, preferences: Preferences, parent=None) -> None:
            del preferences, parent

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def preferences(self) -> Preferences:
            return Preferences(dark_theme=True, export_scale=2.0, transparent_export=True)

    applied_themes: list[bool] = []
    monkeypatch.setattr(main_window_module, "PreferencesDialog", AcceptedPreferencesDialog)
    monkeypatch.setattr(
        main_window_module,
        "apply_theme",
        lambda application, dark: applied_themes.append(dark),
    )
    window._show_preferences()
    assert window.preferences == Preferences(True, 2.0, True)
    assert applied_themes == [True]

    logs = tmp_path / "logs"
    opened_urls: list[QUrl] = []
    monkeypatch.setattr(main_window_module, "log_directory", lambda: logs)
    monkeypatch.setattr(
        main_window_module.QDesktopServices,
        "openUrl",
        lambda url: opened_urls.append(url) or True,
    )
    window._open_logs()
    assert logs.is_dir()
    assert opened_urls and opened_urls[0].isLocalFile()

    window.close()


def test_unsaved_changes_prompt_covers_cancel_discard_and_save(
    qtbot: QtBot,
    monkeypatch,
) -> None:
    _deterministic_preferences(monkeypatch)
    window = MainWindow()
    qtbot.addWidget(window)
    window.document.add(numeric_variable("a", 1.0, 0.0, 10.0, 1.0))
    assert window.session.dirty

    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Cancel,
    )
    assert not window._confirm_discard_changes()

    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Discard,
    )
    assert window._confirm_discard_changes()

    save_calls: list[bool] = []
    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Save,
    )
    monkeypatch.setattr(window, "_save_project", lambda: save_calls.append(True) or True)
    assert window._confirm_discard_changes()
    assert save_calls == [True]

    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)
    window.close()


def test_invalid_open_is_reported_without_replacing_current_document(
    qtbot: QtBot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    _deterministic_preferences(monkeypatch)
    window = MainWindow()
    qtbot.addWidget(window)
    original_document = window.document
    invalid = tmp_path / "invalid.pgl"
    invalid.write_text('{"format":"not-pygeolab","version":1}', encoding="utf-8")

    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(invalid), "Projet PyGeoLab (*.pgl)"),
    )
    errors: list[tuple[str, str]] = []
    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "critical",
        lambda parent, title, text: errors.append((title, text)),
    )

    window._open_project()

    assert window.document is original_document
    assert errors
    assert "Ouverture" in errors[0][0]
    window.close()
