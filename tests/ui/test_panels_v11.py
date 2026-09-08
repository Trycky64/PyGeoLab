"""Exercise the searchable algebra tree and dependency-aware property editor."""

from PySide6.QtCore import Qt

from pygeolab.commands import CommandHistory
from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.properties_panel import PropertiesPanel


def _item(panel: AlgebraPanel, object_id: str):
    return next(
        item
        for item in panel._iter_object_items()
        if item.data(0, Qt.ItemDataRole.UserRole) == object_id
    )


def test_algebra_search_sort_grouping_and_selection_survive_filtering(qtbot) -> None:
    document = Document()
    beta = document.add(GeoObject("point", "Beta", params={"x": 0, "y": 0}))
    alpha = document.add(GeoObject("point", "Alpha", params={"x": 1, "y": 0}))
    history = CommandHistory()
    panel = AlgebraPanel(document, history.execute)
    qtbot.addWidget(panel)
    panel._group.setCurrentIndex(2)
    panel._sort.setCurrentIndex(1)

    assert [panel._tree.topLevelItem(i).text(0) for i in range(2)] == ["Alpha", "Beta"]
    panel.set_selected_ids({alpha.id})
    panel._search.setText("beta")
    assert [item.text(0) for item in panel._iter_object_items()] == ["Beta"]
    panel._search.clear()
    assert _item(panel, alpha.id).isSelected()

    panel._group.setCurrentIndex(1)
    assert panel._tree.topLevelItem(0).text(0) == "point"
    assert {item.data(0, Qt.ItemDataRole.UserRole) for item in panel._iter_object_items()} == {
        alpha.id,
        beta.id,
    }


def test_algebra_inline_name_visibility_and_lock_use_history(qtbot) -> None:
    document = Document()
    point = document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))
    history = CommandHistory()
    panel = AlgebraPanel(document, history.execute)
    qtbot.addWidget(panel)

    _item(panel, point.id).setText(0, "Renommé")
    assert document.get(point.id).name == "Renommé"
    _item(panel, point.id).setCheckState(2, Qt.CheckState.Unchecked)
    assert not document.get(point.id).visible
    _item(panel, point.id).setCheckState(3, Qt.CheckState.Checked)
    assert document.get(point.id).locked
    assert history.undo_count == 3

    history.undo()
    history.undo()
    history.undo()
    restored = document.get(point.id)
    assert restored.name == "A" and restored.visible and not restored.locked


def test_algebra_exposes_invalid_state_and_error_message(qtbot) -> None:
    document = Document()
    first = GeoObject("point", "A", params={"x": 0, "y": 0})
    second = GeoObject("point", "B", params={"x": 0, "y": 0})
    line = GeoObject("line", "d", (first.id, second.id))
    document.restore((first, second, line))
    panel = AlgebraPanel(document, CommandHistory().execute)
    qtbot.addWidget(panel)

    invalid = document.get(line.id)
    item = _item(panel, line.id)
    assert not invalid.valid and invalid.error_state
    assert "indéfini" in item.text(1)
    assert invalid.error_state in item.text(1)
    assert item.toolTip(0) == invalid.error_state


def test_algebra_exposes_function_expression_errors(qtbot) -> None:
    document = Document()
    function = document.add(GeoObject("function", "f", params={"variable": "x", "source": "sin("}))
    panel = AlgebraPanel(document, CommandHistory().execute)
    qtbot.addWidget(panel)

    invalid = document.get(function.id)
    item = _item(panel, function.id)
    assert not invalid.valid and invalid.error_state
    assert invalid.error_state in item.text(1)
    assert item.toolTip(0) == invalid.error_state


def test_properties_show_graph_select_relations_and_edit_parameters(qtbot) -> None:
    document = Document()
    first = GeoObject("point", "A", params={"x": 0, "y": 0})
    second = GeoObject("point", "B", params={"x": 2, "y": 0})
    segment = GeoObject("segment", "s", (first.id, second.id))
    document.restore((first, second, segment))
    history = CommandHistory()
    panel = PropertiesPanel(document, history.execute)
    qtbot.addWidget(panel)
    requested: list[frozenset[str]] = []
    panel.selectionRequested.connect(requested.append)

    panel.set_selection({segment.id})
    assert panel._parents.text() == "A, B"
    assert panel._descendants.text() == "—"
    panel._select_parents_button.click()
    assert requested[-1] == {first.id, second.id}

    panel.set_selection({first.id})
    assert panel._descendants.text() == "s"
    panel._select_descendants_button.click()
    assert requested[-1] == {segment.id}
    assert set(panel._parameter_editors) == {"x", "y"}
    panel._parameter_editors["x"].setValue(1)
    assert document.get(first.id).geometry == Point2D(1, 0)
    assert history.undo_count == 1
    history.undo()
    assert document.get(first.id).geometry == Point2D(0, 0)
