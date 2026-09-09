"""Verify PNG and SVG viewport exports through real Qt paint devices."""

import re
import xml.etree.ElementTree as ET

from PySide6.QtGui import QImage, QPalette
from PySide6.QtWidgets import QApplication

from pygeolab.exporting import (
    copy_png_to_clipboard,
    copy_svg_to_clipboard,
    export_png,
    export_svg,
    fitted_viewport,
    render_png_image,
    render_svg_bytes,
)
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
from pygeolab.rendering.viewport import Viewport


def test_png_and_svg_export(qapp: QApplication, tmp_path) -> None:
    """Both export formats preserve requested resolution and produce nonempty files."""
    del qapp
    document = Document("Export")
    document.restore(
        (
            GeoObject("point", "A", params={"x": -1.0, "y": 0.0}),
            GeoObject("point", "B", params={"x": 1.0, "y": 0.0}),
        )
    )
    viewport = Viewport(width=320, height=200)
    palette = QPalette()
    png = export_png(tmp_path / "scene", document, viewport, palette, scale=2.0)
    svg = export_svg(tmp_path / "scene", document, viewport, palette, transparent=True)

    image = QImage(str(png))
    assert not image.isNull()
    assert image.width() == 640
    assert image.height() == 400
    assert png.suffix == ".png"
    assert png.stat().st_size > 100
    text = svg.read_text(encoding="utf-8")
    assert "<svg" in text
    assert svg.stat().st_size > 100


def test_png_custom_dimensions_scale_transparency_and_metadata(qapp: QApplication) -> None:
    del qapp
    document = Document("Dimensions")
    document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))

    image = render_png_image(
        document,
        Viewport(width=100, height=80),
        QPalette(),
        width=300,
        height=150,
        scale=2,
        transparent=True,
    )

    assert image.size().width() == 600
    assert image.size().height() == 300
    assert image.text("Software") == "PyGeoLab"
    assert image.text("Title") == "Dimensions"
    assert image.pixelColor(0, 0).alpha() == 0


def test_document_viewport_fits_geometry_independently_from_canvas(qapp: QApplication) -> None:
    del qapp
    document = Document()
    document.add(GeoObject("point", "A", params={"x": 1000, "y": 500}))
    document.add(GeoObject("point", "B", params={"x": 1100, "y": 550}))

    fitted = fitted_viewport(document, 400, 200)

    assert fitted.center.x == 1050
    assert fitted.center.y == 525
    assert fitted != Viewport(width=400, height=200)


def test_selection_export_omits_unselected_objects(qapp: QApplication) -> None:
    del qapp
    document = Document()
    selected = document.add(
        GeoObject("point", "A", params={"x": -2, "y": 0}, style=Style(color="#ff0000"))
    )
    document.add(GeoObject("point", "B", params={"x": 2, "y": 0}, style=Style(color="#00ff00")))
    viewport = fitted_viewport(document, 200, 120, {selected.id})

    image = render_png_image(
        document,
        viewport,
        QPalette(),
        transparent=True,
        object_ids={selected.id},
    )

    colors = [image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height())]
    assert any(color.red() > 200 and color.green() < 100 for color in colors)
    assert not any(color.green() > 200 and color.red() < 100 for color in colors)


def test_svg_contains_metadata_labels_curves_and_valid_structure(qapp: QApplication) -> None:
    del qapp
    document = Document("Courbes")
    document.add(GeoObject("function", "f", params={"variable": "x", "source": "sin(x)"}))

    data = render_svg_bytes(document, Viewport(width=320, height=200), QPalette())
    root = ET.fromstring(data)
    text = data.decode("utf-8")

    assert root.tag.endswith("svg")
    assert "Courbes" in text
    assert "f" in text
    assert any(element.tag.endswith(("path", "polyline")) for element in root.iter())


def test_qt_offscreen_clipboard_accepts_png_and_svg(qapp: QApplication) -> None:
    document = Document()
    document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))
    viewport = Viewport(width=160, height=100)

    copy_png_to_clipboard(qapp, document, viewport, QPalette())
    assert not qapp.clipboard().image().isNull()
    copy_svg_to_clipboard(qapp, document, viewport, QPalette())
    mime = qapp.clipboard().mimeData()
    assert mime is not None and mime.hasFormat("image/svg+xml")
    assert "<svg" in mime.text()
    qapp.clipboard().clear()


def test_svg_infinite_lines_are_clipped_to_the_viewbox(qapp: QApplication) -> None:
    del qapp
    document = Document()
    a = GeoObject("point", "A", params={"x": -1, "y": -1})
    b = GeoObject("point", "B", params={"x": 1, "y": 1})
    line = GeoObject("line", "d", (a.id, b.id))
    document.restore((a, b, line))

    data = render_svg_bytes(document, Viewport(width=100, height=80), QPalette())
    root = ET.fromstring(data)
    coordinates: list[tuple[float, float]] = []
    for element in root.iter():
        points = element.attrib.get("points", "")
        coordinates.extend(
            (float(x), float(y))
            for x, y in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", points)
        )

    assert coordinates
    assert all(0 <= x <= 100 and 0 <= y <= 80 for x, y in coordinates)
