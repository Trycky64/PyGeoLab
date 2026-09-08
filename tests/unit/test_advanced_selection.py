"""Verify advanced selection gestures and grouped reversible editing operations."""

from pygeolab.geometry import Point2D
from pygeolab.interaction import InteractionController
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
from pygeolab.persistence import document_from_mapping
from pygeolab.persistence.serializer import serialize_document
from pygeolab.rendering.hit_test import hit_test, objects_in_screen_rect
from pygeolab.rendering.viewport import Viewport

VIEWPORT = Viewport(width=800, height=600, scale=80)


def _point(name: str, x: float, y: float, **kwargs: object) -> GeoObject:
    return GeoObject("point", name, params={"x": x, "y": y}, **kwargs)


def _screen(point: Point2D) -> tuple[float, float]:
    return VIEWPORT.world_to_screen(point)


def _click(
    controller: InteractionController,
    point: Point2D,
    *,
    shift: bool = False,
    ctrl: bool = False,
) -> None:
    x, y = _screen(point)
    controller.pointer_press(x, y, shift=shift, ctrl=ctrl)
    controller.pointer_release(x, y, shift=shift, ctrl=ctrl)


def _marquee(
    controller: InteractionController,
    start: Point2D,
    end: Point2D,
    *,
    shift: bool = False,
    ctrl: bool = False,
) -> None:
    start_x, start_y = _screen(start)
    end_x, end_y = _screen(end)
    controller.pointer_press(start_x, start_y, shift=shift, ctrl=ctrl)
    controller.pointer_move(end_x, end_y, shift=shift, ctrl=ctrl)
    assert controller.preview
    controller.pointer_release(end_x, end_y, shift=shift, ctrl=ctrl)


def test_marquee_replaces_adds_and_toggles_selection() -> None:
    document = Document()
    a, b, c = _point("A", -2, 0), _point("B", 0, 0), _point("C", 2, 0)
    document.restore((a, b, c))
    controller = InteractionController(document, VIEWPORT)

    _marquee(controller, Point2D(-2.5, -0.5), Point2D(0.5, 0.5))
    assert controller.selected_ids == {a.id, b.id}
    _marquee(controller, Point2D(1.5, -0.5), Point2D(2.5, 0.5), shift=True)
    assert controller.selected_ids == {a.id, b.id, c.id}
    _marquee(controller, Point2D(-0.5, -0.5), Point2D(2.5, 0.5), ctrl=True)
    assert controller.selected_ids == {a.id}


def test_ctrl_toggles_while_shift_adds_and_empty_click_clears() -> None:
    document = Document()
    a, b = _point("A", 0, 0), _point("B", 2, 0)
    document.restore((a, b))
    controller = InteractionController(document, VIEWPORT)

    _click(controller, Point2D(0, 0))
    _click(controller, Point2D(2, 0), shift=True)
    _click(controller, Point2D(0, 0), ctrl=True)
    assert controller.selected_ids == {b.id}
    _click(controller, Point2D(5, 3))
    assert not controller.selected_ids


def test_select_all_clear_and_cancelled_marquee() -> None:
    document = Document()
    points = (_point("A", -1, 0), _point("B", 1, 0))
    document.restore(points)
    controller = InteractionController(document, VIEWPORT)
    controller.select_all()
    assert controller.selected_ids == {point.id for point in points}
    controller.clear_selection()
    assert not controller.selected_ids

    start_x, start_y = _screen(Point2D(-2, -1))
    controller.pointer_press(start_x, start_y)
    controller.pointer_move(*_screen(Point2D(2, 1)))
    assert controller.preview
    controller.cancel()
    assert not controller.preview
    assert not controller.selected_ids


def test_overlapping_clicks_cycle_in_visual_stack_order() -> None:
    document = Document()
    lower, upper = _point("A", 0, 0), _point("B", 0, 0)
    document.restore((lower, upper))
    controller = InteractionController(document, VIEWPORT)
    x, y = _screen(Point2D(0, 0))

    assert hit_test(document, VIEWPORT, x, y)[0].object_id == upper.id
    _click(controller, Point2D(0, 0))
    assert controller.selected_ids == {upper.id}
    _click(controller, Point2D(0, 0))
    assert controller.selected_ids == {lower.id}


def test_rectangle_hit_testing_includes_crossing_geometry() -> None:
    document = Document()
    a, b = _point("A", -3, 0), _point("B", 3, 0)
    line = GeoObject("segment", "s", (a.id, b.id))
    outside = _point("C", 4, 4)
    document.restore((a, b, line, outside))
    start = _screen(Point2D(-0.5, -0.5))
    end = _screen(Point2D(0.5, 0.5))

    hits = objects_in_screen_rect(document, VIEWPORT, *start, *end)
    assert line.id in hits
    assert outside.id not in hits


def test_grouped_delete_restores_dependencies_order_and_one_history_entry() -> None:
    document = Document()
    a, b, c = _point("A", 0, 0), _point("B", 2, 0), _point("C", 4, 0)
    segment = GeoObject("segment", "s", (a.id, b.id))
    document.restore((a, b, segment, c))
    original_order = tuple(document.objects)
    controller = InteractionController(document, VIEWPORT)
    controller.selection.replace_many(frozenset({a.id, segment.id, c.id}))

    assert controller.delete_selection()
    assert tuple(document.objects) == (b.id,)
    assert controller.history.undo_count == 1
    assert controller.undo()
    assert tuple(document.objects) == original_order
    assert document.get(segment.id).dependencies == (a.id, b.id)
    assert controller.redo()
    assert tuple(document.objects) == (b.id,)


def test_group_visibility_lock_and_style_are_each_one_reversible_command() -> None:
    document = Document()
    a, b = _point("A", 0, 0), _point("B", 2, 0)
    document.restore((a, b))
    controller = InteractionController(document, VIEWPORT)
    controller.selection.replace_many(frozenset({a.id, b.id}))
    style = Style(color="#ff0000", width=4)

    assert controller.set_selection_visibility(False)
    assert controller.set_selection_locked(True)
    assert controller.set_selection_style(style)
    assert controller.history.undo_count == 3
    assert all(
        obj.style == style and obj.locked and not obj.visible for obj in document.objects.values()
    )

    assert controller.undo()
    assert all(obj.style == Style() for obj in document.objects.values())
    assert controller.undo()
    assert all(not obj.locked for obj in document.objects.values())
    assert controller.undo()
    assert all(obj.visible for obj in document.objects.values())
    for _ in range(3):
        assert controller.redo()
    assert all(
        obj.style == style and obj.locked and not obj.visible for obj in document.objects.values()
    )


def test_duplicate_only_independent_objects_and_undo_redo_batch() -> None:
    document = Document()
    a, b = _point("A", 0, 0), _point("B", 2, 0)
    segment = GeoObject("segment", "s", (a.id, b.id))
    document.restore((a, b, segment))
    controller = InteractionController(document, VIEWPORT)
    controller.selection.replace_many(frozenset({a.id, segment.id}))

    duplicate_ids = controller.duplicate_selection()
    assert len(duplicate_ids) == 1
    duplicate = document.get(next(iter(duplicate_ids)))
    assert duplicate.kind == "point" and duplicate.name == "A1"
    assert duplicate.geometry == Point2D(0.25, -0.25)
    assert controller.selected_ids == duplicate_ids
    assert controller.history.undo_count == 1
    assert controller.undo() and duplicate.id not in document.objects
    assert controller.redo() and duplicate.id in document.objects


def test_drawing_order_change_is_persistent_and_reversible() -> None:
    document = Document()
    a, b, c = _point("A", 0, 0), _point("B", 1, 0), _point("C", 2, 0)
    document.restore((a, b, c))
    controller = InteractionController(document, VIEWPORT)
    controller.selection.replace_many(frozenset({a.id, b.id}))

    assert controller.reorder_selection(to_front=True)
    assert tuple(document.objects) == (c.id, a.id, b.id)
    assert controller.history.undo_count == 1
    assert controller.undo()
    assert tuple(document.objects) == (a.id, b.id, c.id)
    assert controller.redo()
    assert tuple(document.objects) == (c.id, a.id, b.id)
    loaded = document_from_mapping(serialize_document(document))
    assert tuple(loaded.objects) == (c.id, a.id, b.id)
