"""Exercise editable slider controls, keyboard input and history-free animation."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from pygeolab.commands import CommandHistory
from pygeolab.math_engine.functions import FunctionObject
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.variables import numeric_variable, slider_spec
from pygeolab.ui.dialogs.slider_dialog import SliderDialog
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.slider_panel import SliderPanel


def test_algebra_button_creates_a_slider_through_main_window(
    qtbot: QtBot, monkeypatch, tmp_path
) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(SliderDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(
        SliderDialog,
        "variable",
        lambda self: numeric_variable("a", 2.0, -5.0, 5.0, 0.5),
    )

    window.algebra_panel._new_slider_button.click()

    slider = next(obj for obj in window.document.objects.values() if obj.kind == "number")
    assert slider_spec(slider).value == 2.0
    assert window.geometry_view.history.undo_count == 1
    window.session.save(tmp_path / "algebra-slider.pgl")


def test_slider_dialog_edits_bounds_step_and_preserves_initial_value(qtbot: QtBot) -> None:
    variable = numeric_variable("a", 2.0, -10.0, 10.0, 0.5)
    dialog = SliderDialog(variable=variable)
    qtbot.addWidget(dialog)
    dialog.name_edit.setText("coefficient")
    dialog.minimum_spin.setValue(-3)
    dialog.maximum_spin.setValue(4)
    dialog.step_spin.setValue(0.25)
    dialog.value_spin.setValue(3)

    name, params = dialog.definition()

    assert name == "coefficient"
    assert params["value"] == 3.0
    assert params["minimum"] == -3.0
    assert params["maximum"] == 4.0
    assert params["step"] == 0.25
    assert params["initial"] == 2.0


def test_slider_direct_value_reset_and_keyboard_are_reversible(qtbot: QtBot) -> None:
    document = Document()
    variable = document.add(numeric_variable("a", 0.0, -1.0, 1.0, 0.25))
    history = CommandHistory()
    panel = SliderPanel(document, history.execute)
    qtbot.addWidget(panel)
    panel.show()
    controls = panel._rows[variable.id]

    controls.value.setValue(0.75)
    controls.value.editingFinished.emit()
    assert slider_spec(document.get(variable.id)).value == 0.75
    controls.reset.click()
    assert slider_spec(document.get(variable.id)).value == 0.0
    assert history.undo_count == 2

    controls.slider.setFocus()
    qtbot.keyClick(controls.slider, Qt.Key.Key_Right)
    assert slider_spec(document.get(variable.id)).value == 0.25
    assert history.undo_count == 3
    history.undo()
    assert slider_spec(document.get(variable.id)).value == 0.0


def test_slider_animation_recomputes_dependencies_without_history_pollution(qtbot: QtBot) -> None:
    document = Document()
    variable = document.add(numeric_variable("a", 0.0, -1.0, 1.0, 0.1))
    function = document.add(
        GeoObject(
            "function",
            "f",
            (variable.id,),
            {"variable": "x", "source": "a*x"},
        )
    )
    history = CommandHistory()
    panel = SliderPanel(document, history.execute)
    qtbot.addWidget(panel)
    controls = panel._rows[variable.id]
    controls.speed.setValue(0.2)
    controls.speed.editingFinished.emit()
    controls.ping_pong.setChecked(True)
    history_count = history.undo_count

    panel.toggle_animation(variable.id)
    panel._timer.stop()
    for _ in range(4):
        panel._animate_tick(0.2)

    updated = document.get(variable.id)
    assert slider_spec(updated).value > 0
    assert set(document.last_recomputed) == {variable.id, function.id}
    assert isinstance(document.get(function.id).geometry, FunctionObject)
    assert history.undo_count == history_count
    assert panel.active_animation_ids == {variable.id}

    panel.toggle_animation(variable.id)
    assert not panel.active_animation_ids


def test_ping_pong_animation_reverses_at_bounds(qtbot: QtBot) -> None:
    document = Document()
    variable = document.add(numeric_variable("a", 0.9, 0.0, 1.0, 0.1))
    params = dict(variable.params)
    params["ping_pong"] = True
    document.update(variable.id, params=params)
    panel = SliderPanel(document, CommandHistory().execute)
    qtbot.addWidget(panel)

    panel.toggle_animation(variable.id)
    panel._timer.stop()
    panel._animate_tick(0.2)

    assert panel._directions[variable.id] == -1
    assert slider_spec(document.get(variable.id)).value == 0.9
