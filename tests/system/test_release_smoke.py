"""Automate release smoke scenarios while mocking every native desktop boundary."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QPoint, QUrl
from PySide6.QtWidgets import QDialog, QMessageBox
from pytestqt.qtbot import QtBot

from pygeolab.model.variables import numeric_variable, slider_spec
from pygeolab.ui import main_window as main_window_module
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences


def _deterministic_preferences(monkeypatch) -> None:
    """Keep system tests independent from the developer machine's QSettings state."""
    monkeypatch.setattr(Preferences, "load", classmethod(lambda cls: Preferences()))
    monkeypatch.setattr(Preferences, "save", lambda self: None)


def _window(qtbot: QtBot, monkeypatch) -> MainWindow:
    """Create a window whose teardown can never open an unsaved-changes dialog."""
    _deterministic_preferences(monkeypatch)
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)
    return window


def _capture_message_boxes(monkeypatch) -> list[tuple[str, str, str]]:
    """Replace modal error/warning/about boxes with an inspectable in-memory log."""
    messages: list[tuple[str, str, str]] = []

    def capture(kind: str) -> Callable[..., QMessageBox.StandardButton]:
        def handler(parent, title: str, text: str, *args, **kwargs):
            del parent, args, kwargs
            messages.append((kind, title, text))
            return QMessageBox.StandardButton.Ok

        return handler

    monkeypatch.setattr(main_window_module.QMessageBox, "critical", capture("critical"))
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", capture("warning"))
    monkeypatch.setattr(main_window_module.QMessageBox, "about", capture("about"))
    return messages


def test_canvas_creation_undo_redo_is_fully_automated(qtbot: QtBot, monkeypatch) -> None:
    """The primary canvas workflow creates one point and supports one-step undo/redo."""
    window = _window(qtbot, monkeypatch)
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
    window.close()


def test_slider_creation_is_automated(qtbot: QtBot, monkeypatch) -> None:
    """Creating a slider through the MainWindow adds a dirty numeric object."""

    class AcceptedSliderDialog:
        def __init__(self, parent=None) -> None:
            del parent

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def variable(self):
            return numeric_variable("a", 2.0, -10.0, 10.0, 0.5)

    monkeypatch.setattr(main_window_module, "SliderDialog", AcceptedSliderDialog)
    window = _window(qtbot, monkeypatch)
    messages = _capture_message_boxes(monkeypatch)

    window._new_slider()

    variable = next(obj for obj in window.document.objects.values() if obj.kind == "number")
    assert slider_spec(variable).value == 2.0
    assert window.session.dirty
    assert messages == []
    window.close()


def test_project_save_and_open_round_trip_through_main_window(
    qtbot: QtBot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Save As and Open round-trip project state without showing native dialogs."""
    window = _window(qtbot, monkeypatch)
    messages = _capture_message_boxes(monkeypatch)
    variable = window.document.add(numeric_variable("a", 2.0, -10.0, 10.0, 0.5))
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
        main_window_module.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(project_path), "Projet PyGeoLab (*.pgl)"),
    )
    window._open_project()

    restored = next(obj for obj in window.document.objects.values() if obj.kind == "number")
    assert slider_spec(restored).value == 2.0
    assert not window.session.dirty
    assert messages == []
    window.close()


def test_png_export_through_main_window_is_noninteractive(
    qtbot: QtBot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """PNG export routes through MainWindow and writes a real nonempty image."""
    window = _window(qtbot, monkeypatch)
    messages = _capture_message_boxes(monkeypatch)
    window.document.add(numeric_variable("a", 2.0, -10.0, 10.0, 0.5))
    target = tmp_path / "smoke.png"
    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(target), "PNG (*.png)"),
    )

    window._export_png()

    assert messages == []
    assert target.exists()
    assert target.stat().st_size > 100
    window.close()


def test_svg_export_through_main_window_is_noninteractive(
    qtbot: QtBot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """SVG export routes through MainWindow and writes real vector output."""
    window = _window(qtbot, monkeypatch)
    messages = _capture_message_boxes(monkeypatch)
    window.document.add(numeric_variable("a", 2.0, -10.0, 10.0, 0.5))
    target = tmp_path / "smoke.svg"
    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(target), "SVG (*.svg)"),
    )

    window._export_svg()

    assert messages == []
    assert target.exists()
    assert target.stat().st_size > 100
    assert "<svg" in target.read_text(encoding="utf-8")
    window.close()


def test_preferences_and_log_directory_actions_are_noninteractive(
    qtbot: QtBot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Preferences and log-folder actions execute without native desktop interaction."""

    class AcceptedPreferencesDialog:
        def __init__(self, preferences: Preferences, parent=None) -> None:
            del preferences, parent

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def preferences(self) -> Preferences:
            return Preferences(dark_theme=True, export_scale=2.0, transparent_export=True)

    window = _window(qtbot, monkeypatch)
    messages = _capture_message_boxes(monkeypatch)
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
    assert messages == []
    window.close()


def test_unsaved_changes_prompt_covers_cancel_discard_and_save(
    qtbot: QtBot,
    monkeypatch,
) -> None:
    """All three unsaved-changes answers are handled without opening a real message box."""
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
    """An invalid project reports an error while preserving the active document."""
    window = _window(qtbot, monkeypatch)
    original_document = window.document
    invalid = tmp_path / "invalid.pgl"
    invalid.write_text('{"format":"not-pygeolab","version":1}', encoding="utf-8")

    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(invalid), "Projet PyGeoLab (*.pgl)"),
    )
    messages = _capture_message_boxes(monkeypatch)

    window._open_project()

    assert window.document is original_document
    assert messages
    assert messages[0][0] == "critical"
    assert "Ouverture" in messages[0][1]
    window.close()
