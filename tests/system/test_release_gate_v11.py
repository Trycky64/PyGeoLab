"""End-to-end noninteractive smoke coverage for the v1.1 release gate."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from pygeolab.geometry import Point2D
from pygeolab.math_engine.functions import FunctionObject
from pygeolab.model.objects import GeoObject
from pygeolab.model.variables import numeric_variable
from pygeolab.persistence import ProjectSession, RecoveryManager
from pygeolab.ui import main_window as main_window_module
from pygeolab.ui.dialogs.export_dialog import ExportOptions
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences


def _window(qtbot: QtBot, monkeypatch, tmp_path: Path) -> MainWindow:
    monkeypatch.setattr(Preferences, "load", classmethod(lambda cls: Preferences()))
    monkeypatch.setattr(Preferences, "save", lambda self, settings=None: None)
    monkeypatch.setattr(
        main_window_module,
        "RecoveryManager",
        lambda: RecoveryManager(tmp_path / "recovery"),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)
    return window


def _click(window: MainWindow, point: Point2D) -> None:
    position = window.geometry_view.viewport.world_to_screen(point)
    window.geometry_view.interaction.pointer_press(*position)
    window.geometry_view.interaction.pointer_release(*position)


def test_release_smoke_snapping(qtbot: QtBot, monkeypatch, tmp_path: Path) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)
    window.geometry_view.activate_tool("segment")
    _click(window, Point2D(0.04, 0.03))
    _click(window, Point2D(2.05, 0.04))

    points = [obj.geometry for obj in window.document.objects.values() if obj.kind == "point"]
    assert points == [Point2D(0.0, 0.0), Point2D(2.0, 0.0)]
    assert window.geometry_view.history.undo_count == 1


def test_release_smoke_advanced_tool(qtbot: QtBot, monkeypatch, tmp_path: Path) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)
    window.document.restore(
        (
            GeoObject("point", "A", params={"x": 0.0, "y": 0.0}),
            GeoObject("point", "B", params={"x": 2.0, "y": 1.0}),
        )
    )
    window.geometry_view.activate_tool("vector")
    _click(window, Point2D(0.0, 0.0))
    _click(window, Point2D(2.0, 1.0))

    vector = next(obj for obj in window.document.objects.values() if obj.kind == "vector")
    assert vector.valid
    assert window.geometry_view.history.undo()
    assert vector.id not in window.document.objects


def test_release_smoke_function_and_animated_slider(
    qtbot: QtBot, monkeypatch, tmp_path: Path
) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)
    slider = numeric_variable("a", 1.0, 0.0, 10.0, 0.1)
    function = GeoObject(
        "function",
        "f",
        (slider.id,),
        params={"source": "sin(x) + a", "variable": "x"},
    )
    window.document.restore((slider, function))
    before_history = window.geometry_view.history.undo_count

    window.slider_panel.toggle_animation(slider.id)
    window.slider_panel._timer.stop()
    window.slider_panel._animate_tick(elapsed=0.2)

    assert isinstance(window.document.get(function.id).geometry, FunctionObject)
    assert window.document.get(slider.id).geometry != 1.0
    assert function.id in window.document.last_recomputed
    assert window.geometry_view.history.undo_count == before_history


def test_release_smoke_autosave_and_recovery(qtbot: QtBot, monkeypatch, tmp_path: Path) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)
    window.preferences = replace(window.preferences, autosave_enabled=True)
    point = window.document.add(GeoObject("point", "A", params={"x": 3.0, "y": 4.0}))

    window._autosave()
    recovered = window.recovery.load()
    session = ProjectSession()
    session.recover(recovered)

    assert window.recovery.available
    assert session.document.get(point.id).geometry == Point2D(3.0, 4.0)
    assert session.dirty


def test_release_smoke_selection_export(qtbot: QtBot, monkeypatch, tmp_path: Path) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)
    first = window.document.add(GeoObject("point", "A", params={"x": 0.0, "y": 0.0}))
    window.document.add(GeoObject("point", "B", params={"x": 3.0, "y": 3.0}))
    window.geometry_view.set_selected_ids({first.id})
    target = tmp_path / "selection.svg"

    class SelectionExportDialog:
        def __init__(self, width, height, scale, transparent, has_selection, parent=None) -> None:
            del parent
            assert has_selection
            self._options = ExportOptions("selection", transparent, scale, width, height)

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def options(self) -> ExportOptions:
            return self._options

    exported_ids: list[frozenset[str] | None] = []
    original_export = main_window_module.export_svg

    def capture_export(*args, **kwargs):
        object_ids = kwargs.get("object_ids")
        exported_ids.append(None if object_ids is None else frozenset(object_ids))
        return original_export(*args, **kwargs)

    monkeypatch.setattr(main_window_module, "ExportDialog", SelectionExportDialog)
    monkeypatch.setattr(main_window_module, "export_svg", capture_export)
    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(target), "SVG (*.svg)"),
    )

    window._export_svg()

    assert target.is_file() and target.stat().st_size > 100
    assert exported_ids == [frozenset({first.id})]


def test_python_module_executable_smoke_mode_exits_cleanly() -> None:
    environment = dict(os.environ)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [sys.executable, "-m", "pygeolab", "--smoke-test"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
