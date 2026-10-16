"""Tests for analytical object editing, strict validation, and panel synchronization."""

import pytest
from PySide6.QtWidgets import QApplication

from pygeolab.commands import CommandHistory
from pygeolab.geometry import Point2D, parse_point_coordinates
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.properties_panel import PropertiesPanel


def test_parse_point_coordinates_valid() -> None:
    p1 = parse_point_coordinates("(1.5, 2.5)")
    assert p1.x == 1.5 and p1.y == 2.5

    p2 = parse_point_coordinates("3.0, -4.25")
    assert p2.x == 3.0 and p2.y == -4.25

    p3 = parse_point_coordinates("-10; 20")
    assert p3.x == -10.0 and p3.y == 20.0

    p4 = parse_point_coordinates(" 7   8 ")
    assert p4.x == 7.0 and p4.y == 8.0


@pytest.mark.parametrize(
    "invalid_text",
    [
        "",
        "foo",
        "(1)",
        "(1, 2, 3)",
        "nan, 1",
        "1, inf",
        "-inf, 5",
        "1, bar",
    ],
)
def test_parse_point_coordinates_invalid(invalid_text: str) -> None:
    with pytest.raises(ValueError):
        parse_point_coordinates(invalid_text)


def test_properties_panel_edits_free_point_coordinates(qapp: QApplication) -> None:
    doc = Document()
    history = CommandHistory()
    pt = doc.add(GeoObject("point", "A", params={"x": 1.0, "y": 2.0}))

    panel = PropertiesPanel(doc, history.execute)
    panel.set_selection(frozenset({pt.id}))

    assert "x" in panel._parameter_editors
    assert "y" in panel._parameter_editors
    x_editor = panel._parameter_editors["x"]
    assert x_editor.isEnabled()
    assert x_editor.value() == 1.0

    # Edit X coordinate
    x_editor.setValue(5.5)
    assert doc.get(pt.id).geometry == Point2D(5.5, 2.0)

    # Undo
    history.undo()
    assert doc.get(pt.id).geometry == Point2D(1.0, 2.0)

    # Redo
    history.redo()
    assert doc.get(pt.id).geometry == Point2D(5.5, 2.0)

    panel.dispose()


def test_properties_panel_dependent_point_is_read_only(qapp: QApplication) -> None:
    doc = Document()
    history = CommandHistory()
    p1 = doc.add(GeoObject("point", "A", params={"x": 0.0, "y": 0.0}))
    p2 = doc.add(GeoObject("point", "B", params={"x": 4.0, "y": 4.0}))
    mid = doc.add(GeoObject("midpoint", "M", dependencies=(p1.id, p2.id)))

    panel = PropertiesPanel(doc, history.execute)
    panel.set_selection(frozenset({mid.id}))

    assert "x" in panel._parameter_editors
    assert "y" in panel._parameter_editors
    x_editor = panel._parameter_editors["x"]
    y_editor = panel._parameter_editors["y"]

    # Must be disabled / read-only for dependent points
    assert not x_editor.isEnabled()
    assert not y_editor.isEnabled()
    assert x_editor.value() == 2.0
    assert y_editor.value() == 2.0
    assert "dépendant" in x_editor.toolTip().lower()

    panel.dispose()


def test_properties_panel_locked_object_is_disabled(qapp: QApplication) -> None:
    doc = Document()
    history = CommandHistory()
    pt = doc.add(GeoObject("point", "LockedPoint", params={"x": 3.0, "y": 3.0}, locked=True))

    panel = PropertiesPanel(doc, history.execute)
    panel.set_selection(frozenset({pt.id}))

    x_editor = panel._parameter_editors["x"]
    assert not x_editor.isEnabled()
    assert "verrouillé" in x_editor.toolTip().lower()

    panel.dispose()


def test_properties_panel_circle_radius_validation(qapp: QApplication) -> None:
    doc = Document()
    history = CommandHistory()
    center = doc.add(GeoObject("point", "O", params={"x": 0.0, "y": 0.0}))
    circle = doc.add(
        GeoObject("circle_radius", "C", dependencies=(center.id,), params={"radius": 2.5})
    )

    panel = PropertiesPanel(doc, history.execute)
    panel.set_selection(frozenset({circle.id}))

    assert "radius" in panel._parameter_editors
    r_editor = panel._parameter_editors["radius"]
    assert r_editor.isEnabled()
    assert r_editor.value() == 2.5

    # Edit radius
    r_editor.setValue(4.0)
    assert doc.get(circle.id).params["radius"] == 4.0

    # Undo
    history.undo()
    assert doc.get(circle.id).params["radius"] == 2.5

    panel.dispose()


def test_algebra_panel_inline_edit_free_point(qapp: QApplication) -> None:
    doc = Document()
    history = CommandHistory()
    pt = doc.add(GeoObject("point", "A", params={"x": 1.0, "y": 2.0}))

    algebra = AlgebraPanel(doc, history.execute)

    # Find item for point A
    items = list(algebra._iter_object_items())
    assert len(items) == 1
    item = items[0]

    # Edit column 1 (Value) with signals blocked so only one _edit_item is triggered
    algebra._tree.blockSignals(True)
    item.setText(1, "(10.0, -5.0)")
    algebra._tree.blockSignals(False)
    algebra._edit_item(item, 1)

    assert doc.get(pt.id).geometry == Point2D(10.0, -5.0)

    # Undo
    history.undo()
    assert doc.get(pt.id).geometry == Point2D(1.0, 2.0)

    # Redo
    history.redo()
    assert doc.get(pt.id).geometry == Point2D(10.0, -5.0)

    # Re-fetch item reference because document subscription rebuilds tree items
    items = list(algebra._iter_object_items())
    item = items[0]

    # Attempt invalid coordinate edit -> should be rejected and refreshed
    algebra._tree.blockSignals(True)
    item.setText(1, "invalid text")
    algebra._tree.blockSignals(False)
    algebra._edit_item(item, 1)
    assert doc.get(pt.id).geometry == Point2D(10.0, -5.0)

    algebra.dispose()


def test_algebra_panel_inline_edit_dependent_point_is_rejected(qapp: QApplication) -> None:
    from PySide6.QtCore import Qt

    doc = Document()
    history = CommandHistory()
    p1 = doc.add(GeoObject("point", "A", params={"x": 0.0, "y": 0.0}))
    p2 = doc.add(GeoObject("point", "B", params={"x": 2.0, "y": 2.0}))
    mid = doc.add(GeoObject("midpoint", "M", dependencies=(p1.id, p2.id)))

    algebra = AlgebraPanel(doc, history.execute)
    items = {
        item.data(0, int(Qt.ItemDataRole.UserRole)): item for item in algebra._iter_object_items()
    }
    mid_item = items[mid.id]

    # Attempt to edit dependent midpoint coordinate
    algebra._tree.blockSignals(True)
    mid_item.setText(1, "(99, 99)")
    algebra._tree.blockSignals(False)
    algebra._edit_item(mid_item, 1)

    # Midpoint should NOT change
    assert doc.get(mid.id).geometry == Point2D(1.0, 1.0)

    algebra.dispose()
