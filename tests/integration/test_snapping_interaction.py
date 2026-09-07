"""Exercise snapping through construction previews, commands and coalesced drags."""

from pygeolab.geometry import Point2D, Segment2D
from pygeolab.interaction import InteractionController, SnapKind
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.rendering.viewport import Viewport

VIEWPORT = Viewport(width=800, height=600, scale=80)


def _screen(point: Point2D) -> tuple[float, float]:
    return VIEWPORT.world_to_screen(point)


def _click(
    controller: InteractionController, point: Point2D, *, suppress_snap: bool = False
) -> None:
    x, y = _screen(point)
    controller.pointer_press(x, y, suppress_snap=suppress_snap)
    controller.pointer_release(x, y, suppress_snap=suppress_snap)


def test_grid_snapping_applies_to_point_creation_and_segment_preview() -> None:
    document = Document()
    controller = InteractionController(document, VIEWPORT)
    controller.activate("segment")
    _click(controller, Point2D(0.04, 0.03))
    controller.pointer_move(*_screen(Point2D(2.05, 0.04)))

    assert controller.snap_result is not None
    assert controller.snap_result.kind is SnapKind.GRID
    assert controller.preview == (Segment2D(Point2D(0, 0), Point2D(2, 0)),)

    _click(controller, Point2D(2.05, 0.04))
    points = [obj.geometry for obj in document.objects.values() if obj.kind == "point"]
    assert points == [Point2D(0, 0), Point2D(2, 0)]
    assert controller.history.undo_count == 1


def test_free_point_drag_snaps_to_another_point_and_records_one_command() -> None:
    document = Document()
    moving = GeoObject("point", "A", params={"x": 0, "y": 0})
    target = GeoObject("point", "B", params={"x": 2, "y": 1})
    document.restore((moving, target))
    controller = InteractionController(document, VIEWPORT)
    controller.pointer_press(*_screen(Point2D(0, 0)))
    controller.pointer_move(*_screen(Point2D(2.08, 1.02)))
    controller.pointer_release(*_screen(Point2D(2.08, 1.02)))

    assert document.get(moving.id).geometry == Point2D(2, 1)
    assert controller.history.undo_count == 1
    assert controller.undo()
    assert document.get(moving.id).geometry == Point2D(0, 0)


def test_alt_temporarily_suppresses_snap_without_changing_global_setting() -> None:
    document = Document()
    controller = InteractionController(document, VIEWPORT)
    controller.activate("point")
    raw = Point2D(1.04, 1.03)

    _click(controller, raw, suppress_snap=True)

    created = next(iter(document.objects.values()))
    assert isinstance(created.geometry, Point2D)
    assert created.geometry.almost_equals(raw)
    assert controller.snapping_options.enabled
    assert controller.snap_result is None


def test_global_toggle_disables_and_reenables_snapping() -> None:
    document = Document()
    controller = InteractionController(document, VIEWPORT)
    controller.activate("point")
    controller.set_snapping_enabled(False)
    _click(controller, Point2D(1.04, 1.03))
    first = next(iter(document.objects.values())).geometry
    assert isinstance(first, Point2D)
    assert first.almost_equals(Point2D(1.04, 1.03))

    controller.set_snapping_enabled(True)
    _click(controller, Point2D(3.04, 2.03))
    assert list(document.objects.values())[-1].geometry == Point2D(3, 2)
