"""Exercise complete construction, dependency update and history scenarios."""

from pygeolab.geometry import Point2D
from pygeolab.interaction import InteractionController
from pygeolab.model.document import Document
from pygeolab.rendering.viewport import Viewport


def test_construct_segment_midpoint_drag_and_undo_chain() -> None:
    viewport = Viewport(width=800, height=600, scale=80)
    document = Document()
    controller = InteractionController(document, viewport)

    def click(world: Point2D) -> None:
        x, y = viewport.world_to_screen(world)
        controller.pointer_press(x, y)
        controller.pointer_release(x, y)

    controller.activate("segment")
    click(Point2D(0, 0))
    click(Point2D(4, 0))
    segment = next(obj for obj in document.objects.values() if obj.kind == "segment")

    controller.activate("midpoint")
    click(Point2D(2, 0))
    middle = next(obj for obj in document.objects.values() if obj.kind == "midpoint")
    assert middle.dependencies == (segment.id,)
    assert middle.geometry == Point2D(2, 0)

    controller.activate("select")
    first = next(obj for obj in document.objects.values() if obj.kind == "point")
    assert isinstance(first.geometry, Point2D)
    start_x, start_y = viewport.world_to_screen(first.geometry)
    end = Point2D(first.geometry.x, 2)
    end_x, end_y = viewport.world_to_screen(end)
    controller.pointer_press(start_x, start_y)
    controller.pointer_move(end_x, end_y)
    controller.pointer_release(end_x, end_y)
    assert document.get(middle.id).geometry == Point2D(2, 1)

    controller.undo()
    assert document.get(middle.id).geometry == Point2D(2, 0)
    controller.undo()
    assert middle.id not in document.objects
    controller.undo()
    assert not document.objects
    controller.redo()
    controller.redo()
    controller.redo()
    assert document.get(middle.id).geometry == Point2D(2, 1)
