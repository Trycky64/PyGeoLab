"""Exercise the Qt geometry viewport integration without implementing construction tools."""

from pytestqt.qtbot import QtBot

from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.ui.geometry_view import GeometryView


def test_geometry_view_tracks_size_pan_zoom_and_document_updates(qtbot: QtBot) -> None:
    document = Document()
    point = document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))
    view = GeometryView(document)
    qtbot.addWidget(view)
    view.resize(800, 600)
    view.show()
    qtbot.waitUntil(view.isVisible)

    assert view.viewport.width == 800
    assert view.viewport.height == 600
    old_center = view.viewport.center
    view.pan_by_pixels(80, 40)
    assert view.viewport.center != old_center

    cursor = (300.0, 250.0)
    anchor = view.viewport.screen_to_world(*cursor)
    old_scale = view.viewport.scale
    view.zoom_at(1.5, *cursor)
    assert view.viewport.scale == old_scale * 1.5
    assert view.viewport.screen_to_world(*cursor).almost_equals(anchor)

    view.reset_view()
    assert view.viewport.center == Point2D(0, 0)
    assert view.viewport.scale == 80

    document.move_point(point.id, Point2D(2, 3))
    assert document.get(point.id).geometry == Point2D(2, 3)
