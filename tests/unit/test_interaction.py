"""Test hit-testing, tool state machines, previews, selection and coalesced dragging."""

from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Segment2D
from pygeolab.interaction import InteractionController
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.rendering.hit_test import first_hit, hit_test
from pygeolab.rendering.viewport import Viewport

VIEWPORT = Viewport(width=800, height=600, scale=80)


def screen(point: Point2D) -> tuple[float, float]:
    """Map one world point through the shared interaction test viewport."""
    return VIEWPORT.world_to_screen(point)


def free_point(name: str, x: float, y: float) -> GeoObject:
    """Create one free point definition."""
    return GeoObject("point", name, params={"x": x, "y": y})


def click(controller: InteractionController, point: Point2D, shift: bool = False) -> None:
    """Send a full primary click at a world position."""
    x, y = screen(point)
    controller.pointer_press(x, y, shift)
    controller.pointer_release(x, y, shift)


def test_hit_testing_prefers_points_over_overlapping_segments() -> None:
    document = Document()
    a, b = free_point("A", 0, 0), free_point("B", 2, 0)
    segment = GeoObject("segment", "s", (a.id, b.id))
    document.restore((a, b, segment))
    x, y = screen(Point2D(0, 0))
    hits = hit_test(document, VIEWPORT, x, y)
    assert hits[0].object_id == a.id
    assert first_hit(document, VIEWPORT, x, y).id == a.id


def test_selection_shift_multiselect_and_empty_click_clear() -> None:
    document = Document()
    a, b = free_point("A", 0, 0), free_point("B", 2, 0)
    document.restore((a, b))
    controller = InteractionController(document, VIEWPORT)
    click(controller, Point2D(0, 0))
    assert controller.selected_ids == {a.id}
    click(controller, Point2D(2, 0), shift=True)
    assert controller.selected_ids == {a.id, b.id}
    click(controller, Point2D(4, 3))
    assert not controller.selected_ids


def test_drag_free_point_updates_dependents_and_records_one_history_entry() -> None:
    document = Document()
    a, b = free_point("A", 0, 0), free_point("B", 4, 0)
    midpoint = GeoObject("midpoint", "M", (a.id, b.id))
    document.restore((a, b, midpoint))
    controller = InteractionController(document, VIEWPORT)
    ax, ay = screen(Point2D(0, 0))
    end_x, end_y = screen(Point2D(2, 2))
    controller.pointer_press(ax, ay)
    controller.pointer_move(*screen(Point2D(1, 1)))
    controller.pointer_move(end_x, end_y)
    controller.pointer_release(end_x, end_y)
    assert document.get(a.id).geometry == Point2D(2, 2)
    assert document.get(midpoint.id).geometry == Point2D(3, 1)
    assert controller.history.undo_count == 1
    controller.undo()
    assert document.get(a.id).geometry == Point2D(0, 0)
    assert document.get(midpoint.id).geometry == Point2D(2, 0)


def test_escape_cancels_drag_and_restores_initial_point_without_history() -> None:
    document = Document()
    a = document.add(free_point("A", 0, 0))
    controller = InteractionController(document, VIEWPORT)
    x, y = screen(Point2D(0, 0))
    controller.pointer_press(x, y)
    controller.pointer_move(*screen(Point2D(2, 1)))
    controller.cancel()
    assert document.get(a.id).geometry == Point2D(0, 0)
    assert controller.history.undo_count == 0


def test_point_segment_line_and_circle_tools_create_recipes_and_undo_batches() -> None:
    for tool_name, kind in (("segment", "segment"), ("line", "line"), ("circle", "circle")):
        document = Document()
        controller = InteractionController(document, VIEWPORT)
        controller.activate(tool_name)
        click(controller, Point2D(-1, 0))
        controller.pointer_move(*screen(Point2D(1, 0)))
        assert controller.preview
        click(controller, Point2D(1, 0))
        kinds = [obj.kind for obj in document.objects.values()]
        assert kinds.count("point") == 2
        assert kinds.count(kind) == 1
        assert controller.history.undo_count == 1
        controller.undo()
        assert not document.objects

    document = Document()
    controller = InteractionController(document, VIEWPORT)
    controller.activate("point")
    click(controller, Point2D(1, 2))
    assert len(document.objects) == 1
    assert next(iter(document.objects.values())).geometry == Point2D(1, 2)


def test_escape_cancels_incomplete_construction_without_creating_objects() -> None:
    document = Document()
    controller = InteractionController(document, VIEWPORT)
    controller.activate("segment")
    click(controller, Point2D(0, 0))
    controller.pointer_move(*screen(Point2D(2, 0)))
    assert controller.preview
    controller.cancel()
    assert not controller.preview
    assert not document.objects
    assert controller.history.undo_count == 0


def test_polygon_tool_closes_near_first_pending_vertex() -> None:
    document = Document()
    controller = InteractionController(document, VIEWPORT)
    controller.activate("polygon")
    for point in (Point2D(0, 0), Point2D(2, 0), Point2D(1, 2), Point2D(0, 0)):
        click(controller, point)
    polygons = [obj for obj in document.objects.values() if obj.kind == "polygon"]
    assert len(polygons) == 1
    assert isinstance(polygons[0].geometry, Polygon2D)
    assert len(document.objects) == 4


def test_midpoint_intersection_parallel_and_perpendicular_tools() -> None:
    document = Document()
    a, b, c = free_point("A", -2, 0), free_point("B", 2, 0), free_point("C", 0, 2)
    horizontal = GeoObject("line", "h", (a.id, b.id))
    vertical_a, vertical_b = free_point("D", 0, -2), c
    vertical = GeoObject("line", "v", (vertical_a.id, vertical_b.id))
    document.restore((a, b, c, vertical_a, horizontal, vertical))
    controller = InteractionController(document, VIEWPORT)

    controller.activate("midpoint")
    click(controller, Point2D(-2, 0))
    click(controller, Point2D(2, 0))
    assert any(obj.kind == "midpoint" for obj in document.objects.values())

    controller.activate("intersection")
    click(controller, Point2D(1, 0))
    click(controller, Point2D(0, 1))
    intersections = [obj for obj in document.objects.values() if obj.kind == "intersection"]
    assert len(intersections) == 1
    assert intersections[0].geometry == Point2D(0, 0)

    controller.activate("parallel")
    click(controller, Point2D(0, 2))
    click(controller, Point2D(1, 0))
    parallel = [obj for obj in document.objects.values() if obj.kind == "parallel"]
    assert len(parallel) == 1
    assert isinstance(parallel[0].geometry, Line2D)

    controller.activate("perpendicular")
    click(controller, Point2D(0, 2))
    click(controller, Point2D(1, 0))
    perpendicular = [obj for obj in document.objects.values() if obj.kind == "perpendicular"]
    assert len(perpendicular) == 1
    assert isinstance(perpendicular[0].geometry, Line2D)


def test_locked_and_calculated_points_are_not_dragged() -> None:
    document = Document()
    locked = free_point("A", 0, 0)
    locked = GeoObject("point", "A", params={"x": 0, "y": 0}, locked=True, id=locked.id)
    a, b = free_point("B", 2, 0), free_point("C", 4, 0)
    middle = GeoObject("midpoint", "M", (a.id, b.id))
    document.restore((locked, a, b, middle))
    controller = InteractionController(document, VIEWPORT)
    for world in (Point2D(0, 0), Point2D(3, 0)):
        x, y = screen(world)
        controller.pointer_press(x, y)
        controller.pointer_move(*screen(Point2D(world.x, 2)))
        controller.pointer_release(*screen(Point2D(world.x, 2)))
    assert document.get(locked.id).geometry == Point2D(0, 0)
    assert document.get(middle.id).geometry == Point2D(3, 0)
    assert controller.history.undo_count == 0
