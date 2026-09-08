"""Exercise advanced tools through dynamic dependencies and Qt Escape handling."""

from pathlib import Path

from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from pygeolab.geometry import Point2D
from pygeolab.interaction import InteractionController
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.persistence import load_project, save_project
from pygeolab.rendering.viewport import Viewport
from pygeolab.ui.geometry_view import GeometryView

VIEWPORT = Viewport(width=800, height=600, scale=80)


def _screen(point: Point2D) -> tuple[float, float]:
    return VIEWPORT.world_to_screen(point)


def _click(controller: InteractionController, point: Point2D) -> None:
    x, y = _screen(point)
    controller.pointer_press(x, y)
    controller.pointer_release(x, y)


def test_vector_driven_translation_recomputes_and_remains_reversible() -> None:
    document = Document()
    origin = GeoObject("point", "O", params={"x": 0, "y": 0})
    endpoint = GeoObject("point", "B", params={"x": 0, "y": 1})
    source = GeoObject("point", "A", params={"x": 2, "y": 0})
    document.restore((origin, endpoint, source))
    controller = InteractionController(document, VIEWPORT)

    controller.activate("vector")
    _click(controller, Point2D(0, 0))
    _click(controller, Point2D(0, 1))
    vector = next(obj for obj in document.objects.values() if obj.kind == "vector")
    controller.activate("translate")
    _click(controller, Point2D(2, 0))
    _click(controller, Point2D(0, 0.5))
    translated = next(obj for obj in document.objects.values() if obj.kind == "translate")
    assert translated.dependencies == (source.id, vector.id)
    assert translated.geometry == Point2D(2, 1)

    document.move_point(endpoint.id, Point2D(0, 3))
    assert document.get(translated.id).geometry == Point2D(2, 3)
    assert translated.id in document.last_recomputed

    assert controller.undo()
    assert translated.id not in document.objects
    assert controller.redo()
    assert document.get(translated.id).geometry == Point2D(2, 3)


def test_escape_key_cancels_advanced_preview_without_document_mutation(qtbot: QtBot) -> None:
    document = Document()
    first = GeoObject("point", "A", params={"x": 1, "y": 0})
    center = GeoObject("point", "O", params={"x": 0, "y": 0})
    document.restore((first, center))
    view = GeometryView(document)
    qtbot.addWidget(view)
    view.resize(800, 600)
    view.show()
    qtbot.waitUntil(view.isVisible)
    view.activate_tool("circumcircle")
    for point in (Point2D(1, 0), Point2D(0, 0)):
        x, y = view.viewport.world_to_screen(point)
        view.interaction.pointer_press(x, y)
        view.interaction.pointer_release(x, y)
    view.interaction.pointer_move(*view.viewport.world_to_screen(Point2D(0, 1)))
    assert view.interaction.preview
    before = set(document.objects)

    qtbot.keyClick(view, Qt.Key.Key_Escape)

    assert not view.interaction.preview
    assert set(document.objects) == before
    assert view.history.undo_count == 0


def test_advanced_tool_recipes_round_trip_in_version_one_format(tmp_path: Path) -> None:
    document = Document()
    origin = GeoObject("point", "O", params={"x": 0, "y": 0})
    right = GeoObject("point", "A", params={"x": 1, "y": 0})
    top = GeoObject("point", "B", params={"x": 0, "y": 1})
    document.restore((origin, right, top))
    controller = InteractionController(document, VIEWPORT)

    for tool, clicks in (
        ("ray", (Point2D(0, 0), Point2D(1, 0))),
        ("circle_radius", (Point2D(0, 0), Point2D(0, 1))),
        ("rotate", (Point2D(1, 0), Point2D(0, 0), Point2D(0, 1))),
    ):
        controller.activate(tool)
        for point in clicks:
            _click(controller, point)

    path = save_project(document, tmp_path / "advanced.pgl")
    loaded = load_project(path)

    assert tuple(loaded.objects) == tuple(document.objects)
    for object_id, original in document.objects.items():
        assert loaded.get(object_id).kind == original.kind
        assert loaded.get(object_id).params == original.params
        assert loaded.get(object_id).geometry == original.geometry
