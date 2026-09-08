"""Verify advanced tool state machines, previews, recipes and reversible commands."""

import math
from collections.abc import Iterable

import pytest

from pygeolab.geometry import Circle2D, Line2D, Point2D, Ray2D, Vector2D
from pygeolab.interaction import InteractionController
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.rendering.viewport import Viewport

VIEWPORT = Viewport(width=800, height=600, scale=80)


def _screen(point: Point2D) -> tuple[float, float]:
    return VIEWPORT.world_to_screen(point)


def _click(controller: InteractionController, point: Point2D) -> None:
    x, y = _screen(point)
    controller.pointer_press(x, y)
    controller.pointer_release(x, y)


def _prepare() -> tuple[Document, dict[str, GeoObject]]:
    document = Document()
    definitions = {
        "origin": GeoObject("point", "O", params={"x": 0, "y": 0}),
        "right": GeoObject("point", "A", params={"x": 1, "y": 0}),
        "top": GeoObject("point", "B", params={"x": 0, "y": 1}),
        "left": GeoObject("point", "C", params={"x": -1, "y": 0}),
        "far_left": GeoObject("point", "D", params={"x": -2, "y": 0}),
        "far_right": GeoObject("point", "E", params={"x": 2, "y": 0}),
    }
    line = GeoObject(
        "line",
        "d",
        (definitions["far_left"].id, definitions["far_right"].id),
    )
    vector = GeoObject("vector", "v", (definitions["origin"].id, definitions["top"].id))
    document.restore((*definitions.values(), line, vector))
    definitions["line"] = document.get(line.id)
    definitions["vector"] = document.get(vector.id)
    return document, definitions


def _perform(
    controller: InteractionController,
    tool: str,
    clicks: Iterable[Point2D],
    preview_at: Point2D,
) -> None:
    controller.activate(tool)
    click_points = tuple(clicks)
    for point in click_points[:-1]:
        _click(controller, point)
    controller.pointer_move(*_screen(preview_at))
    assert controller.preview, f"L'outil {tool} doit fournir une preview"
    _click(controller, click_points[-1])


@pytest.mark.parametrize(
    "tool,kind,clicks,preview",
    [
        ("ray", "ray", (Point2D(0, 0), Point2D(1, 0)), Point2D(1, 0)),
        ("vector", "vector", (Point2D(0, 0), Point2D(0, 1)), Point2D(0, 1)),
        (
            "perpendicular_bisector",
            "perpendicular_bisector",
            (Point2D(1, 0), Point2D(-1, 0)),
            Point2D(-1, 0),
        ),
        (
            "angle_bisector",
            "angle_bisector",
            (Point2D(1, 0), Point2D(0, 0), Point2D(0, 1)),
            Point2D(0, 1),
        ),
        (
            "projection",
            "projection",
            (Point2D(0, 1), Point2D(0.5, 0)),
            Point2D(0.5, 0),
        ),
        ("point_on", "point_on", (Point2D(0.5, 0),), Point2D(0.5, 0)),
        (
            "circle_radius",
            "circle_radius",
            (Point2D(0, 0), Point2D(1, 0)),
            Point2D(1, 0),
        ),
        (
            "circumcircle",
            "circumcircle",
            (Point2D(1, 0), Point2D(0, 0), Point2D(0, 1)),
            Point2D(0, 1),
        ),
        ("distance", "distance", (Point2D(1, 0), Point2D(0, 1)), Point2D(0, 1)),
        (
            "angle",
            "angle",
            (Point2D(1, 0), Point2D(0, 0), Point2D(0, 1)),
            Point2D(0, 1),
        ),
        (
            "translate",
            "translate",
            (Point2D(1, 0), Point2D(0, 0.5)),
            Point2D(0, 0.5),
        ),
        (
            "rotate",
            "rotate",
            (Point2D(1, 0), Point2D(0, 0), Point2D(0, 1)),
            Point2D(0, 1),
        ),
        (
            "reflect_point",
            "reflect_point",
            (Point2D(1, 0), Point2D(0, 0)),
            Point2D(0, 0),
        ),
        (
            "reflect_line",
            "reflect_line",
            (Point2D(0, 1), Point2D(0.5, 0)),
            Point2D(0.5, 0),
        ),
        (
            "scale",
            "scale",
            (Point2D(1, 0), Point2D(0, 0), Point2D(-1, 0)),
            Point2D(-1, 0),
        ),
    ],
)
def test_advanced_tools_preview_commit_and_undo_redo(
    tool: str,
    kind: str,
    clicks: tuple[Point2D, ...],
    preview: Point2D,
) -> None:
    document, _ = _prepare()
    controller = InteractionController(document, VIEWPORT)
    original_ids = set(document.objects)

    _perform(controller, tool, clicks, preview)

    created = [obj for key, obj in document.objects.items() if key not in original_ids]
    assert len(created) == 1
    assert created[0].kind == kind
    assert created[0].valid
    assert controller.history.undo_count == 1
    assert controller.undo()
    assert set(document.objects) == original_ids
    assert controller.redo()
    assert created[0].id in document.objects


@pytest.mark.parametrize(
    "tool,partial_clicks,preview",
    [
        ("ray", (Point2D(0, 0),), Point2D(1, 0)),
        ("vector", (Point2D(0, 0),), Point2D(0, 1)),
        ("perpendicular_bisector", (Point2D(1, 0),), Point2D(-1, 0)),
        ("angle_bisector", (Point2D(1, 0), Point2D(0, 0)), Point2D(0, 1)),
        ("projection", (Point2D(0, 1),), Point2D(0.5, 0)),
        ("point_on", (), Point2D(0.5, 0)),
        ("circle_radius", (Point2D(0, 0),), Point2D(1, 0)),
        ("circumcircle", (Point2D(1, 0), Point2D(0, 0)), Point2D(0, 1)),
        ("distance", (Point2D(1, 0),), Point2D(0, 1)),
        ("angle", (Point2D(1, 0), Point2D(0, 0)), Point2D(0, 1)),
        ("translate", (Point2D(1, 0),), Point2D(0, 0.5)),
        ("rotate", (Point2D(1, 0), Point2D(0, 0)), Point2D(0, 1)),
        ("reflect_point", (Point2D(1, 0),), Point2D(0, 0)),
        ("reflect_line", (Point2D(0, 1),), Point2D(0.5, 0)),
        ("scale", (Point2D(1, 0), Point2D(0, 0)), Point2D(-1, 0)),
    ],
)
def test_escape_clears_every_advanced_tool_preview(
    tool: str, partial_clicks: tuple[Point2D, ...], preview: Point2D
) -> None:
    document, _ = _prepare()
    controller = InteractionController(document, VIEWPORT)
    controller.activate(tool)
    for point in partial_clicks:
        _click(controller, point)
    controller.pointer_move(*_screen(preview))
    assert controller.preview

    controller.cancel()

    assert not controller.preview
    assert controller.history.undo_count == 0


def test_advanced_recipe_values_and_dynamic_dependencies() -> None:
    document, objects = _prepare()
    controller = InteractionController(document, VIEWPORT)

    scenarios = (
        ("ray", (Point2D(0, 0), Point2D(1, 0)), Point2D(1, 0)),
        ("vector", (Point2D(0, 0), Point2D(0, 1)), Point2D(0, 1)),
        ("circle_radius", (Point2D(0, 0), Point2D(1, 0)), Point2D(1, 0)),
        ("rotate", (Point2D(1, 0), Point2D(0, 0), Point2D(0, 1)), Point2D(0, 1)),
        ("scale", (Point2D(1, 0), Point2D(0, 0), Point2D(-1, 0)), Point2D(-1, 0)),
    )
    for tool, clicks, preview in scenarios:
        _perform(controller, tool, clicks, preview)

    scenario_kinds = {row[0] for row in scenarios}
    created = {obj.kind: obj for obj in document.objects.values() if obj.kind in scenario_kinds}
    assert isinstance(created["ray"].geometry, Ray2D)
    assert created["vector"].geometry == Vector2D(0, 1)
    assert created["circle_radius"].geometry == Circle2D(Point2D(0, 0), 1)
    rotated = created["rotate"].geometry
    assert isinstance(rotated, Point2D)
    assert rotated.almost_equals(Point2D(0, 1))
    assert created["rotate"].params["angle"] == pytest.approx(math.pi / 2)
    assert created["scale"].geometry == Point2D(-1, 0)
    assert created["scale"].params["factor"] == pytest.approx(-1)

    document.move_point(objects["top"].id, Point2D(0, 2))
    assert created["vector"].id in document.last_recomputed
    assert document.get(created["vector"].id).geometry == Vector2D(0, 2)
    rotated_after_move = document.get(created["rotate"].id).geometry
    assert isinstance(rotated_after_move, Point2D)
    assert rotated_after_move.almost_equals(Point2D(0, 1))


def test_degenerate_advanced_construction_stays_transient() -> None:
    document, _ = _prepare()
    controller = InteractionController(document, VIEWPORT)
    controller.activate("circle_radius")
    _click(controller, Point2D(0, 0))
    _click(controller, Point2D(0, 0))
    assert controller.history.undo_count == 0
    assert all(obj.kind != "circle_radius" for obj in document.objects.values())


def test_each_advanced_tool_produces_the_expected_geometry() -> None:
    def construct(tool: str, clicks: tuple[Point2D, ...]) -> GeoObject:
        document, _ = _prepare()
        controller = InteractionController(document, VIEWPORT)
        original = set(document.objects)
        _perform(controller, tool, clicks, clicks[-1])
        return next(obj for key, obj in document.objects.items() if key not in original)

    ray = construct("ray", (Point2D(0, 0), Point2D(1, 0))).geometry
    vector = construct("vector", (Point2D(0, 0), Point2D(0, 1))).geometry
    bisector = construct("perpendicular_bisector", (Point2D(1, 0), Point2D(-1, 0))).geometry
    angle_bisector_geometry = construct(
        "angle_bisector", (Point2D(1, 0), Point2D(0, 0), Point2D(0, 1))
    ).geometry
    projection = construct("projection", (Point2D(0, 1), Point2D(0.5, 0))).geometry
    point_on = construct("point_on", (Point2D(0.5, 0),)).geometry
    circle = construct("circle_radius", (Point2D(0, 0), Point2D(1, 0))).geometry
    circumcircle = construct("circumcircle", (Point2D(1, 0), Point2D(0, 0), Point2D(0, 1))).geometry
    distance = construct("distance", (Point2D(1, 0), Point2D(0, 1))).geometry
    angle_measure = construct("angle", (Point2D(1, 0), Point2D(0, 0), Point2D(0, 1))).geometry
    translated = construct("translate", (Point2D(1, 0), Point2D(0, 0.5))).geometry
    rotated = construct("rotate", (Point2D(1, 0), Point2D(0, 0), Point2D(0, 1))).geometry
    central = construct("reflect_point", (Point2D(1, 0), Point2D(0, 0))).geometry
    axial = construct("reflect_line", (Point2D(0, 1), Point2D(0.5, 0))).geometry
    scaled = construct("scale", (Point2D(1, 0), Point2D(0, 0), Point2D(-1, 0))).geometry

    assert isinstance(ray, Ray2D) and ray.start == Point2D(0, 0)
    assert vector == Vector2D(0, 1)
    assert isinstance(bisector, Line2D) and bisector.distance(Point2D(0, 2)) < 1e-9
    assert isinstance(angle_bisector_geometry, Line2D)
    assert angle_bisector_geometry.distance(Point2D(1, 1)) < 1e-9
    assert projection == Point2D(0, 0)
    assert point_on == Point2D(0.5, 0)
    assert circle == Circle2D(Point2D(0, 0), 1)
    assert isinstance(circumcircle, Circle2D)
    assert circumcircle.center == Point2D(0.5, 0.5)
    assert distance == pytest.approx(math.sqrt(2))
    assert angle_measure == pytest.approx(math.pi / 2)
    assert translated == Point2D(1, 1)
    assert isinstance(rotated, Point2D) and rotated.almost_equals(Point2D(0, 1))
    assert central == Point2D(-1, 0)
    assert axial == Point2D(0, -1)
    assert scaled == Point2D(-1, 0)


def test_point_on_object_and_point_line_distance_follow_their_support() -> None:
    document, objects = _prepare()
    controller = InteractionController(document, VIEWPORT)
    _perform(controller, "point_on", (Point2D(0.5, 0),), Point2D(0.5, 0))
    constrained = next(obj for obj in document.objects.values() if obj.kind == "point_on")
    _perform(
        controller,
        "distance",
        (Point2D(0, 1), Point2D(1.5, 0)),
        Point2D(1.5, 0),
    )
    measurement = next(obj for obj in document.objects.values() if obj.kind == "distance")
    assert measurement.dependencies[1] == objects["line"].id
    assert measurement.geometry == pytest.approx(1)

    document.move_point(objects["far_left"].id, Point2D(-2, 2))
    document.move_point(objects["far_right"].id, Point2D(2, 2))

    assert document.get(constrained.id).geometry == Point2D(0.5, 2)
    assert document.get(measurement.id).geometry == pytest.approx(1)


def test_distance_prefers_an_existing_point_over_a_line_beneath_it() -> None:
    document, objects = _prepare()
    controller = InteractionController(document, VIEWPORT)

    _perform(
        controller,
        "distance",
        (Point2D(1, 0), Point2D(0, 0)),
        Point2D(0, 0),
    )

    measurement = next(obj for obj in document.objects.values() if obj.kind == "distance")
    assert measurement.dependencies == (objects["right"].id, objects["origin"].id)
    assert measurement.geometry == pytest.approx(1)
