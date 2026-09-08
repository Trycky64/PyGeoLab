"""Exercise algebra/properties synchronization through real Qt widgets."""

from PySide6.QtWidgets import QLabel

from pygeolab.commands import CommandHistory
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.properties_panel import PropertiesPanel


def test_panels_follow_document_and_property_history(qtbot) -> None:
    document = Document()
    history = CommandHistory()
    point = document.add(GeoObject("point", "A", params={"x": 1, "y": 2}))
    algebra = AlgebraPanel(document, history.execute)
    properties = PropertiesPanel(document, history.execute)
    qtbot.addWidget(algebra)
    qtbot.addWidget(properties)
    properties.set_selection(frozenset({point.id}))
    properties._name.setText("B")
    properties._name.editingFinished.emit()
    assert document.get(point.id).name == "B"
    assert history.can_undo
    history.undo()
    assert document.get(point.id).name == "A"


def test_slider_panel_lists_numeric_variables(qtbot) -> None:
    """Numeric document objects appear as live controls without a modal window teardown."""
    from pygeolab.model.variables import numeric_variable
    from pygeolab.ui.slider_panel import SliderPanel

    document = Document()
    history = CommandHistory()
    panel = SliderPanel(document, history.execute)
    qtbot.addWidget(panel)
    document.add(numeric_variable("a", 2, 0, 10, 1))
    panel.refresh()
    assert any("a = 2" in label.text() for label in panel.findChildren(QLabel))


def test_properties_panel_edits_multiple_objects_as_grouped_commands(qtbot) -> None:
    document = Document()
    history = CommandHistory()
    first = document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))
    second = document.add(GeoObject("point", "B", params={"x": 1, "y": 0}))
    properties = PropertiesPanel(document, history.execute)
    qtbot.addWidget(properties)
    properties.set_selection({first.id, second.id})

    assert not properties._name.isEnabled()
    properties._width.setValue(4)
    assert history.undo_count == 1
    assert document.get(first.id).style.width == document.get(second.id).style.width == 4
    properties._locked.setChecked(True)
    assert history.undo_count == 2
    assert document.get(first.id).locked and document.get(second.id).locked
    properties._visible.setChecked(False)
    assert history.undo_count == 3
    assert not document.get(first.id).visible and not document.get(second.id).visible

    history.undo()
    assert document.get(first.id).visible and document.get(second.id).visible
