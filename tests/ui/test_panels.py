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
    """Numeric document objects appear as live controls in the slider dock."""
    from pygeolab.model.variables import numeric_variable
    from pygeolab.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.document.add(numeric_variable("a", 2, 0, 10, 1))
    window.slider_panel.refresh()
    assert any("a = 2" in label.text() for label in window.slider_panel.findChildren(QLabel))
