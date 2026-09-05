"""Exercise algebra/properties synchronization through real Qt widgets."""

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
    qtbot.addWidget(algebra); qtbot.addWidget(properties)
    properties.set_selection(frozenset({point.id}))
    properties._name.setText("B")
    properties._name.editingFinished.emit()
    assert document.get(point.id).name == "B"
    assert history.can_undo
    history.undo()
    assert document.get(point.id).name == "A"
