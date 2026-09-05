"""Verify the Qt painter renderer across all currently supported geometry types."""

from PySide6.QtGui import QImage, QPainter, QPalette

from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport


def test_renderer_draws_supported_document_geometry_without_mutation() -> None:
    document = Document()
    a = document.add(GeoObject("point", "A", params={"x": -2, "y": -1}))
    b = document.add(GeoObject("point", "B", params={"x": 2, "y": 1}))
    c = document.add(GeoObject("point", "C", params={"x": 0, "y": 2}))
    for kind, name, dependencies in (
        ("segment", "s", (a.id, b.id)),
        ("line", "d", (a.id, b.id)),
        ("ray", "r", (a.id, c.id)),
        ("vector", "v", (a.id, b.id)),
        ("circle", "c", (a.id, b.id)),
        ("polygon", "p", (a.id, b.id, c.id)),
    ):
        document.add(GeoObject(kind, name, dependencies=dependencies))

    before = dict(document.objects)
    image = QImage(640, 480, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    Renderer().render(
        painter,
        document,
        Viewport(scale=70, width=640, height=480),
        QPalette(),
        {a.id},
    )
    painter.end()

    assert image.width() == 640
    assert document.objects == before
